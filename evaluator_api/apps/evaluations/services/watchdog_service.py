# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging
import time

from django.core.cache import cache

from apps.evaluations.models import Scan

logger = logging.getLogger(__name__)

WATCHDOG_INACTIVITY_TIMEOUT = 5 * 60
WATCHDOG_KEY_TEMPLATE = "watchdog:last_activity:{}:{}"
WATCHDOG_CACHE_TTL = 7200


def _key(evaluation_id, scan_type):
    safe_scan = scan_type.replace(" ", "_") if scan_type else scan_type
    return WATCHDOG_KEY_TEMPLATE.format(evaluation_id, safe_scan)


def arm(evaluation_id, scan_types):
    """Sets the activity timestamp for each scan being watched."""

    now = time.time()
    for scan_type in scan_types:
        cache.set(_key(evaluation_id, scan_type), now, timeout=WATCHDOG_CACHE_TTL)
    logger.info(f"Watchdog armed for evaluation {evaluation_id}, scans: {scan_types}")


def refresh(evaluation_id, scan_type):
    """Updates the activity timestamp for a single scan."""

    cache.set(_key(evaluation_id, scan_type), time.time(), timeout=WATCHDOG_CACHE_TTL)


def disarm(evaluation_id, scan_types):
    """Clears the watchdog keys for the given scans."""

    for scan_type in scan_types:
        cache.delete(_key(evaluation_id, scan_type))
    logger.debug(f"Watchdog disarmed for evaluation {evaluation_id}, scans: {scan_types}")


def elapsed_since_last_activity(evaluation_id, scan_type):
    """Returns seconds since the last recorded activity for this scan."""

    cached = cache.get(_key(evaluation_id, scan_type))

    if cached is not None:
        return time.time() - cached

    scan = (
        Scan.objects
        .filter(evaluation_id=evaluation_id, scan_type=scan_type)
        .only("updated_at")
        .first()
    )
    if scan and scan.updated_at:
        return (time.time() - scan.updated_at.timestamp())

    return WATCHDOG_INACTIVITY_TIMEOUT
