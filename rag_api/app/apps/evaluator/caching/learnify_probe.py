# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging
from typing import Callable, Optional

from django.core.cache import cache

from rag.document_processing.processors.learnify import LearnifyUnavailableError
from .primitives import (
    LAST_MODIFIED_CACHE_TTL,
    LAST_MODIFIED_LOCK_TTL,
    LEARNIFY_DOWN_TTL,
    LEARNIFY_NOT_FOUND_TTL,
    acquire_or_build,
)

logger = logging.getLogger(__name__)


def last_modified_key(course_key: str) -> str:
    return f"module:last_modified:{course_key}"


def last_modified_lock_key(course_key: str) -> str:
    return f"module:lock:last_modified:{course_key}"


def last_modified_down_key(course_key: str) -> str:
    return f"module:last_modified:down:{course_key}"


def last_modified_not_found_key(course_key: str) -> str:
    return f"module:last_modified:not_found:{course_key}"


def acquire_last_modified(course_key: str, fetch_fn: Callable[[], Optional[str]],
                          force: bool = False) -> Optional[str]:
    """
    Return Learnify last_modified from the Redis cache, or call fetch_fn once across all processes.
    Two short fast-fail markers spare Learnify from burst re-fetches: "down" makes callers
    raise LearnifyUnavailableError, "not_found" makes them return None.
    """

    down_key = last_modified_down_key(course_key)
    not_found_key = last_modified_not_found_key(course_key)

    if cache.get(down_key):
        logger.info(f"Learnify marked down for '{course_key}', failing fast.")
        raise LearnifyUnavailableError(f"Learnify recently unreachable for '{course_key}'.")

    if cache.get(not_found_key):
        logger.info(f"Module '{course_key}' marked not-found (absent in Learnify), failing fast.")
        return None

    def guarded_fetch():
        try:
            result = fetch_fn()
        except LearnifyUnavailableError:
            cache.set(down_key, "1", timeout=LEARNIFY_DOWN_TTL)
            raise
        if result is None:
            cache.set(not_found_key, "1", timeout=LEARNIFY_NOT_FOUND_TTL)
        else:
            cache.delete(down_key)
            cache.delete(not_found_key)
        return result

    return acquire_or_build(
        data_key=last_modified_key(course_key),
        lock_key=last_modified_lock_key(course_key),
        ttl=LAST_MODIFIED_CACHE_TTL,
        lock_ttl=LAST_MODIFIED_LOCK_TTL,
        build_fn=guarded_fetch,
        force=force,
    )
