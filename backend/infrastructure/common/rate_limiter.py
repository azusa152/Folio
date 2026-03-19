"""Thread-safe token-bucket rate limiter shared by all infrastructure adapters."""

import threading
import time


class RateLimiter:
    """Ensure a minimum interval between consecutive calls (thread-safe)."""

    def __init__(self, calls_per_second: float) -> None:
        self._min_interval = 1.0 / calls_per_second
        self._lock = threading.Lock()
        self._last_call = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_call
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
            self._last_call = time.monotonic()
