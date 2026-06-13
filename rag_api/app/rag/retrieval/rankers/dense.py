# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging
from typing import List, Tuple
import numpy as np
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from ..core import VectorStore

logger = logging.getLogger(__name__)


class DenseEmbeddingRanker:
    """Cosine-similarity ranker over a precomputed embedding list."""

    def __init__(
        self,
        documents: List[Document],
        doc_embeddings: List[List[float]],
        query_embedder: Embeddings,
    ):
        self.documents = documents
        self.doc_embeddings = doc_embeddings
        self.query_embedder = query_embedder

    def retrieve(self, query: str, top_k: int) -> List[Tuple[Document, float]]:
        """Return top_k (doc, score) by cosine similarity. Empty list when no embeddings."""

        if not self.doc_embeddings or not self.documents:
            return []

        q_vec = np.array(self.query_embedder.embed_query(query))
        doc_vecs = np.array(self.doc_embeddings)
        q_norm = np.linalg.norm(q_vec)
        d_norms = np.linalg.norm(doc_vecs, axis=1)
        denom = d_norms * q_norm
        denom[denom == 0] = 1e-9
        sims = doc_vecs @ q_vec / denom

        top_indices = np.argsort(sims)[::-1][:top_k]
        return [(self.documents[i], float(sims[i])) for i in top_indices]


class MMRStoreRanker:
    """MMR retrieval over a Chroma-backed VectorStore. Wraps store's as_retriever."""

    def __init__(self, store: VectorStore):
        self.store = store

    def retrieve(self, query: str, top_k: int) -> List[Tuple[Document, float]]:
        """
        Retrieve up to top_k docs via MMR. Returns (doc, 1.0) tuples — Chroma's
        MMR doesn't surface scores, callers that fuse on rank (e.g. RRF) don't need them.
        """

        if self.store.vector_store is None:
            logger.error("MMRStoreRanker called but VectorStore has no loaded Chroma instance.")
            return []

        collection_size = self.store.vector_store._collection.count()
        retriever = self.store.vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={"k": top_k, "fetch_k": min(max(top_k * 5, 50), collection_size)},
        )
        results = retriever.invoke(query) or []
        logger.debug(f"MMR retrieved {len(results[:top_k])}/{top_k} chunks for query: '{query[:60]}...'")
        return [(doc, 1.0) for doc in results[:top_k]]
