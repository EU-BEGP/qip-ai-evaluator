# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging
from typing import List
from langchain_core.documents import Document

from ...rankers import CrossEncoderReranker
from ..budget import DEFAULT_TOKEN_ENCODING, count_tokens, select_by_token_budget
from ..hybrid import HybridRetriever

logger = logging.getLogger(__name__)


class ModuleRetrievalPipeline:
    """Tier 1 (full module) OR Tier 2 (hybrid RAG with dynamic candidate sizing)."""

    def __init__(self, hybrid: HybridRetriever, reranker: CrossEncoderReranker, token_budget: int,
                 min_candidates_per_ranker: int = 30, max_rerank_candidates: int = 500,
                 token_encoding: str = DEFAULT_TOKEN_ENCODING):
        self.hybrid = hybrid
        self.reranker = reranker
        self.token_budget = token_budget
        self.min_candidates_per_ranker = min_candidates_per_ranker
        self.max_rerank_candidates = max_rerank_candidates
        self.token_encoding = token_encoding

    def retrieve(self, query: str, documents: List[Document]) -> List[Document]:
        """Return the doc chunks chosen for this query."""

        if not documents:
            return []

        token_count = count_tokens(documents, self.token_encoding)

        # Tier 1 — entire module fits in budget. Skip retrieval entirely.
        if token_count <= self.token_budget:
            logger.info(
                f"Module fits in token budget ({token_count}/{self.token_budget}). Sending full module."
            )
            return sorted(documents, key=lambda d: d.metadata.get("chunk_index", 0))

        # Tier 2 — hybrid RAG with dynamic candidate sizing.
        per_ranker_top_k = self._dynamic_per_ranker_top_k(token_count, len(documents))

        _sparse, _dense, candidates = self.hybrid.retrieve(
            query,
            sparse_top_k=per_ranker_top_k,
            dense_top_k=per_ranker_top_k,
        )

        if not candidates:
            candidates = documents

        # Cap reranker input to bound cross-encoder compute. Candidates are RRF-
        # ordered (relevance desc), so the tail is the weakest joint signal.
        if len(candidates) > self.max_rerank_candidates:
            logger.info(
                f"Capping reranker input from {len(candidates)} to {self.max_rerank_candidates} candidates."
            )
            candidates = candidates[:self.max_rerank_candidates]

        ranked = self.reranker.rerank(query, candidates, top_k=len(candidates))
        selected = select_by_token_budget(ranked, self.token_budget, self.token_encoding)
        logger.info(
            f"Module retrieval: {len(selected)} chunks selected within {self.token_budget} token budget "
            f"(per_ranker_top_k={per_ranker_top_k}, candidates_reranked={len(candidates)})."
        )
        return selected

    def _dynamic_per_ranker_top_k(self, token_count: int, n_documents: int) -> int:
        """
        Per-ranker top_k that scales with how many chunks the budget could absorb.
        Floor at min_candidates_per_ranker protects tiny-budget cases; 2x capacity
        gives the reranker headroom over the budget's effective ceiling.
        """

        avg_chunk_tokens = max(1, token_count / n_documents)
        capacity = max(1, int(self.token_budget / avg_chunk_tokens))
        return max(self.min_candidates_per_ranker, capacity * 2)
