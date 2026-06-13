# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from typing import List, Tuple
import tiktoken
from langchain_core.documents import Document

DEFAULT_TOKEN_ENCODING = "cl100k_base"


def count_tokens(documents: List[Document], token_encoding: str = DEFAULT_TOKEN_ENCODING) -> int:
    """Total token count across all document page_content under the given encoding."""

    if not documents:
        return 0
    enc = tiktoken.get_encoding(token_encoding)
    return sum(len(enc.encode(doc.page_content)) for doc in documents)


def select_by_token_budget(ranked: List[Tuple[Document, str, float]], budget: int,
                           token_encoding: str = DEFAULT_TOKEN_ENCODING) -> List[Document]:
    """
    Pick chunks in rank order until token budget is exhausted, then restore
    document order by chunk_index.
    """

    enc = tiktoken.get_encoding(token_encoding)
    selected: List[Document] = []
    used = 0
    for doc, _, _ in ranked:
        cost = len(enc.encode(doc.page_content))
        if used + cost > budget:
            break
        selected.append(doc)
        used += cost
    return sorted(selected, key=lambda d: d.metadata.get("chunk_index", 0))
