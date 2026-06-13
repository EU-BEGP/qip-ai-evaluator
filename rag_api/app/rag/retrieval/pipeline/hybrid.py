# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from typing import Callable, List, Optional, Protocol, Tuple
from langchain_core.documents import Document

from .fusion import rrf_merge


class _Ranker(Protocol):
    """Anything that takes a query + top_k and returns scored docs."""

    def retrieve(self, query: str, top_k: int) -> List[Tuple[Document, float]]: ...


class HybridRetriever:
    """
    Composes sparse + dense retrievers and fuses their outputs via RRF.
    Reranking and budget filtering are caller-side concerns. Fused list is
    returned in relevance order (RRF score desc).
    """

    def __init__(self, sparse: _Ranker, dense: _Ranker, sparse_candidates: int = 30, dense_candidates: int = 30,
                 fuse: Callable[[List[List[Tuple[Document, float]]], int], List[Document]] = rrf_merge, rrf_k: int = 60):
        self.sparse = sparse
        self.dense = dense
        self.sparse_candidates = sparse_candidates
        self.dense_candidates = dense_candidates
        self.fuse = fuse
        self.rrf_k = rrf_k

    def retrieve(self, query: str, sparse_top_k: Optional[int] = None,
                 dense_top_k: Optional[int] = None) -> Tuple[List[Tuple[Document, float]], List[Tuple[Document, float]], List[Document]]:
        """
        Run both retrievers and fuse the results. sparse_top_k/dense_top_k override the per-call retrieval breadth.
        """

        sparse_k = sparse_top_k if sparse_top_k is not None else self.sparse_candidates
        dense_k = dense_top_k if dense_top_k is not None else self.dense_candidates

        sparse_hits = self.sparse.retrieve(query, top_k=sparse_k) if self.sparse else []
        dense_hits = self.dense.retrieve(query, top_k=dense_k) if self.dense else []
        fused = self.fuse([sparse_hits, dense_hits], self.rrf_k)
        return sparse_hits, dense_hits, fused
