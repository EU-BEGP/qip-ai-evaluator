# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging
import time
from typing import Dict, List, Optional, Tuple
from langchain_core.documents import Document

from rag.prompts import build_batch_evaluation_prompt, build_previous_eval_section

logger = logging.getLogger(__name__)


def format_chunk(doc: Document) -> str:
    """Prepend heading_path context to chunk content when available."""

    heading = doc.metadata.get("heading_path", "")
    return f"[{heading}]\n{doc.page_content}" if heading else doc.page_content


def build_merged_query(batch: List[Dict]) -> str:
    """Join a criteria batch's names + descriptions into one retrieval query."""

    return " | ".join(f"{c['name']}: {c['description']}" for c in batch)


def evaluate_batch(llm, batch: List[Dict], doc_chunks: List[Document], kb_chunks: List[Document],
                   scan_name: str, document_snapshot: str, previous_evaluation: Optional[Dict],
                   course_key: Optional[str] = None) -> Tuple[List, float]:
    """
    Run a single LLM call over a batch of criteria.
    Returns (List[CriterionEvaluation], elapsed_seconds).
    """

    doc_text = "\n\n".join(format_chunk(d) for d in doc_chunks)
    kb_text = "\n\n".join(d.page_content for d in kb_chunks)
    prev_sections = [
        build_previous_eval_section(previous_evaluation, scan_name, c["name"])
        for c in batch
    ]
    prompt = build_batch_evaluation_prompt(
        batch, doc_text, kb_text, document_snapshot, prev_sections
    )

    start = time.time()
    result = llm.run_prompt(
        prompt,
        mode="batch_criterion",
        remember=False,
        prompt_cache_key=course_key,
    )
    logger.debug(result)
    return result.evaluations, time.time() - start
