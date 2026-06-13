# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from typing import List, Tuple

import bm25s
from langchain_core.documents import Document


class BM25Ranker:
    """BM25 index over a fixed document corpus, backed by bm25s (Lù, 2024)."""

    def __init__(self, documents: List[Document], k1: float = 1.5, b: float = 0.75):
        self.docs = documents
        self.k1 = k1
        self.b = b
        self._build()

    def _build(self) -> None:
        corpus = [d.page_content for d in self.docs]
        corpus_tokens = bm25s.tokenize(corpus, stopwords=None, show_progress=False)
        self.retriever = bm25s.BM25(k1=self.k1, b=self.b)
        self.retriever.index(corpus_tokens)

    def retrieve(self, query: str, top_k: int) -> List[Tuple[Document, float]]:
        """Return top_k documents with positive BM25 scores, ordered by score desc."""

        query_tokens = bm25s.tokenize([query], stopwords=None, show_progress=False)
        k = min(top_k, len(self.docs))
        results, scores = self.retriever.retrieve(query_tokens, corpus=self.docs, k=k)
        return [
            (doc, float(score))
            for doc, score in zip(results[0], scores[0])
            if score > 0
        ]
