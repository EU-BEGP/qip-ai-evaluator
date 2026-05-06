# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging
from typing import Dict, List, Optional
import redis as _redis_lib

from celery import shared_task
from django.conf import settings

EVAL_CANCELLED_KEY = "eval:cancelled:{}"

_redis_client = None


def _get_redis():
    global _redis_client
    if _redis_client is None:
        _redis_client = _redis_lib.from_url(settings.CELERY_BROKER_URL)
    return _redis_client


class EvaluationCancelledError(Exception):
    pass

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
    run_id: Optional[str] = None,
):
    """Run a full module evaluation asynchronously in a Celery worker."""

    log_id = evaluation_id or "No-ID"
    logger.info(f"[{log_id}] Task started for course '{original_link}'")
    logger.info(f"[{log_id}] Scans to run: {'ALL' if not scan_names else scan_names}")
    if previous_evaluation:
        logger.info(f"[{log_id}] Using previous evaluation data.")
    try:
        # Checkpoint 1: cancel before any work begins
        if run_id and _get_redis().exists(EVAL_CANCELLED_KEY.format(run_id)):
            raise EvaluationCancelledError(f"Task cancelled before start (run_id={run_id})")

        evaluator = ContentEvaluator(
            vector_manager=GLOBAL_VECTOR_MANAGER,
            rag_model=GLOBAL_RAG_MODEL,
        )
        # Verify module exists in Learnify before processing
        try:
            last_mod = evaluator.get_module_last_modified(course_key)
            if not last_mod:
                raise ValueError("Learnify returned empty modified date.")
        except EvaluationCancelledError:
            raise
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
                run_id=run_id,
            )
            return

        docs = evaluator.vector_manager.load_documents([course_key])
        if not docs:
            logger.error(f"[{log_id}] No documents found for course_key '{course_key}'.")
            send_callback(
                callback_url, original_link, "FAILED",
                error="No documents found", results=None,
                evaluation_id=evaluation_id, qip_user_id=qip_user_id,
                run_id=run_id,
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
                run_id=run_id,
            )

        def interim_callback_fn(interim_json):
            # Checkpoint 2: cancel between criteria
            if run_id and _get_redis().exists(EVAL_CANCELLED_KEY.format(run_id)):
                raise EvaluationCancelledError(f"Task cancelled at interim checkpoint (run_id={run_id})")
            send_interim_callback(
                callback_url=callback_url,
                interim_json=interim_json,
                course_key=original_link,
                evaluation_id=evaluation_id,
                qip_user_id=qip_user_id,
                run_id=run_id,
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
                run_id=run_id,
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
                run_id=run_id,
            )

    except EvaluationCancelledError:
        logger.info(f"[{log_id}] Evaluation cancelled (run_id={run_id}).")

    except Exception as e:
        logger.error(f"[{log_id}] Evaluation task failed: {e}", exc_info=True)
        send_callback(
            callback_url, original_link, "FAILED",
            error=str(e), results=None,
            evaluation_id=evaluation_id, qip_user_id=qip_user_id,
            run_id=run_id,
        )

    finally:
        if run_id:
            _get_redis().delete(EVAL_CANCELLED_KEY.format(run_id))
