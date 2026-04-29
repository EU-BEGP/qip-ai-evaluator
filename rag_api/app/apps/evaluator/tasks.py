# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging
from typing import Dict, List, Optional

from celery import shared_task
from django.conf import settings

from rag.rag_pipeline.content_evaluator import ContentEvaluator
from rag.retrievers.cross_encoder import CrossEncoderRAG
from .callbacks import send_callback, send_interim_callback, send_snapshot_callback
from .init_knowledge import build_knowledge_base_auto, load_criteria_auto

logger = logging.getLogger(__name__)

# --- Shared setup ---
logger.info("Initializing shared AI models (heavy resources)...")

GLOBAL_VECTOR_MANAGER = build_knowledge_base_auto()
load_criteria_auto()
GLOBAL_RAG_MODEL = CrossEncoderRAG(
    model_name="cross-encoder/ms-marco-MiniLM-L6-v2", use_memory_only=True
)
GLOBAL_EVALUATOR = ContentEvaluator(
    vector_manager=GLOBAL_VECTOR_MANAGER,
    rag_model=GLOBAL_RAG_MODEL,
)

logger.info("Shared AI models ready.")
# --- End of shared setup ---


@shared_task(bind=True)
def run_evaluation_task(
    self,
    course_key: str,
    original_link: str,
    callback_url: str,
    evaluation_id: Optional[str] = None,
    qip_user_id: Optional[str] = None,
    scan_names: Optional[List[str]] = None,
    previous_evaluation: Optional[Dict] = None,
    existing_snapshot: Optional[str] = None,
):
    """Run a full module evaluation asynchronously in a Celery worker."""

    log_id = evaluation_id or "No-ID"
    logger.info(f"[{log_id}] Task started for course '{original_link}'")
    logger.info(f"[{log_id}] Scans to run: {'ALL' if not scan_names else scan_names}")
    if previous_evaluation:
        logger.info(f"[{log_id}] Using previous evaluation data.")
    try:
        evaluator = GLOBAL_EVALUATOR
        # Verify module exists in Learnify before processing
        try:
            last_mod = evaluator.get_module_last_modified(course_key)
            if not last_mod:
                raise ValueError("Learnify returned empty modified date.")
        except Exception as e:
            logger.error(f"[{log_id}] Learnify check failed: {e}")
            send_callback(
                callback_url=callback_url,
                course_key=original_link,
                status="FAILED",
                results=None,
                error=f"Learnify Validation Failed: {str(e)}",
                evaluation_id=evaluation_id,
                qip_user_id=qip_user_id,
                scan_names=scan_names,
            )
            return

        docs = evaluator.vector_manager.load_documents([course_key])
        if not docs:
            logger.error(f"[{log_id}] No documents found for course_key '{course_key}'.")
            send_callback(
                callback_url, original_link, "FAILED",
                error="No documents found", results=None,
                evaluation_id=evaluation_id, qip_user_id=qip_user_id,
            )
            return

        for i, doc in enumerate(docs):
            doc.metadata["chunk_index"] = i + 1

        evaluator.set_documents_for_rag(docs, existing_snapshot=existing_snapshot)

        # Send snapshot back immediately when a new one was generated
        if not existing_snapshot and evaluator.document_snapshot:
            send_snapshot_callback(
                callback_url, evaluator.document_snapshot,
                original_link, evaluation_id, qip_user_id,
            )

        def interim_callback_fn(interim_json):
            send_interim_callback(
                callback_url=callback_url,
                interim_json=interim_json,
                course_key=original_link,
                evaluation_id=evaluation_id,
                qip_user_id=qip_user_id,
            )

        result_json, failed_scans = evaluator.evaluate(
            document_chunks=docs,
            k_doc=20,
            k_kb=5,
            course_key=course_key,
            scan_names=scan_names,
            previous_evaluation=previous_evaluation,
            interim_callback=interim_callback_fn,
        )

        if result_json and result_json.get("content"):
            send_callback(
                callback_url, original_link, "COMPLETE",
                results=result_json, error=None,
                evaluation_id=evaluation_id, qip_user_id=qip_user_id,
            )

        if failed_scans:
            logger.error(f"Sending FAILED callback for scans: {failed_scans}")
            send_callback(
                callback_url, original_link, "FAILED",
                results=None,
                error="Max retries exceeded during processing for Scan",
                evaluation_id=evaluation_id,
                qip_user_id=qip_user_id,
                scan_names=failed_scans,
            )

    except Exception as e:
        logger.error(f"[{log_id}] Evaluation task failed: {e}", exc_info=True)
        send_callback(
            callback_url, original_link, "FAILED",
            error=str(e), results=None,
            evaluation_id=evaluation_id, qip_user_id=qip_user_id,
        )
