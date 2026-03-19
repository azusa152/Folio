"""Shared disk-backed L2 cache wrapper used by all infrastructure adapters."""

from __future__ import annotations

import contextlib
from typing import Any

import diskcache


class DiskCache:
    """Thin, exception-safe wrapper around diskcache.Cache.

    All public methods suppress exceptions so a disk failure is never fatal.
    Direct access to the underlying cache is available via `.cache` for
    operations such as prefix-deletion or full cache iteration.
    """

    def __init__(self, directory: str, size_limit: int) -> None:
        self.cache = diskcache.Cache(directory, size_limit=size_limit)

    def get(self, key: str) -> Any:
        """Return cached value or None on any error."""
        with contextlib.suppress(Exception):
            return self.cache.get(key)
        return None

    def set(self, key: str, value: Any, ttl: int) -> None:
        """Write value with expiry; silently skip on any error."""
        with contextlib.suppress(Exception):
            self.cache.set(key, value, expire=ttl)

    def clear(self) -> None:
        """Remove all entries from the cache."""
        self.cache.clear()

    def iterkeys(self):
        """Iterate over all cache keys."""
        return self.cache.iterkeys()

    def delete(self, key: str) -> None:
        """Delete a specific key; silently skip on any error."""
        with contextlib.suppress(Exception):
            del self.cache[key]
