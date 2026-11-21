from collections.abc import Iterable

from ._types import _CacheT

__all__ = ('_create_cache',)


def _create_cache[K, V](init: Iterable[tuple[K, V]] = (), maxsize: int = 128) -> _CacheT[K, V]:
    cache: _CacheT[K, V] = {}
    try:
        from cachebox import LRUCache

        cache = LRUCache(maxsize)
    except ImportError:
        cache = {}
    if init:
        for k, v in init:
            cache[k] = v
    return cache
