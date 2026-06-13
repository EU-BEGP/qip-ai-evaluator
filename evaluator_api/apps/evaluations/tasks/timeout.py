# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging

from celery import shared_task

from apps.evaluations.models import Evaluation, Scan
from apps.evaluations.services import watchdog_service as watchdog

logger = logging.getLogger(__name__)


@shared_task
def async_check_evaluation_timeout(evaluation_id, scans_to_run, run_id=None):
    """
    Heartbeat watchdog: fires INACTIVITY_TIMEOUT seconds after the last criterion result.
    Reschedules itself while progress continues; triggers failure only on true silence.
    """

    from apps.evaluations.services.life_cycle_service import LifecycleService

    try:
        evaluation = Evaluation.objects.get(id=evaluation_id)
    except Evaluation.DoesNotExist:
        watchdog.disarm(evaluation_id, scans_to_run)
        logger.warning(f"Watchdog: Evaluation {evaluation_id} not found. Exiting.")
        return

    terminal = {Evaluation.Status.COMPLETED, Evaluation.Status.FAILED}
    if evaluation.status in terminal:
        watchdog.disarm(evaluation_id, scans_to_run)
        logger.info(f"Watchdog cleared for Evaluation {evaluation_id} (status={evaluation.status}).")
        return

    active_scans = list(
        Scan.objects.filter(
            evaluation_id=evaluation_id,
            scan_type__in=scans_to_run,
        ).exclude(
            status__in=[Scan.Status.COMPLETED, Scan.Status.FAILED]
        ).values_list("scan_type", flat=True)
    )

    if not active_scans:
        watchdog.disarm(evaluation_id, scans_to_run)
        logger.info(f"Watchdog cleared for Evaluation {evaluation_id}. All scans finished.")
        return

    stuck_scans = []
    min_remaining = watchdog.WATCHDOG_INACTIVITY_TIMEOUT
    for scan_type in active_scans:
        elapsed = watchdog.elapsed_since_last_activity(evaluation_id, scan_type)
        if elapsed >= watchdog.WATCHDOG_INACTIVITY_TIMEOUT:
            stuck_scans.append(scan_type)
        else:
            min_remaining = min(min_remaining, watchdog.WATCHDOG_INACTIVITY_TIMEOUT - elapsed)

    if stuck_scans:
        logger.error(
            f"Watchdog triggered! Scans {stuck_scans} inactive on Evaluation {evaluation_id}. Marking as FAILED."
        )
        LifecycleService.mark_failed(
            evaluation=evaluation,
            scan_types=stuck_scans,
            reason=f"AI service timed out after {watchdog.WATCHDOG_INACTIVITY_TIMEOUT // 60} minutes of inactivity.",
            run_id=run_id,
        )
        remaining_active = [s for s in active_scans if s not in stuck_scans]
        if remaining_active:
            async_check_evaluation_timeout.apply_async(
                args=[evaluation_id, remaining_active, run_id],
                countdown=watchdog.WATCHDOG_INACTIVITY_TIMEOUT,
            )
    else:
        async_check_evaluation_timeout.apply_async(
            args=[evaluation_id, active_scans, run_id],
            countdown=int(min_remaining) + 10,
        )
        logger.info(
            f"Watchdog rescheduled for Evaluation {evaluation_id} in {int(min_remaining) + 10}s."
        )
