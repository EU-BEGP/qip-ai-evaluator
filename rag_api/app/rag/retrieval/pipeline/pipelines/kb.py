# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging
from typing import List, Optional
from langchain_core.documents import Document

from ...rankers import CrossEncoderReranker
from ..hybrid import HybridRetriever

logger = logging.getLogger(__name__)


class KBRetrievalPipeline:
    """Hybrid retrieve over the KB, then rerank a deduplicated candidate set."""

    def __init__(self, hybrid: HybridRetriever, reranker: CrossEncoderReranker):
        self.hybrid = hybrid
        self.reranker = reranker

    def retrieve(self, query: str, top_k: int, exclude_docs: Optional[List[Document]] = None) -> List[Document]:
        """Return up to top_k KB docs ranked by the cross-encoder, excluding any duplicates of exclude_docs."""

        _sparse, _dense, candidates = self.hybrid.retrieve(query)

        if exclude_docs:
            seen = {d.page_content for d in exclude_docs}
            candidates = [c for c in candidates if c.page_content not in seen]

        if not candidates:
            return []

        ranked = self.reranker.rerank(query, candidates, top_k=top_k)
        return [doc for doc, _, _ in ranked]
