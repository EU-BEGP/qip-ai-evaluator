# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from typing import Dict, List, Tuple
from langchain_core.documents import Document


def rrf_merge(ranked_lists: List[List[Tuple[Document, float]]], k: int = 60,) -> List[Document]:
    """
    Reciprocal Rank Fusion across multiple ranked lists. Uses source::chunk_index
    as dedup key. Returns deduplicated docs ordered by descending RRF score.
    """

    scores: Dict[str, float] = {}
    doc_map: Dict[str, Document] = {}

    for ranked in ranked_lists:
        for rank, (doc, _) in enumerate(ranked):
            chunk_idx = doc.metadata.get("chunk_index")
            source = doc.metadata.get("source", "")
            if chunk_idx is not None:
                key = f"{source}::{chunk_idx}"
            else:
                key = doc.page_content[:80]
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
            if key not in doc_map:
                doc_map[key] = doc

    return [doc_map[k] for k in sorted(scores, key=lambda x: scores[x], reverse=True)]
