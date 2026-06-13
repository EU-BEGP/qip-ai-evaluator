# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging
from typing import List, Optional, Tuple
from langchain_core.documents import Document
from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """Cross-encoder reranker for an already-retrieved candidate set."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L6-v2"):
        self.cross_encoder = CrossEncoder(model_name)

    def rerank(self, query: str, documents: List[Document], top_k: int = 10, batch_size: int = 64) -> List[Tuple[Document, str, float]]:
        """
        Rank candidates by cross-encoder relevance and return the top_k in RELEVANCE order (highest score first). 
        Downstream callers are responsible for any final ordering (e.g., by chunk_index for reader-facing display).
        """

        if not documents:
            logger.error("rerank called but no documents provided.")
            raise ValueError("No documents provided to rerank.")

        cross_input = [(query, doc.page_content) for doc in documents]
        scores: List[float] = []
        for i in range(0, len(cross_input), batch_size):
            batch = cross_input[i:i + batch_size]
            scores.extend(self.cross_encoder.predict(batch))

        scored_docs = [(doc, doc.page_content, score) for doc, score in zip(documents, scores)]
        ranked_by_score = sorted(scored_docs, key=lambda x: x[2], reverse=True)

        # Deduplicate by source::chunk_index to handle multi-file KB collections
        seen_keys = set()
        top_docs: List[Tuple[Document, str, float]] = []
        for doc, text, score in ranked_by_score:
            chunk_idx = doc.metadata.get("chunk_index")
            source = doc.metadata.get("source", "")
            key = f"{source}::{chunk_idx}" if chunk_idx is not None else doc.page_content[:80]
            if key not in seen_keys:
                top_docs.append((doc, text, score))
                seen_keys.add(key)
            if len(top_docs) >= top_k:
                break

        return top_docs

    def rank_chunks(self, query: str, documents: Optional[List[Document]] = None,
                    top_k: int = 10, batch_size: int = 64) -> List[Tuple[Document, str, float]]:
        return self.rerank(query, documents or [], top_k=top_k, batch_size=batch_size)
