"""
Infrastructure — ETF 成分股與行業板塊權重適配器。

提供 ETF 前 N 大成分股查詢及行業板塊權重分佈，
所有資料透過 L1 記憶體快取 + L2 磁碟快取雙層保護。
"""

from __future__ import annotations

import contextlib

from cachetools import TTLCache

from domain.constants import (
    DISK_ETF_HOLDINGS_TTL,
    DISK_ETF_SECTOR_WEIGHTS_TTL,
    DISK_KEY_ETF_HOLDINGS,
    DISK_KEY_ETF_SECTOR_WEIGHTS,
    ETF_HOLDINGS_CACHE_MAXSIZE,
    ETF_HOLDINGS_CACHE_TTL,
    ETF_TOP_N,
    SCAN_THREAD_POOL_SIZE,
)
from infrastructure.market_data._market_data_shared import (
    _RETRYABLE_EXCEPTIONS,
    _cached_fetch,
    _disk_cache,
    _FastShutdownExecutor,
    _rate_limiter,
    _run_batch_with_timeout,
    _yf_info_cache,
    _yf_retry,
    _yf_ticker_obj,
)
from logging_config import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# L1 caches (in-memory)
# ---------------------------------------------------------------------------

_etf_holdings_cache: TTLCache = TTLCache(
    maxsize=ETF_HOLDINGS_CACHE_MAXSIZE, ttl=ETF_HOLDINGS_CACHE_TTL
)
_etf_sector_weights_cache: TTLCache = TTLCache(
    maxsize=ETF_HOLDINGS_CACHE_MAXSIZE, ttl=ETF_HOLDINGS_CACHE_TTL
)

# Sentinel values — cached to avoid repeated yfinance calls for non-ETF tickers
_ETF_NOT_FOUND_SENTINEL: list[dict] = []
_ETF_SECTOR_WEIGHTS_NOT_FOUND: dict = {}

# yfinance funds_data.sector_weightings uses snake_case keys; map to GICS standard names.
_ETF_SECTOR_KEY_MAP: dict[str, str] = {
    "technology": "Technology",
    "consumer_cyclical": "Consumer Cyclical",
    "financial_services": "Financial Services",
    "realestate": "Real Estate",
    "consumer_defensive": "Consumer Defensive",
    "healthcare": "Healthcare",
    "utilities": "Utilities",
    "communication_services": "Communication Services",
    "energy": "Energy",
    "industrials": "Industrials",
    "basic_materials": "Basic Materials",
}


# ---------------------------------------------------------------------------
# ETF detection
# ---------------------------------------------------------------------------


def detect_is_etf(ticker: str) -> bool:
    """透過 yfinance quoteType 偵測是否為 ETF。失敗時回傳 False。"""
    from infrastructure.market_data._market_data_shared import _yf_info

    try:
        info = _yf_info(ticker)
        return info.get("quoteType", "") == "ETF"
    except Exception as exc:
        logger.debug("偵測 ETF 失敗（%s），回傳 False：%s", ticker, exc)
        return False


# ---------------------------------------------------------------------------
# ETF top holdings
# ---------------------------------------------------------------------------


@_yf_retry
def _fetch_etf_top_holdings(ticker: str) -> list[dict] | None:
    """從 yfinance 取得 ETF 前 N 大成分股。
    回傳 [{"symbol": "AAPL", "name": "Apple Inc.", "weight": 0.072}, ...] 或 None。
    非 ETF 標的會回傳 None。
    """
    try:
        ticker_obj = _yf_ticker_obj(ticker)
        fd = ticker_obj.funds_data
        if fd is None:
            return None
        top = fd.top_holdings
        if top is None or top.empty:
            logger.debug("%s ETF top_holdings 為空，將重試抓取。", ticker)
            raise OSError(f"{ticker}: yfinance returned empty ETF top_holdings")

        cols = list(top.columns)
        logger.debug(
            "%s top_holdings columns=%s, index=%s", ticker, cols, top.index.name
        )

        result = []
        for symbol, row in top.head(ETF_TOP_N).iterrows():
            weight = row.get("Holding Percent", row.get("% Assets"))
            if weight is None or weight == 0:
                continue
            name = row.get("Name", row.get("Holding Name", ""))
            result.append(
                {
                    "symbol": str(symbol).strip().upper(),
                    "name": str(name) if name else "",
                    "weight": float(weight),
                }
            )
        logger.info("%s ETF 成分股取得 %d 筆（前 %d）", ticker, len(result), ETF_TOP_N)
        return result if result else None
    except _RETRYABLE_EXCEPTIONS as e:
        logger.debug("%s 取得 ETF 成分股遇到暫時性錯誤，將重試：%s", ticker, e)
        raise
    except Exception as e:
        logger.debug("%s 非 ETF 或取得成分股失敗：%s", ticker, e)
        return None


def get_etf_top_holdings(
    ticker: str, *, is_known_etf: bool | None = None
) -> list[dict] | None:
    """取得 ETF 前 N 大成分股（含 L1 + L2 快取）。
    非 ETF 標的回傳 None。使用空 list 哨兵避免反覆呼叫 yfinance。
    """

    def _fetch_with_sentinel(t: str) -> list[dict]:
        result = _fetch_etf_top_holdings(t)
        return result if result else _ETF_NOT_FOUND_SENTINEL

    cached_info = _yf_info_cache.get(ticker)
    if (
        is_known_etf is not True
        and cached_info
        and cached_info.get("quoteType", "") != "ETF"
    ):
        return None

    try:
        data = _cached_fetch(
            _etf_holdings_cache,
            ticker,
            DISK_KEY_ETF_HOLDINGS,
            DISK_ETF_HOLDINGS_TTL,
            _fetch_with_sentinel,
            is_error=lambda d: d == _ETF_NOT_FOUND_SENTINEL,
        )
    except _RETRYABLE_EXCEPTIONS as e:
        logger.warning("%s ETF 成分股抓取重試後仍失敗，回傳空結果：%s", ticker, e)
        return None
    if data == _ETF_NOT_FOUND_SENTINEL and is_known_etf:
        disk_key = f"{DISK_KEY_ETF_HOLDINGS}:{ticker}"
        with contextlib.suppress(Exception):
            _disk_cache.delete(disk_key)
        _etf_holdings_cache.pop(ticker, None)
        logger.warning(
            "%s 為 ETF 但成分股快取為空，已清除負向快取以便下次重新抓取。",
            ticker,
        )
    return data if data else None


def prewarm_etf_holdings_batch(
    tickers: list[str], max_workers: int = SCAN_THREAD_POOL_SIZE
) -> dict[str, list[dict] | None]:
    """並行預熱多檔 ETF 的成分股快取。
    回傳 {ticker: holdings_list_or_None} 對照表。
    """
    results: dict[str, list[dict] | None] = {}
    with _FastShutdownExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(get_etf_top_holdings, t): t for t in tickers}
        completed, timed_out = _run_batch_with_timeout(
            futures, executor, label="ETF 成分股預熱"
        )
    for future in completed:
        ticker = completed[future]
        try:
            results[ticker] = future.result()
        except Exception as exc:
            logger.error("預熱 %s ETF 成分股失敗：%s", ticker, exc, exc_info=True)
            results[ticker] = None
    for ticker in timed_out:
        results[ticker] = None
    return results


# ---------------------------------------------------------------------------
# ETF sector weights
# ---------------------------------------------------------------------------


def _fetch_etf_sector_weights(ticker: str) -> dict[str, float] | None:
    """從 yfinance funds_data.sector_weightings 取得 ETF 的行業板塊權重分佈。
    回傳 {"Technology": 0.32, "Healthcare": 0.14, ...} 或 None。
    非 ETF 標的或無資料時回傳 None。
    """
    _rate_limiter.wait()
    try:
        t = _yf_ticker_obj(ticker)
        fd = t.funds_data
        if fd is None:
            return None
        weights = fd.sector_weightings
        if not weights:
            return None
        if isinstance(weights, list):
            if not weights:
                return None
            merged: dict[str, float] = {}
            for item in weights:
                if isinstance(item, dict):
                    merged.update(item)  # type: ignore[arg-type]
            weights = merged
        if not isinstance(weights, dict) or not weights:
            return None

        result: dict[str, float] = {}
        for raw_key, weight in weights.items():
            if not isinstance(weight, (int, float)) or weight <= 0:
                continue
            normalized = _ETF_SECTOR_KEY_MAP.get(
                str(raw_key).lower(), str(raw_key).title()
            )
            result[normalized] = result.get(normalized, 0.0) + float(weight)

        if not result:
            return None
        logger.info("%s ETF 行業板塊權重取得 %d 個板塊", ticker, len(result))
        return result
    except Exception as e:
        logger.debug("%s 非 ETF 或取得行業板塊權重失敗：%s", ticker, e)
        return None


def get_etf_sector_weights(
    ticker: str, *, is_known_etf: bool | None = None
) -> dict[str, float] | None:
    """取得 ETF 行業板塊權重分佈（含 L1 + L2 快取）。
    回傳 {"Technology": 0.32, ...} 或 None（非 ETF 或無資料）。
    """

    def _fetch_with_sentinel(t: str) -> dict[str, float]:
        result = _fetch_etf_sector_weights(t)
        return result if result else _ETF_SECTOR_WEIGHTS_NOT_FOUND

    cached_info = _yf_info_cache.get(ticker)
    if (
        is_known_etf is not True
        and cached_info
        and cached_info.get("quoteType", "") != "ETF"
    ):
        return None

    try:
        data = _cached_fetch(
            _etf_sector_weights_cache,
            ticker,
            DISK_KEY_ETF_SECTOR_WEIGHTS,
            DISK_ETF_SECTOR_WEIGHTS_TTL,
            _fetch_with_sentinel,
            is_error=lambda d: d == _ETF_SECTOR_WEIGHTS_NOT_FOUND,
        )
    except _RETRYABLE_EXCEPTIONS as e:
        logger.warning("%s ETF 板塊權重抓取重試後仍失敗，回傳空結果：%s", ticker, e)
        return None
    if data == _ETF_SECTOR_WEIGHTS_NOT_FOUND and is_known_etf:
        disk_key = f"{DISK_KEY_ETF_SECTOR_WEIGHTS}:{ticker}"
        with contextlib.suppress(Exception):
            _disk_cache.delete(disk_key)
        _etf_sector_weights_cache.pop(ticker, None)
        logger.warning(
            "%s 為 ETF 但板塊權重快取為空，已清除負向快取以便下次重新抓取。",
            ticker,
        )
    return data if data else None


def prewarm_etf_sector_weights_batch(
    tickers: list[str], max_workers: int = SCAN_THREAD_POOL_SIZE
) -> dict[str, dict[str, float] | None]:
    """並行預熱多檔 ETF 的行業板塊權重快取。
    非 ETF 標的會快速命中哨兵快取，不造成額外 yfinance 呼叫。
    回傳 {ticker: weights_or_None} 對照表。
    """
    results: dict[str, dict[str, float] | None] = {}
    with _FastShutdownExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(get_etf_sector_weights, t): t for t in tickers}
        completed, timed_out = _run_batch_with_timeout(
            futures, executor, label="ETF 板塊權重預熱"
        )
    for future in completed:
        ticker = completed[future]
        try:
            results[ticker] = future.result()
        except Exception as exc:
            logger.error("預熱 %s ETF 行業板塊權重失敗：%s", ticker, exc, exc_info=True)
            results[ticker] = None
    for ticker in timed_out:
        results[ticker] = None
    return results
