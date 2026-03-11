import threading
import time

from infrastructure.cache import SWRCache


def test_swr_cache_returns_miss_for_unknown_key() -> None:
    cache = SWRCache[str, int](maxsize=2, fresh_ttl=5, stale_ttl=15)
    value, state = cache.get("k1")
    assert value is None
    assert state == "miss"


def test_swr_cache_transitions_fresh_stale_expired() -> None:
    now = [0.0]
    cache = SWRCache[str, int](
        maxsize=2,
        fresh_ttl=5,
        stale_ttl=15,
        time_fn=lambda: now[0],
    )

    cache.set("k1", 100)

    now[0] = 3
    value_fresh, state_fresh = cache.get("k1")
    assert value_fresh == 100
    assert state_fresh == "fresh"

    now[0] = 8
    value_stale, state_stale = cache.get("k1")
    assert value_stale == 100
    assert state_stale == "stale"

    now[0] = 20
    value_expired, state_expired = cache.get("k1")
    assert value_expired is None
    assert state_expired == "expired"


def test_swr_cache_refreshes_stale_entry_in_background() -> None:
    now = [0.0]
    cache = SWRCache[str, int](
        maxsize=2,
        fresh_ttl=5,
        stale_ttl=30,
        time_fn=lambda: now[0],
    )
    cache.set("k1", 1)
    now[0] = 10

    release_refresh = threading.Event()
    refresh_started = threading.Event()
    call_count = {"n": 0}
    lock = threading.Lock()

    def refresh_fn() -> int:
        with lock:
            call_count["n"] += 1
        refresh_started.set()
        release_refresh.wait(timeout=1.0)
        return 2

    value1, state1 = cache.get("k1", refresh_fn=refresh_fn)
    value2, state2 = cache.get("k1", refresh_fn=refresh_fn)
    assert value1 == 1
    assert state1 == "stale"
    assert value2 == 1
    assert state2 == "stale"

    assert refresh_started.wait(timeout=1.0)
    release_refresh.set()
    time.sleep(0.05)

    with lock:
        assert call_count["n"] == 1

    value_refreshed, state_refreshed = cache.get("k1")
    assert value_refreshed == 2
    assert state_refreshed in {"fresh", "stale"}
