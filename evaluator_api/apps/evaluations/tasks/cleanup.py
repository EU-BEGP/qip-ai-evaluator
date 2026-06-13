# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging
from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from apps.evaluations.models import Evaluation, Module, Scan
from apps.evaluations.services.life_cycle_service import LifecycleService

logger = logging.getLogger(__name__)

SAFETY_NET_INACTIVITY_MINUTES = 10


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


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 3, "countdown": 5 * 60})
def cleanup_orphaned_scans(self):
    """Safety net for scans whose watchdog never fired. Marks long-inactive IN_PROGRESS scans as FAILED."""

    cutoff = timezone.now() - timedelta(minutes=SAFETY_NET_INACTIVITY_MINUTES)
    stuck_scans = (
        Scan.objects
        .filter(status=Scan.Status.IN_PROGRESS, updated_at__lt=cutoff)
        .select_related('evaluation')
    )

    grouped = {}
    for scan in stuck_scans:
        grouped.setdefault(scan.evaluation, []).append(scan.scan_type)

    if not grouped:
        logger.debug("Safety net: no orphaned scans detected.")
        return

    for evaluation, scan_types in grouped.items():
        LifecycleService.mark_failed(
            evaluation=evaluation,
            scan_types=scan_types,
            reason=f"Orphaned scan detected by safety net (inactive for >{SAFETY_NET_INACTIVITY_MINUTES} min).",
        )
        logger.warning(
            f"Safety net failed {len(scan_types)} orphaned scan(s) for evaluation {evaluation.id}"
        )
