# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging
from dataclasses import dataclass
from typing import List, Optional
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from ..core import VectorStore
from ..rankers import BM25Ranker, CrossEncoderReranker, DenseEmbeddingRanker, MMRStoreRanker
from .budget import DEFAULT_TOKEN_ENCODING
from .pipelines import KBRetrievalPipeline, ModuleRetrievalPipeline
from .hybrid import HybridRetriever

logger = logging.getLogger(__name__)

# Defaults so the dataclass and from_dict share one source of truth.
DEFAULT_MODULE_CHUNK_TOKEN_BUDGET = 8000
DEFAULT_MIN_CANDIDATES_PER_RANKER = 30
DEFAULT_MAX_RERANK_CANDIDATES = 500
DEFAULT_KB_CANDIDATES_PER_RANKER = 30
DEFAULT_RRF_K = 60


@dataclass(frozen=True)
class RetrievalConfig:
    """Immutable bundle of retrieval-side knobs read from config.yaml."""

    module_chunk_token_budget: int = DEFAULT_MODULE_CHUNK_TOKEN_BUDGET
    min_candidates_per_ranker: int = DEFAULT_MIN_CANDIDATES_PER_RANKER
    max_rerank_candidates: int = DEFAULT_MAX_RERANK_CANDIDATES
    kb_candidates_per_ranker: int = DEFAULT_KB_CANDIDATES_PER_RANKER
    rrf_k: int = DEFAULT_RRF_K
    use_kb: bool = True
    token_encoding: str = DEFAULT_TOKEN_ENCODING

    @classmethod
    def from_dict(cls, cfg: dict) -> "RetrievalConfig":
        """Build a RetrievalConfig from the parsed config.yaml dict."""

        retrieval = cfg.get("retrieval", {}) or {}
        text_splitter = cfg.get("document_processing", {}).get("text_splitter", {}) or {}

        legacy_candidates = retrieval.get("bm25_candidates", retrieval.get("dense_candidates"))

        return cls(
            module_chunk_token_budget=retrieval.get(
                "module_chunk_token_budget",
                retrieval.get("module_context_window_tokens", DEFAULT_MODULE_CHUNK_TOKEN_BUDGET),
            ),
            min_candidates_per_ranker=retrieval.get(
                "min_candidates_per_ranker",
                legacy_candidates if legacy_candidates is not None else DEFAULT_MIN_CANDIDATES_PER_RANKER,
            ),
            max_rerank_candidates=retrieval.get("max_rerank_candidates", DEFAULT_MAX_RERANK_CANDIDATES),
            kb_candidates_per_ranker=retrieval.get(
                "kb_candidates_per_ranker",
                legacy_candidates if legacy_candidates is not None else DEFAULT_KB_CANDIDATES_PER_RANKER,
            ),
            rrf_k=retrieval.get("rrf_k", DEFAULT_RRF_K),
            use_kb=retrieval.get("use_kb", True),
            token_encoding=text_splitter.get("token_encoding", DEFAULT_TOKEN_ENCODING),
        )


def build_kb_pipeline(cfg: RetrievalConfig, vector_store: VectorStore,
                      kb_bm25: Optional[BM25Ranker], reranker: CrossEncoderReranker) -> Optional[KBRetrievalPipeline]:
    """
    Build the KB retrieval pipeline (hybrid sparse+dense + rerank + dedup).
    Returns None when KB usage is disabled or the BM25 index is missing.
    """

    if not cfg.use_kb or kb_bm25 is None:
        return None

    hybrid = HybridRetriever(
        sparse=kb_bm25,
        dense=MMRStoreRanker(vector_store),
        sparse_candidates=cfg.kb_candidates_per_ranker,
        dense_candidates=cfg.kb_candidates_per_ranker,
        rrf_k=cfg.rrf_k,
    )
    return KBRetrievalPipeline(hybrid=hybrid, reranker=reranker)


def build_module_pipeline(cfg: RetrievalConfig, documents: List[Document],
                          doc_embeddings: Optional[List[List[float]]], embeddings: Embeddings,
                          reranker: CrossEncoderReranker) -> Optional[ModuleRetrievalPipeline]:
    """
    Build the module retrieval pipeline for a specific module's documents.
    Returns None when there are no documents to index. The dense ranker is
    omitted when doc_embeddings is absent; the hybrid then runs sparse-only.
    """

    if not documents:
        return None

    sparse = BM25Ranker(documents)
    dense = (
        DenseEmbeddingRanker(documents, doc_embeddings, embeddings)
        if doc_embeddings else None
    )
    hybrid = HybridRetriever(
        sparse=sparse,
        dense=dense,
        sparse_candidates=cfg.min_candidates_per_ranker,
        dense_candidates=cfg.min_candidates_per_ranker,
        rrf_k=cfg.rrf_k,
    )
    return ModuleRetrievalPipeline(
        hybrid=hybrid,
        reranker=reranker,
        token_budget=cfg.module_chunk_token_budget,
        min_candidates_per_ranker=cfg.min_candidates_per_ranker,
        max_rerank_candidates=cfg.max_rerank_candidates,
        token_encoding=cfg.token_encoding,
    )
