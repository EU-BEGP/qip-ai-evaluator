# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging
import uuid

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from django.core.cache import cache

from apps.evaluations.models import Evaluation
from apps.evaluations.services.rag_service import RagService
from apps.evaluations.services import watchdog_service as watchdog
from apps.evaluations.services.life_cycle_service import LifecycleService
from apps.evaluations.tasks.timeout import async_check_evaluation_timeout

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=10)
def async_trigger_rag_evaluation(self, evaluation_id, scans_to_run, payload):
    """Triggers the external RAG API safely and handles rollbacks if the service is down."""

    logger.info(f"[Eval {evaluation_id}] RAG trigger task attempt {self.request.retries + 1}")

    if not payload.get("existing_snapshot"):
        fresh = (
            Evaluation.objects
            .filter(id=evaluation_id)
            .values_list("document_snapshot", flat=True)
            .first()
        )
        if fresh:
            payload["existing_snapshot"] = fresh
            logger.info(f"[Eval {evaluation_id}] Snapshot picked up from DB")

    snapshot_resolved = cache.get(f"snapshot:resolved:{evaluation_id}")

    if not payload.get("existing_snapshot") and not snapshot_resolved:
        lock_key = f"snapshot:lock:{evaluation_id}"
        is_first = cache.add(lock_key, "1", timeout=600)
        if not is_first:
            logger.info(
                f"[Eval {evaluation_id}] Snapshot generation already in progress. "
                f"Retrying in 10 s (attempt {self.request.retries + 1}/{self.max_retries})"
            )
            try:
                raise self.retry(countdown=10)
            except MaxRetriesExceededError:
                evaluation = Evaluation.objects.filter(id=evaluation_id).first()
                if evaluation:
                    LifecycleService.mark_failed(
                        evaluation=evaluation,
                        scan_types=scans_to_run,
                        reason="Snapshot generation retries exhausted while waiting for lock.",
                    )
                return
        logger.info(f"[Eval {evaluation_id}] Snapshot lock acquired — this task will generate the snapshot")
    elif snapshot_resolved and not payload.get("existing_snapshot"):
        logger.info(f"[Eval {evaluation_id}] Snapshot already resolved (full-module mode), skipping lock")

    run_id = str(uuid.uuid4())
    payload["run_id"] = run_id

    try:
        RagService.trigger_evaluation(payload)
        logger.info(f"[Eval {evaluation_id}] RAG triggered successfully (run_id={run_id})")

        watchdog.arm(evaluation_id, scans_to_run)
        async_check_evaluation_timeout.apply_async(
            args=[evaluation_id, scans_to_run, run_id],
            countdown=watchdog.WATCHDOG_INACTIVITY_TIMEOUT,
        )
        logger.info(f"Watchdog armed for Evaluation {evaluation_id} (run_id={run_id})")

    except Exception as e:
        logger.error(f"[Eval {evaluation_id}] RAG trigger failed: {e}")
        evaluation = Evaluation.objects.filter(id=evaluation_id).first()
        if evaluation:
            LifecycleService.mark_failed(
                evaluation=evaluation,
                scan_types=scans_to_run,
                reason=f"RAG trigger failed: {e}",
                run_id=run_id,
            )


@shared_task
def async_cancel_rag_evaluation(run_id):
    """Sends a cancel signal to the RAG API for the given run_id."""

    if not run_id:
        logger.warning("async_cancel_rag_evaluation called with no run_id — nothing to cancel.")
        return
    RagService.cancel_evaluation(run_id)


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 5 * 60})
def async_sync_module_metadata(self, evaluation_id):
    """Retrieves the RAG metadata in the background without blocking the user."""

    try:
        evaluation = Evaluation.objects.select_related('module').get(id=evaluation_id)
    except Evaluation.DoesNotExist:
        logger.error(f"Evaluation ID {evaluation_id} does not exist. Metadata sync failed.")
        return

    LifecycleService.fetch_and_update_metadata(evaluation)

    evaluation.refresh_from_db()
    if evaluation.metadata_json and 'title' in evaluation.metadata_json:
        new_title = RagService.clean_title(evaluation.metadata_json['title'])
        evaluation.title = new_title
        evaluation.module.title = new_title

        evaluation.module.save(update_fields=['title'])
        evaluation.save(update_fields=['title'])

    logger.info(f"Metadata synced successfully for Evaluation ID {evaluation_id}")
