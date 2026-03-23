"""
Infrastructure — 市場資料共用基礎設施（私有模組）。

提供 market_data 套件所有子模組共用的：
- 速率限制器 (_rate_limiter)
- 磁碟快取 (_disk_cache, _disk_get, _disk_set)
- 通用二層快取函式 (_cached_fetch)
- In-flight 重複請求去重 (_deduped_fetch)
- curl-cffi Session 工廠 (_get_session)
- 批次逾時執行 (_run_batch_with_timeout)
- yfinance 低階包裝函式 (_yf_history, _yf_history_short, _yf_info, …)
- 重試裝飾器 (_yf_retry) 及例外分類工具
- Fear & Greed 元件失敗追蹤工具

此模組為私有介面，外部請透過 infrastructure.market_data 存取公開 API。
"""

from __future__ import annotations

import contextlib
import threading
import time
from collections.abc import Callable  # noqa: TC003
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from typing import Any, TypeVar

import pandas as pd  # noqa: TC002
import yfinance as yf
from cachetools import TTLCache
from curl_cffi import requests as cffi_requests
from curl_cffi.curl import CurlError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from domain.constants import (
    CURL_CFFI_IMPERSONATE,
    DISK_KEY_YF_INFO,
    DISK_YF_INFO_TTL,
    FG_COMPONENT_FAILURE_COOLDOWN_SECONDS,
    PREWARM_BATCH_TIMEOUT,
    YF_CONNECT_TIMEOUT,
    YF_INFO_CACHE_MAXSIZE,
    YF_INFO_CACHE_TTL,
    YF_READ_TIMEOUT,
    YFINANCE_RATE_LIMIT_CPS,
    YFINANCE_RETRY_ATTEMPTS,
    YFINANCE_RETRY_WAIT_MAX,
    YFINANCE_RETRY_WAIT_MIN,
)
from infrastructure.common.config import DISK_CACHE_DIR, DISK_CACHE_SIZE_LIMIT
from infrastructure.common.disk_cache import DiskCache
from infrastructure.common.rate_limiter import RateLimiter
from logging_config import get_logger

T = TypeVar("T")

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Thread pool — fast shutdown to avoid blocking container teardown
# ---------------------------------------------------------------------------


class _FastShutdownExecutor(ThreadPoolExecutor):
    """ThreadPoolExecutor that shuts down without blocking on context exit."""

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.shutdown(wait=False, cancel_futures=True)
        return False


# ---------------------------------------------------------------------------
# Retry decorator — exponential back-off for transient network/DNS errors
# ---------------------------------------------------------------------------

_RETRYABLE_EXCEPTIONS = (CurlError, ConnectionError, OSError, TimeoutError)
_TRANSIENT_YF_ERROR_MARKERS: tuple[str, ...] = (
    "ssl_error_syscall",
    "failed to perform",
    "curl: (35)",
    "timed out",
    "connection reset",
    "connection aborted",
    "temporarily unavailable",
    "could not resolve host",
    "max retries exceeded",
)

_yf_retry = retry(
    stop=stop_after_attempt(YFINANCE_RETRY_ATTEMPTS),
    wait=wait_exponential(min=YFINANCE_RETRY_WAIT_MIN, max=YFINANCE_RETRY_WAIT_MAX),
    retry=retry_if_exception_type(_RETRYABLE_EXCEPTIONS),
    reraise=True,
)


def _is_error_dict(result: Any) -> bool:
    """判斷 fetcher 結果是否為錯誤回應（含 'error' 鍵的 dict）。"""
    return isinstance(result, dict) and "error" in result


def _is_yf_info_error(result: Any) -> bool:
    """判斷 yfinance info 是否為不適合寫入 L2 的不完整結果。"""
    if not isinstance(result, dict) or not result:
        return True
    return "quoteType" not in result


def _is_dividend_error(result: Any) -> bool:
    """判斷股息 fetcher 結果是否為錯誤。"""
    return isinstance(result, dict) and result.get("ytd_dividend_per_share") is None


def _is_transient_yf_error(exc: Exception) -> bool:
    """Classify transient Yahoo/yfinance transport errors by exception type/message."""
    if isinstance(exc, (CurlError, ConnectionError, TimeoutError, OSError)):
        return True
    msg = str(exc).lower()
    return any(marker in msg for marker in _TRANSIENT_YF_ERROR_MARKERS)


# ---------------------------------------------------------------------------
# Rate limiter — prevents yfinance from being rate-limited / blocked
# ---------------------------------------------------------------------------

_rate_limiter = RateLimiter(calls_per_second=YFINANCE_RATE_LIMIT_CPS)


# ---------------------------------------------------------------------------
# In-flight dedup — ensures only one concurrent yfinance call per cache key
# ---------------------------------------------------------------------------

_inflight_lock = threading.Lock()
_inflight_events: dict[str, threading.Event] = {}

# Fear & Greed component failure cooldown
_fg_component_failures: dict[str, float] = {}
_fg_component_failures_lock = threading.Lock()


def _is_fg_component_in_cooldown(ticker: str, *, now: float | None = None) -> bool:
    """Return True when ticker is inside short failure cooldown window."""
    current = time.monotonic() if now is None else now
    with _fg_component_failures_lock:
        last_failed = _fg_component_failures.get(ticker)
    return (
        last_failed is not None
        and current - last_failed < FG_COMPONENT_FAILURE_COOLDOWN_SECONDS
    )


def _mark_fg_component_failure(ticker: str, *, now: float | None = None) -> None:
    """Record latest component fetch failure timestamp."""
    current = time.monotonic() if now is None else now
    with _fg_component_failures_lock:
        _fg_component_failures[ticker] = current


def _clear_fg_component_failure(ticker: str) -> None:
    """Clear failure marker after successful fetch."""
    with _fg_component_failures_lock:
        _fg_component_failures.pop(ticker, None)


def _deduped_fetch(
    key: str, fetcher: Callable[[], T], result_getter: Callable[[], T]
) -> T:
    """確保同一 key 的 yfinance 呼叫在任意時刻只有一個在飛行中。

    若已有相同 key 的請求進行中，等待其完成後透過 result_getter 取用結果（例如讀 L1 快取）。
    """
    with _inflight_lock:
        if key in _inflight_events:
            event = _inflight_events[key]
            should_wait = True
        else:
            event = threading.Event()
            _inflight_events[key] = event
            should_wait = False

    if should_wait:
        event.wait()
        return result_getter()

    try:
        return fetcher()
    finally:
        event.set()
        with _inflight_lock:
            _inflight_events.pop(key, None)


# ---------------------------------------------------------------------------
# L2 cache (disk) — survives container restarts, avoids cold-start stampedes
# ---------------------------------------------------------------------------

_disk_cache = DiskCache(DISK_CACHE_DIR, size_limit=DISK_CACHE_SIZE_LIMIT)


def _disk_get(key: str) -> Any:
    """從磁碟快取 (L2) 讀取。失敗時回傳 None（非致命）。"""
    return _disk_cache.get(key)


def _disk_set(key: str, value: Any, ttl: int) -> None:
    """寫入磁碟快取 (L2)。失敗時靜默跳過（非致命）。"""
    _disk_cache.set(key, value, ttl)


# ---------------------------------------------------------------------------
# Generic two-level cache fetch (_cached_fetch)
# ---------------------------------------------------------------------------


def _cached_fetch(
    l1_cache: TTLCache,
    ticker: str,
    disk_prefix: str,
    disk_ttl: int,
    fetcher: Callable[[str], T],
    is_error: Callable[[T], bool] | None = None,
) -> T:
    """通用二層快取取得函式。L1 → L2 → fetcher，並回寫兩層快取。"""
    l1_error_cached = None
    cached = l1_cache.get(ticker)
    if cached is not None:
        if is_error is None or not is_error(cached):
            logger.debug("%s 命中 L1 快取（prefix=%s）。", ticker, disk_prefix)
            return cached
        l1_error_cached = cached
        logger.debug(
            "%s L1 為錯誤結果，繼續嘗試 L2（prefix=%s）。", ticker, disk_prefix
        )

    disk_key = f"{disk_prefix}:{ticker}"
    disk_cached = _disk_get(disk_key)
    if disk_cached is not None:
        if is_error is not None and is_error(disk_cached):
            with contextlib.suppress(Exception):
                _disk_cache.delete(disk_key)
            logger.debug(
                "%s L2 磁碟快取為舊錯誤結果，已清除（prefix=%s）。",
                ticker,
                disk_prefix,
            )
        else:
            logger.debug("%s 命中 L2 磁碟快取（prefix=%s）。", ticker, disk_prefix)
            l1_cache[ticker] = disk_cached
            return disk_cached
    if l1_error_cached is not None:
        return l1_error_cached

    logger.debug("%s L1+L2 皆未命中（prefix=%s），呼叫 fetcher...", ticker, disk_prefix)

    def _do_fetch() -> T:
        res = fetcher(ticker)
        l1_cache[ticker] = res
        if is_error is not None and is_error(res):
            logger.debug("%s 結果含錯誤，略過寫入 L2 磁碟快取。", ticker)
        else:
            _disk_set(disk_key, res, disk_ttl)
        return res

    def _get_cached() -> T:
        cached_val = l1_cache.get(ticker)
        if cached_val is not None:
            return cached_val  # type: ignore[return-value]
        disk_val = _disk_get(disk_key)
        if disk_val is not None:
            l1_cache[ticker] = disk_val
            return disk_val  # type: ignore[return-value]
        return fetcher(ticker)

    return _deduped_fetch(disk_key, _do_fetch, _get_cached)


# ---------------------------------------------------------------------------
# curl-cffi session factory — Chrome impersonation to bypass YF bot detection
# ---------------------------------------------------------------------------


def _get_session() -> cffi_requests.Session:
    """建立模擬 Chrome 瀏覽器的 Session，以繞過 Yahoo Finance 的 bot 防護。"""
    return cffi_requests.Session(
        impersonate=CURL_CFFI_IMPERSONATE,
        timeout=(YF_CONNECT_TIMEOUT, YF_READ_TIMEOUT),
    )


# ---------------------------------------------------------------------------
# Batch execution with timeout
# ---------------------------------------------------------------------------


def _run_batch_with_timeout(
    futures: dict[Future, str],
    executor: ThreadPoolExecutor,
    *,
    timeout: float | None = None,
    label: str = "batch",
) -> tuple[dict[Future, str], list[str]]:
    """Collect completed futures within *timeout* seconds, then abandon stragglers."""
    if timeout is None:
        timeout = PREWARM_BATCH_TIMEOUT
    completed: dict[Future, str] = {}
    timed_out_keys: list[str] = []
    try:
        for future in as_completed(futures, timeout=timeout):
            completed[future] = futures[future]
    except TimeoutError:
        timed_out_keys = [futures[f] for f in futures if not f.done()]
        executor.shutdown(wait=False, cancel_futures=True)
        logger.warning(
            "%s 批次逾時（%ds），%d 個任務未完成已放棄。",
            label,
            timeout,
            len(timed_out_keys),
        )
    return completed, timed_out_keys


# ---------------------------------------------------------------------------
# NaN utility
# ---------------------------------------------------------------------------


def _is_nan(val: Any) -> bool:
    """安全判斷 NaN（支援 None / float）。"""
    if val is None:
        return True
    try:
        import math

        return math.isnan(float(val))
    except (TypeError, ValueError):
        return True


# ---------------------------------------------------------------------------
# L1 cache for yfinance info (shared across modules for fast-path guards)
# ---------------------------------------------------------------------------

_yf_info_cache: TTLCache = TTLCache(
    maxsize=YF_INFO_CACHE_MAXSIZE, ttl=YF_INFO_CACHE_TTL
)


# ---------------------------------------------------------------------------
# Raw yfinance wrappers (retried, rate-limited, session-managed)
# ---------------------------------------------------------------------------


@_yf_retry
def _yf_history(ticker: str, period: str):
    """取得 yfinance 歷史資料（含重試）。空結果視為可重試。"""
    stock = yf.Ticker(ticker, session=_get_session())
    _rate_limiter.wait()
    hist = stock.history(period=period)
    if hist.empty:
        raise OSError(
            f"{ticker}: yfinance returned empty history, possibly due to a swallowed network error"
        )
    return stock, hist


@_yf_retry
def _yf_quarterly_financials(ticker: str) -> Any:
    """取得 yfinance 季度財報（含重試）。"""
    stock = yf.Ticker(ticker, session=_get_session())
    _rate_limiter.wait()
    return stock.quarterly_financials


@_yf_retry
def _yf_calendar(ticker: str) -> Any:
    """取得 yfinance 財報日曆（含重試）。"""
    stock = yf.Ticker(ticker, session=_get_session())
    _rate_limiter.wait()
    return stock.calendar


@_yf_retry
def _fetch_yf_info_from_yf(ticker: str) -> dict:
    """實際從 yfinance 取得股票 info（供 _cached_fetch 使用）。"""
    stock = yf.Ticker(ticker, session=_get_session())
    _rate_limiter.wait()
    return stock.info or {}


def _yf_info(ticker: str) -> dict:
    """取得 yfinance 股票 info（L1 + L2 快取，含重試）。"""
    return _cached_fetch(
        _yf_info_cache,
        ticker,
        DISK_KEY_YF_INFO,
        DISK_YF_INFO_TTL,
        _fetch_yf_info_from_yf,
        is_error=_is_yf_info_error,
    )


@_yf_retry
def _yf_history_short(ticker: str, period: str = "5d") -> pd.DataFrame:
    """取得 yfinance 短期歷史（含重試）。空結果視為可重試。"""
    _rate_limiter.wait()
    session = _get_session()
    ticker_obj = yf.Ticker(ticker, session=session)
    hist = ticker_obj.history(period=period)
    if hist.empty:
        raise OSError(
            f"{ticker}: yfinance returned empty short history, possibly due to a swallowed network error"
        )
    return hist


@_yf_retry
def _yf_ticker_obj(ticker: str) -> yf.Ticker:
    """建立 yfinance Ticker 物件（含重試）。用於 ETF funds_data 等屬性存取。"""
    _rate_limiter.wait()
    return yf.Ticker(ticker, session=_get_session())


def _yf_download(*args: Any, **kwargs: Any) -> pd.DataFrame:
    """Thin typed wrapper around yf.download()."""
    result = yf.download(*args, **kwargs)
    return result  # type: ignore[return-value]


@_yf_retry
def _yf_dividends(ticker: str) -> pd.Series | None:
    """取得股息歷史（含重試）。"""
    stock = yf.Ticker(ticker, session=_get_session())
    _rate_limiter.wait()
    return stock.get_dividends()


@_yf_retry
def _yf_splits(ticker: str) -> pd.Series | None:
    """取得股票分割歷史（含重試）。"""
    stock = yf.Ticker(ticker, session=_get_session())
    _rate_limiter.wait()
    return stock.get_splits()


def _yf_dividend_data(ticker: str) -> tuple[dict, pd.Series | None]:
    """從單一 Ticker 物件取得 info 與股息歷史。"""
    info = _yf_info(ticker)
    dividends: pd.Series | None = _yf_dividends(ticker)
    return info, dividends
