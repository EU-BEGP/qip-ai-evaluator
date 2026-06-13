# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging
import threading
from collections import OrderedDict
from typing import Callable, List, Optional

from django.core.cache import cache

from .primitives import (
    DATA_LOCK_TTL,
    DOCS_CACHE_TTL,
    EMBEDDINGS_LRU_MAX,
    ModuleCacheEntry,
    SNAPSHOT_CACHE_TTL,
    acquire_or_build,
    lock_key,
)

logger = logging.getLogger(__name__)


def docs_key(cache_key: tuple) -> str:
    return f"module:docs:{cache_key[0]}:{cache_key[1]}"


def snapshot_key(cache_key: tuple) -> str:
    return f"module:snapshot:{cache_key[0]}:{cache_key[1]}"


_embeddings_cache: "OrderedDict[tuple, List[List[float]]]" = OrderedDict()
_embeddings_cache_lock = threading.Lock()


def ensure_docs(cache_key: tuple, load_docs_fn: Callable[[], List]) -> List:
    """Returns docs from Redis cache or runs load_docs_fn once across all processes."""

    return acquire_or_build(
        data_key=docs_key(cache_key),
        lock_key=lock_key("docs", cache_key),
        ttl=DOCS_CACHE_TTL,
        lock_ttl=DATA_LOCK_TTL,
        build_fn=load_docs_fn,
    )


def get_or_build_embeddings(cache_key: tuple, build_fn: Callable[[], List[List[float]]]) -> List[List[float]]:
    """
    Per-process LRU cache for doc embeddings keyed by (course_key, last_modified).
    Same-process subsequent calls reuse without recomputing; bounded size keeps memory in check.
    """

    with _embeddings_cache_lock:
        cached = _embeddings_cache.get(cache_key)
        if cached is not None:
            _embeddings_cache.move_to_end(cache_key)
            return cached

    embeddings = build_fn()

    with _embeddings_cache_lock:
        _embeddings_cache[cache_key] = embeddings
        _embeddings_cache.move_to_end(cache_key)
        while len(_embeddings_cache) > EMBEDDINGS_LRU_MAX:
            _embeddings_cache.popitem(last=False)

    return embeddings


def acquire_snapshot(cache_key: tuple, build_fn: Callable[[], str],
                     existing_snapshot: Optional[str] = None) -> Optional[str]:
    """
    Returns the document snapshot for cache_key (LLM-generated digest or "" for full-module mode).
    When existing_snapshot is provided it is written through to the cache so any sibling on the same
    module version reuses it without regenerating. Otherwise the value is fetched from cache or built
    once (deduped via SETNX) and shared with concurrent callers.
    """

    key = snapshot_key(cache_key)

    if existing_snapshot is not None:
        cache.set(key, existing_snapshot, timeout=SNAPSHOT_CACHE_TTL)
        return existing_snapshot

    return acquire_or_build(
        data_key=key,
        lock_key=lock_key("snapshot", cache_key),
        ttl=SNAPSHOT_CACHE_TTL,
        lock_ttl=DATA_LOCK_TTL,
        build_fn=build_fn,
    )


def acquire_module_data(cache_key: tuple, load_docs_fn: Callable[[], List],
                        build_embeddings_fn: Callable[[List], List[List[float]]],
                        generate_snapshot_fn: Callable[[List], str], existing_snapshot: Optional[str] = None) -> ModuleCacheEntry:
    """
    Builds a ModuleCacheEntry for cache_key. The three components are deduped at different scopes:
      - docs:       Redis-shared across all processes
      - embeddings: per-process LRU (rebuilt from cached docs, bounded size)
      - snapshot:   Redis-shared; existing_snapshot is written through for siblings
    """

    docs = ensure_docs(cache_key, load_docs_fn)
    embeddings = get_or_build_embeddings(cache_key, lambda: build_embeddings_fn(docs))
    snapshot = acquire_snapshot(
        cache_key,
        lambda: generate_snapshot_fn(docs),
        existing_snapshot=existing_snapshot,
    )
    return ModuleCacheEntry(docs=docs, snapshot=snapshot, doc_embeddings=embeddings)
