"""
Reusable stale-while-revalidate cache for application services.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Callable

CacheState = Literal["miss", "fresh", "stale", "expired"]
logger = logging.getLogger(__name__)


@dataclass
class _CacheEntry[V]:
    value: V
    created_at: float


class SWRCache[K, V]:
    """In-memory LRU cache with fresh + stale windows.

    - fresh window: return value as-is.
    - stale window: return value immediately and optionally refresh in background.
    - expired: treat as miss.
    """

    def __init__(
        self,
        *,
        maxsize: int,
        fresh_ttl: int,
        stale_ttl: int,
        time_fn: Callable[[], float] | None = None,
    ) -> None:
        if maxsize <= 0:
            raise ValueError("maxsize must be > 0")
        if fresh_ttl <= 0:
            raise ValueError("fresh_ttl must be > 0")
        if stale_ttl < fresh_ttl:
            raise ValueError("stale_ttl must be >= fresh_ttl")

        self._maxsize = maxsize
        self._fresh_ttl = fresh_ttl
        self._stale_ttl = stale_ttl
        self._time_fn = time_fn or time.monotonic

        self._store: OrderedDict[K, _CacheEntry[V]] = OrderedDict()
        self._refreshing_keys: set[K] = set()
        self._lock = threading.Lock()

    def get(
        self,
        key: K,
        *,
        refresh_fn: Callable[[], V] | None = None,
    ) -> tuple[V | None, CacheState]:
        should_refresh = False
        value: V | None = None
        now = self._time_fn()

        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None, "miss"

            age = now - entry.created_at
            if age <= self._fresh_ttl:
                self._store.move_to_end(key)
                return entry.value, "fresh"

            if age <= self._stale_ttl:
                self._store.move_to_end(key)
                value = entry.value
                if refresh_fn is not None and key not in self._refreshing_keys:
                    self._refreshing_keys.add(key)
                    should_refresh = True
            else:
                self._store.pop(key, None)
                return None, "expired"

        if should_refresh:
            self._refresh_in_background(key, refresh_fn)

        return value, "stale"

    def set(self, key: K, value: V) -> None:
        with self._lock:
            self._store[key] = _CacheEntry(value=value, created_at=self._time_fn())
            self._store.move_to_end(key)
            while len(self._store) > self._maxsize:
                self._store.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._refreshing_keys.clear()

    def _refresh_in_background(self, key: K, refresh_fn: Callable[[], V]) -> None:
        def _runner() -> None:
            try:
                refreshed = refresh_fn()
                self.set(key, refreshed)
            except Exception as exc:
                # Keep stale value when refresh fails.
                logger.warning("SWR background refresh failed for key=%r: %s", key, exc)
            finally:
                with self._lock:
                    self._refreshing_keys.discard(key)

        threading.Thread(target=_runner, daemon=True).start()
