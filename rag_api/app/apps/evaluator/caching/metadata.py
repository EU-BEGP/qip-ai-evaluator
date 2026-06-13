# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from typing import Callable, Dict, List

from django.core.cache import cache

from .module_data import ensure_docs
from .primitives import (
    DATA_LOCK_TTL,
    METADATA_CACHE_TTL,
    acquire_or_build,
    lock_key,
)


def metadata_key(cache_key: tuple) -> str:
    return f"module:meta:{cache_key[0]}:{cache_key[1]}"


def acquire_metadata(cache_key: tuple, load_docs_fn: Callable[[], List],
                     build_metadata_fn: Callable[[List], Dict]) -> Dict:
    """Returns metadata dict (Redis-shared cross-process). build_metadata_fn(docs) returns the metadata."""

    key = metadata_key(cache_key)

    cached = cache.get(key)
    if cached is not None:
        cache.touch(key, METADATA_CACHE_TTL)
        return cached

    docs = ensure_docs(cache_key, load_docs_fn)

    return acquire_or_build(
        data_key=key,
        lock_key=lock_key("metadata", cache_key),
        ttl=METADATA_CACHE_TTL,
        lock_ttl=DATA_LOCK_TTL,
        build_fn=lambda: build_metadata_fn(docs),
    )
