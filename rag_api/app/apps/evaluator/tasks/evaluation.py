# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

from rag.pipeline.evaluator import ContentEvaluator
from ..callbacks import send_callback, send_interim_callback, send_snapshot_callback
from ..caching import ModuleCacheEntry, acquire_last_modified, acquire_module_data
from rag.document_processing.processors.learnify.client import fetch_module_last_modified
from .shared import (
    GLOBAL_KB_BM25,
    GLOBAL_RERANKER,
    GLOBAL_VECTOR_STORE,
    EvaluationCancelledError,
    clear_cancel,
    is_cancelled,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EvaluationContext:
    """Immutable task-scoped parameters passed to phase helpers."""

    course_key: str
    original_link: str
    callback_url: str
    evaluation_id: Optional[str]
    qip_user_id: Optional[str]
    run_id: Optional[str]
    scan_names: Optional[List[str]]
    previous_evaluation: Optional[Dict]
    existing_snapshot: Optional[str]


def _has_evaluable_content(docs: List) -> bool:
    """True when at least one document carries body text beyond bare title headings."""

    for doc in docs:
        for line in doc.page_content.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                return True
    return False


def _send_failed(ctx: EvaluationContext, error: str, scan_names: Optional[List[str]] = None) -> None:
    """Single point for emitting FAILED callbacks across the task."""

    send_callback(
        callback_url=ctx.callback_url,
        course_key=ctx.original_link,
        status="FAILED",
        results=None,
        error=error,
        evaluation_id=ctx.evaluation_id,
        qip_user_id=ctx.qip_user_id,
        scan_names=scan_names if scan_names is not None else ctx.scan_names,
        run_id=ctx.run_id,
    )


def _verify_module(ctx: EvaluationContext, evaluator: ContentEvaluator) -> Optional[str]:
    """Resolve module last_modified via Learnify. Emit FAILED callback and return None on failure."""

    try:
        last_mod = acquire_last_modified(
            ctx.course_key,
            lambda: fetch_module_last_modified(ctx.course_key),
            force=True,
        )
        if not last_mod:
            raise ValueError("Learnify returned empty modified date.")
        return last_mod
    except EvaluationCancelledError:
        raise
    except Exception as e:
        log_id = ctx.evaluation_id or "No-ID"
        logger.error(f"[{log_id}] Learnify check failed: {e}")
        _send_failed(ctx, f"Learnify Validation Failed: {str(e)}")
        return None


def _prepare_module_data(ctx: EvaluationContext, evaluator: ContentEvaluator, last_mod: str) -> ModuleCacheEntry:
    """Acquire (or build) cached docs + embeddings + snapshot for this module version."""

    cache_key = (ctx.course_key, last_mod)

    def load_docs():
        raw_docs = evaluator.vector_store.load_documents([ctx.course_key])
        if not raw_docs:
            raise ValueError(f"No documents found for course_key '{ctx.course_key}'.")
        if not _has_evaluable_content(raw_docs):
            raise ValueError("Module has no evaluable content.")
        for i, doc in enumerate(raw_docs):
            doc.metadata["chunk_index"] = i + 1
        return raw_docs

    def build_embeddings(docs):
        return evaluator.vector_store.embeddings.embed_documents(
            [d.page_content for d in docs]
        )

    def generate_snapshot(docs):
        evaluator.set_documents_for_rag(
            docs, doc_embeddings=None, existing_snapshot=None, generate_snapshot=True
        )
        return evaluator.document_snapshot

    return acquire_module_data(
        cache_key,
        load_docs,
        build_embeddings,
        generate_snapshot,
        existing_snapshot=ctx.existing_snapshot,
    )


def _emit_snapshot_if_new(ctx: EvaluationContext, evaluator: ContentEvaluator) -> None:
    """
    Signal snapshot phase complete when no existing snapshot was provided.
    Empty string signals full-module mode so the evaluator_api releases its snapshot lock.
    """

    if ctx.existing_snapshot:
        return
    send_snapshot_callback(
        ctx.callback_url,
        evaluator.document_snapshot or "",
        ctx.original_link,
        ctx.evaluation_id,
        ctx.qip_user_id,
        run_id=ctx.run_id,
    )


def _make_interim_callback(ctx: EvaluationContext) -> Callable[[dict], None]:
    """Return a per-criterion callback closure that checks cancel + dispatches the interim payload."""

    def interim_callback_fn(interim_json: dict) -> None:
        if is_cancelled(ctx.run_id):
            raise EvaluationCancelledError(
                f"Task cancelled at interim checkpoint (run_id={ctx.run_id})"
            )
        send_interim_callback(
            callback_url=ctx.callback_url,
            interim_json=interim_json,
            course_key=ctx.original_link,
            evaluation_id=ctx.evaluation_id,
            qip_user_id=ctx.qip_user_id,
            run_id=ctx.run_id,
        )

    return interim_callback_fn


def _execute_scans(ctx: EvaluationContext, evaluator: ContentEvaluator, docs: List) -> Tuple[Optional[dict], List[str]]:
    """Run the evaluation across scan_names. Returns (result_json, failed_scans)."""

    return evaluator.evaluate(
        document_chunks=docs,
        k_kb=5,
        course_key=ctx.course_key,
        scan_names=ctx.scan_names,
        previous_evaluation=ctx.previous_evaluation,
        interim_callback=_make_interim_callback(ctx),
    )


def _emit_final(ctx: EvaluationContext, result_json: Optional[dict], failed_scans: List[str]) -> None:
    """Send COMPLETE callback for the populated result and a FAILED callback for any failed scans."""

    if result_json and result_json.get("content"):
        send_callback(
            ctx.callback_url, ctx.original_link, "COMPLETE",
            results=result_json, error=None,
            evaluation_id=ctx.evaluation_id, qip_user_id=ctx.qip_user_id,
            run_id=ctx.run_id,
        )

    if failed_scans:
        logger.error(f"Sending FAILED callback for scans: {failed_scans}")
        _send_failed(
            ctx,
            "Max retries exceeded during processing for Scan",
            scan_names=failed_scans,
        )


@shared_task(bind=True)
def run_evaluation_task(self, course_key: str, original_link: str, callback_url: str,
                        evaluation_id: Optional[str] = None, qip_user_id: Optional[str] = None,
                        scan_names: Optional[List[str]] = None, previous_evaluation: Optional[Dict] = None,
                        existing_snapshot: Optional[str] = None, run_id: Optional[str] = None):
    """Run a full module evaluation asynchronously in a Celery worker."""

    ctx = EvaluationContext(
        course_key=course_key,
        original_link=original_link,
        callback_url=callback_url,
        evaluation_id=evaluation_id,
        qip_user_id=qip_user_id,
        run_id=run_id,
        scan_names=scan_names,
        previous_evaluation=previous_evaluation,
        existing_snapshot=existing_snapshot,
    )

    log_id = ctx.evaluation_id or "No-ID"
    logger.info(f"[{log_id}] Task started for course '{ctx.original_link}'")
    logger.info(f"[{log_id}] Scans to run: {'ALL' if not ctx.scan_names else ctx.scan_names}")
    if ctx.previous_evaluation:
        logger.info(f"[{log_id}] Using previous evaluation data.")

    try:
        if is_cancelled(ctx.run_id):
            raise EvaluationCancelledError(f"Task cancelled before start (run_id={ctx.run_id})")

        evaluator = ContentEvaluator(
            vector_store=GLOBAL_VECTOR_STORE,
            kb_bm25=GLOBAL_KB_BM25,
            reranker=GLOBAL_RERANKER,
        )

        last_mod = _verify_module(ctx, evaluator)
        if last_mod is None:
            return

        cache_entry = _prepare_module_data(ctx, evaluator, last_mod)
        evaluator.set_documents_for_rag(
            cache_entry.docs,
            doc_embeddings=cache_entry.doc_embeddings,
            existing_snapshot=cache_entry.snapshot,
        )
        _emit_snapshot_if_new(ctx, evaluator)

        result_json, failed_scans = _execute_scans(ctx, evaluator, cache_entry.docs)
        _emit_final(ctx, result_json, failed_scans)

    except EvaluationCancelledError:
        logger.info(f"[{log_id}] Evaluation cancelled (run_id={ctx.run_id}).")

    except SoftTimeLimitExceeded:
        logger.error(f"[{log_id}] Task exceeded time limit (run_id={ctx.run_id}).")
        _send_failed(ctx, "Evaluation timed out")

    except Exception as e:
        logger.error(f"[{log_id}] Evaluation task failed: {e}", exc_info=True)
        _send_failed(ctx, str(e))

    finally:
        clear_cancel(ctx.run_id)
