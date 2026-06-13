# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging
import time
import uuid
from typing import Callable

from django.core.cache import cache

logger = logging.getLogger(__name__)

# --- TTLs (sliding for cached values, hard for locks) ---
DOCS_CACHE_TTL = 300            # 5 min idle for parsed Learnify docs
METADATA_CACHE_TTL = 300        # 5 min idle for LLM-extracted metadata
SNAPSHOT_CACHE_TTL = 300        # 5 min idle for document snapshot
LAST_MODIFIED_CACHE_TTL = 60    # 1 min for Learnify last_modified
LEARNIFY_DOWN_TTL = 30          # Down-marker window for fast-fail during Learnify outages
LEARNIFY_NOT_FOUND_TTL = 30     # Not-found marker window for fast-fail on modules with no Module/Chapter section
DATA_LOCK_TTL = 180             # 3 min max for a docs/metadata/snapshot build under a lock
LAST_MODIFIED_LOCK_TTL = 30     # 30 s max for a last_modified fetch under a lock
POLL_INTERVAL = 1.0             # Seconds between cache polls while waiting on another process
EMBEDDINGS_LRU_MAX = 50         # Max entries kept in the per-process embeddings cache


class ModuleCacheEntry:
    """Lightweight container returned to callers of acquire_module_data."""

    __slots__ = ("docs", "snapshot", "doc_embeddings")

    def __init__(self, docs=None, snapshot=None, doc_embeddings=None):
        self.docs = docs
        self.snapshot = snapshot
        self.doc_embeddings = doc_embeddings


def lock_key(name: str, cache_key: tuple) -> str:
    """Generic lock-key builder shared by every (course_key, last_modified)-scoped cache tier."""

    return f"module:lock:{name}:{cache_key[0]}:{cache_key[1]}"


def acquire_or_build(data_key: str, lock_key: str, ttl: int, lock_ttl: int,
                     build_fn: Callable, force: bool = False, sliding: bool = True):
    """
    Cross-process dedup over a cache: on a miss, one caller wins the SETNX lock and builds
    while the rest wait and share its outcome (no caller ever re-fetches). A None result is
    never cached, so the next request retries fresh.
    """

    if not force:
        cached = cache.get(data_key)
        if cached is not None:
            if sliding:
                cache.touch(data_key, ttl)
            return cached

    lock_token = uuid.uuid4().hex
    lock_acquired = cache.add(lock_key, lock_token, timeout=lock_ttl)

    if not lock_acquired:
        logger.info(f"Build for '{data_key}' running on another process, polling...")
        max_polls = max(1, int(lock_ttl / POLL_INTERVAL))
        for _ in range(max_polls):
            time.sleep(POLL_INTERVAL)
            cached = cache.get(data_key)
            if cached is not None:
                logger.info(f"Cache populated by another process for '{data_key}'.")
                return cached
            if not cache.get(lock_key):
                # Builder released the lock; re-check once. No value - it failed - share the failure.
                cached = cache.get(data_key)
                if cached is not None:
                    return cached
                logger.info(f"Builder for '{data_key}' failed; sharing the failure without re-fetching.")
                return None
        logger.warning(f"Polling for '{data_key}' timed out; giving up without re-fetching.")
        return None

    try:
        result = build_fn()
        if result is not None:
            cache.set(data_key, result, timeout=ttl)
        return result
    finally:
        if cache.get(lock_key) == lock_token:
            cache.delete(lock_key)
