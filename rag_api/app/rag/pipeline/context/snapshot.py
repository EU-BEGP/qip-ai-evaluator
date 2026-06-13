# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from typing import List
from langchain_core.documents import Document

from rag.prompts import build_snapshot_prompt
from rag.retrieval import CrossEncoderReranker


def build_module_snapshot(documents: List[Document], reranker: CrossEncoderReranker, llm,
                          total_chunks_to_use: int = 20, first_n_chunks: int = 5, top_k_chunks: int = 15) -> str:
    """
    Build a compact LLM-generated digest using a smart-chunking strategy.
    Selects the first N chunks (intro / preamble) plus the top K semantically relevant chunks (reranked against a heading-oriented query) to keep the
    snapshot prompt within safe bounds on large modules while preserving the most informative content.
    """

    if not documents:
        return ""

    if len(documents) <= total_chunks_to_use:
        selected_chunks = documents
    else:
        first_block = documents[:first_n_chunks]
        remaining = documents[first_n_chunks:]

        search_query = (
            "Document Title, Abstract, Keywords, "
            "Intended Learning Outcomes, Outline, Table of Contents, Main Headings"
        )
        ranked_remaining = reranker.rerank(search_query, documents=remaining, top_k=top_k_chunks)
        top_chunks = [doc for doc, _, _ in ranked_remaining]
        top_chunks.sort(key=lambda doc: doc.metadata.get("chunk_index", 0))
        selected_chunks = first_block + top_chunks

    full_text = "\n\n".join(d.page_content for d in selected_chunks)
    return llm.run_prompt(build_snapshot_prompt(full_text), mode="snapshot", remember=True)
