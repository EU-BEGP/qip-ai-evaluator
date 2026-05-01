# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging
import time
from celery import shared_task

from django.db.models import Count
from django.db import transaction
from apps.evaluations.models import Evaluation, Scan, Module
from apps.evaluations.services.life_cycle_service import LifecycleService
from apps.evaluations.services.rag_service import RagService

logger = logging.getLogger(__name__)

WATCHDOG_INACTIVITY_TIMEOUT = 5 * 60  # Seconds of silence before a scan is considered STUCK
WATCHDOG_CACHE_KEY = "watchdog:last_activity:{}"


@shared_task
def async_sync_module_metadata(evaluation_id):
    """Retrieves the RAG metadata in the background without blocking the user."""

    try:
        evaluation = Evaluation.objects.select_related('module').get(id=evaluation_id)

        LifecycleService.fetch_and_update_metadata(evaluation)

        evaluation.refresh_from_db()
        if evaluation.metadata_json and 'title' in evaluation.metadata_json:
            new_title = RagService.clean_title(evaluation.metadata_json['title'])
            evaluation.title = new_title
            evaluation.module.title = new_title

            evaluation.module.save(update_fields=['title'])
            evaluation.save(update_fields=['title'])

        logger.info(f"Metadata synced successfully for Evaluation ID {evaluation_id}")

    except Evaluation.DoesNotExist:
        logger.error(f"Evaluation ID {evaluation_id} does not exist. Metadata sync failed.")
    except Exception as e:
        logger.error(f"Error in async metadata task for Evaluation ID {evaluation_id}: {str(e)}")


@shared_task(bind=True, max_retries=10)
def async_trigger_rag_evaluation(self, evaluation_id, scans_to_run, payload):
    """
    Triggers the external RAG API safely and handles rollbacks if the service is down.
    Guarantees at most one snapshot generation per evaluation at a time
    Re-reads the snapshot from the DB and uses a Redis lock so only one task generates it
    """

    from django.core.cache import cache

    logger.info(f"[Eval {evaluation_id}] RAG trigger task attempt {self.request.retries + 1}")

    # Re-read: snapshot may have arrived since this task was queued.
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

    # Still no snapshot: enforce single-generator lock.
    if not payload.get("existing_snapshot"):
        lock_key = f"snapshot:lock:{evaluation_id}"
        is_first = cache.add(lock_key, "1", timeout=600)
        if not is_first:
            logger.info(
                f"[Eval {evaluation_id}] Snapshot generation already in progress. "
                f"Retrying in 10 s (attempt {self.request.retries + 1}/{self.max_retries})"
            )
            raise self.retry(countdown=10)
        logger.info(f"[Eval {evaluation_id}] Snapshot lock acquired — this task will generate the snapshot")

    try:
        RagService.trigger_evaluation(payload)
        logger.info(f"[Eval {evaluation_id}] RAG triggered successfully")

    except Exception as e:
        logger.error(f"[Eval {evaluation_id}] RAG trigger failed: {e}")
        Scan.objects.filter(evaluation_id=evaluation_id, scan_type__in=scans_to_run).update(status=Scan.Status.FAILED)
        Evaluation.objects.filter(id=evaluation_id).update(status=Evaluation.Status.FAILED)


@shared_task
def async_check_evaluation_timeout(evaluation_id, scans_to_run):
    """
    Heartbeat watchdog: fires INACTIVITY_TIMEOUT seconds after the last criterion result.
    Reschedules itself while progress continues; triggers failure only on true silence.
    """

    from django.core.cache import cache
    from apps.evaluations.services.webhooks_service import WebhookHandlerService

    cache_key = WATCHDOG_CACHE_KEY.format(evaluation_id)

    try:
        evaluation = Evaluation.objects.get(id=evaluation_id)
    except Evaluation.DoesNotExist:
        cache.delete(cache_key)
        logger.warning(f"Watchdog: Evaluation {evaluation_id} not found. Exiting.")
        return

    terminal = {Evaluation.Status.COMPLETED, Evaluation.Status.FAILED}
    if evaluation.status in terminal:
        cache.delete(cache_key)
        logger.info(f"Watchdog cleared for Evaluation {evaluation_id} (status={evaluation.status}).")
        return

    # Check for scans that haven't finished yet (PENDING or IN_PROGRESS)
    active_scans = list(
        Scan.objects.filter(
            evaluation_id=evaluation_id,
            scan_type__in=scans_to_run,
        ).exclude(
            status__in=[Scan.Status.COMPLETED, Scan.Status.FAILED]
        ).values_list("scan_type", flat=True)
    )

    if not active_scans:
        cache.delete(cache_key)
        logger.info(f"Watchdog cleared for Evaluation {evaluation_id}. All scans finished.")
        return

    last_activity = cache.get(cache_key)

    if last_activity is None:
        elapsed = WATCHDOG_INACTIVITY_TIMEOUT
    else:
        elapsed = time.time() - last_activity

    if elapsed >= WATCHDOG_INACTIVITY_TIMEOUT:
        logger.error(
            f"Watchdog triggered! Scans {active_scans} inactive for {elapsed:.0f}s "
            f"on Evaluation {evaluation_id}. Marking as FAILED."
        )
        WebhookHandlerService._handle_failure(evaluation, {
            "scan_names": active_scans,
            "error": f"AI service timed out after {WATCHDOG_INACTIVITY_TIMEOUT // 60} minutes of inactivity.",
        })
        cache.delete(cache_key)
    else:
        remaining = WATCHDOG_INACTIVITY_TIMEOUT - elapsed
        async_check_evaluation_timeout.apply_async(
            args=[evaluation_id, scans_to_run],
            countdown=int(remaining) + 10,
        )
        logger.info(
            f"Watchdog rescheduled for Evaluation {evaluation_id} "
            f"in {int(remaining) + 10}s (last activity {elapsed:.0f}s ago)."
        )


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 5 * 60})
def cleanup_module_evaluations(self, limit=4):
    """Cleans up old evaluations for modules that have more than a certain number of evaluations."""

    try:
        module_ids = (
            Module.objects
            .annotate(eval_count=Count("evaluations"))
            .filter(eval_count__gt=limit)
            .values_list("id", flat=True)
            .iterator(chunk_size=200)
        )

        for m_id in module_ids:
            with transaction.atomic():
                keep_ids = list(
                    Evaluation.objects
                    .filter(module_id=m_id)
                    .order_by("-created_at")
                    .values_list("id", flat=True)[:limit]
                )

                deleted_count, _ = (
                    Evaluation.objects
                    .filter(module_id=m_id)
                    .exclude(id__in=keep_ids)
                    .delete()
                )

                if deleted_count:
                    logger.info(f"Cleanup module {m_id}: {deleted_count} deleted")

    except Exception as exc:
        logger.error(f"Critical cleanup error: {exc}")
        raise self.retry(exc=exc)
