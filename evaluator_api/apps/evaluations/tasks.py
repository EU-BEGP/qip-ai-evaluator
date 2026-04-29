# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging
from celery import shared_task

from django.db.models import Count
from django.db import transaction
from apps.evaluations.models import Evaluation, Scan, Module
from apps.evaluations.services.life_cycle_service import LifecycleService
from apps.evaluations.services.rag_service import RagService

logger = logging.getLogger(__name__)


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
    """Checks if scans are still stuck in IN_PROGRESS after a timeout period and marks them as FAILED."""

    from apps.evaluations.services.webhooks_service import WebhookHandlerService

    logger.info(f"Watchdog checking for timeout on Evaluation ID {evaluation_id}")

    try:
        stuck_scans = Scan.objects.filter(
            evaluation_id=evaluation_id,
            scan_type__in=scans_to_run,
            status=Scan.Status.IN_PROGRESS
        )

        if stuck_scans.exists():
            logger.error(
                f"Watchdog triggered! Scans {scans_to_run} timed out for Evaluation {evaluation_id}. Marking as FAILED."
            )
            evaluation = Evaluation.objects.get(id=evaluation_id)
            timeout_payload = {
                "scan_names": scans_to_run,
                "error": "The AI service took too long to respond (Timeout)."
            }
            WebhookHandlerService._handle_failure(evaluation, timeout_payload)

        else:
            logger.info(f"Watchdog cleared for Evaluation ID {evaluation_id}. No stuck scans found.")

    except Exception as e:
        logger.error(f"Error in Watchdog task for Evaluation {evaluation_id}: {str(e)}")


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
