"""
Infrastructure — 外匯匯率與歷史資料適配器。

提供即時匯率查詢與匯率歷史資料（用於幣別曝險監控），
所有資料透過 L1 記憶體快取 + L2 磁碟快取雙層保護。
"""

from __future__ import annotations

import pandas as pd
from cachetools import TTLCache

from domain.constants import (
    DISK_FOREX_HISTORY_LONG_TTL,
    DISK_FOREX_HISTORY_TTL,
    DISK_FOREX_TTL,
    DISK_KEY_FOREX,
    DISK_KEY_FOREX_HISTORY,
    DISK_KEY_FOREX_HISTORY_LONG,
    FOREX_CACHE_MAXSIZE,
    FOREX_CACHE_TTL,
    FOREX_HISTORY_CACHE_MAXSIZE,
    FOREX_HISTORY_CACHE_TTL,
    FOREX_HISTORY_LONG_CACHE_MAXSIZE,
    FOREX_HISTORY_LONG_CACHE_TTL,
    FX_HISTORY_PERIOD,
    FX_LONG_TERM_PERIOD,
)
from infrastructure.market_data._market_data_shared import (
    _cached_fetch,
    _disk_cache,
    _FastShutdownExecutor,
    _is_nan,
    _run_batch_with_timeout,
    _yf_history_short,
)
from logging_config import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# L1 caches (in-memory)
# ---------------------------------------------------------------------------

_forex_cache: TTLCache = TTLCache(maxsize=FOREX_CACHE_MAXSIZE, ttl=FOREX_CACHE_TTL)
_forex_history_cache: TTLCache = TTLCache(
    maxsize=FOREX_HISTORY_CACHE_MAXSIZE, ttl=FOREX_HISTORY_CACHE_TTL
)
_forex_history_long_cache: TTLCache = TTLCache(
    maxsize=FOREX_HISTORY_LONG_CACHE_MAXSIZE, ttl=FOREX_HISTORY_LONG_CACHE_TTL
)


# ---------------------------------------------------------------------------
# Cache management
# ---------------------------------------------------------------------------


def clear_forex_caches() -> dict:
    """清除 FX 相關 L1 記憶體快取與對應 L2 磁碟快取。"""
    l1_caches = [
        _forex_cache,
        _forex_history_cache,
        _forex_history_long_cache,
    ]
    for cache in l1_caches:
        cache.clear()

    deleted_disk_entries = 0
    for disk_prefix in [
        DISK_KEY_FOREX,
        DISK_KEY_FOREX_HISTORY,
        DISK_KEY_FOREX_HISTORY_LONG,
    ]:
        try:
            to_delete = [
                key
                for key in _disk_cache.iterkeys()
                if isinstance(key, str) and key.startswith(f"{disk_prefix}:")
            ]
            for key in to_delete:
                _disk_cache.delete(key)
            deleted_disk_entries += len(to_delete)
        except Exception:
            logger.warning("清除 FX 磁碟快取失敗：prefix=%s", disk_prefix)

    logger.info(
        "已清除 FX 快取（L1×%d + L2 entries=%d）。",
        len(l1_caches),
        deleted_disk_entries,
    )
    return {"l1_cleared": len(l1_caches), "l2_entries_cleared": deleted_disk_entries}


# ---------------------------------------------------------------------------
# Exchange rate
# ---------------------------------------------------------------------------


def _fetch_forex_rate(pair_key: str) -> float:
    """從 yfinance 取得單一匯率（供 _cached_fetch 使用）。
    pair_key 格式為 "DISPLAY_CURRENCY:HOLDING_CURRENCY"，例如 "USD:TWD"。
    回傳值為：1 單位 holding_currency = ? 單位 display_currency 的匯率。
    """
    try:
        display_cur, holding_cur = pair_key.split(":")
        if display_cur == holding_cur:
            return 1.0

        yf_ticker = f"{holding_cur}{display_cur}=X"
        hist = _yf_history_short(yf_ticker, "5d")

        if hist is not None and not hist.empty:
            rate = float(hist["Close"].dropna().iloc[-1])
            logger.info("匯率 %s → %s = %.4f", holding_cur, display_cur, rate)
            return rate

        yf_ticker_rev = f"{display_cur}{holding_cur}=X"
        hist_rev = _yf_history_short(yf_ticker_rev, "5d")

        if hist_rev is not None and not hist_rev.empty:
            rev_rate = float(hist_rev["Close"].dropna().iloc[-1])
            rate = 1.0 / rev_rate if rev_rate > 0 else 1.0
            logger.info(
                "匯率 %s → %s = %.4f（反向查詢）", holding_cur, display_cur, rate
            )
            return rate

        logger.warning("無法取得匯率 %s → %s，使用 1.0", holding_cur, display_cur)
        return 1.0

    except Exception as e:
        logger.warning("取得匯率失敗（%s）：%s，使用 1.0", pair_key, e)
        return 1.0


def get_exchange_rate(display_currency: str, holding_currency: str) -> float:
    """取得匯率：1 單位 holding_currency = ? 單位 display_currency。
    結果透過 L1 + L2 快取。
    """
    if display_currency == holding_currency:
        return 1.0
    pair_key = f"{display_currency}:{holding_currency}"
    return _cached_fetch(
        _forex_cache, pair_key, DISK_KEY_FOREX, DISK_FOREX_TTL, _fetch_forex_rate
    )


def get_exchange_rates(
    display_currency: str, holding_currencies: list[str]
) -> dict[str, float]:
    """批次取得匯率：各 holding_currency → display_currency。
    回傳 dict[holding_currency, rate]，rate 表示 1 單位 holding = ? 單位 display。
    快取命中時直接回傳；快取未命中時並行發起 yfinance 請求。
    """
    foreign = set(holding_currencies) - {display_currency}
    rates: dict[str, float] = {display_currency: 1.0}
    if not foreign:
        return rates

    with _FastShutdownExecutor(max_workers=len(foreign)) as executor:
        futures = {
            executor.submit(get_exchange_rate, display_currency, cur): cur
            for cur in foreign
        }
        completed, timed_out = _run_batch_with_timeout(
            futures, executor, label="匯率取得"
        )
    for future in completed:
        cur = completed[future]
        try:
            rates[cur] = future.result()
        except Exception as exc:
            logger.warning("並行取得匯率失敗（%s）：%s，使用 1.0", cur, exc)
            rates[cur] = 1.0
    for cur in timed_out:
        rates[cur] = 1.0
    return rates


# ---------------------------------------------------------------------------
# Forex history (for Currency Exposure Monitor)
# ---------------------------------------------------------------------------


def _fetch_forex_history(pair_key: str) -> list[dict]:
    """從 yfinance 取得匯率歷史（供 _cached_fetch 使用）。
    pair_key 格式為 "BASE:QUOTE"，例如 "USD:TWD"。
    回傳 [{"date": "2026-02-05", "close": 32.15}, ...] 按日期升序。
    """
    try:
        base, quote = pair_key.split(":")
        if base == quote:
            return []

        yf_ticker = f"{base}{quote}=X"
        hist = _yf_history_short(yf_ticker, FX_HISTORY_PERIOD)

        if hist is not None and not hist.empty:
            return [
                {
                    "date": pd.Timestamp(idx).strftime("%Y-%m-%d"),
                    "close": round(float(row["Close"]), 4),
                }
                for idx, row in hist.iterrows()
                if not _is_nan(row.get("Close"))
            ]

        yf_ticker_rev = f"{quote}{base}=X"
        hist_rev = _yf_history_short(yf_ticker_rev, FX_HISTORY_PERIOD)

        if hist_rev is not None and not hist_rev.empty:
            return [
                {
                    "date": pd.Timestamp(idx).strftime("%Y-%m-%d"),
                    "close": round(1.0 / float(row["Close"]), 4),
                }
                for idx, row in hist_rev.iterrows()
                if not _is_nan(row.get("Close")) and float(row["Close"]) > 0
            ]

        logger.warning("無法取得匯率歷史 %s/%s", base, quote)
        return []

    except Exception as e:
        logger.warning("取得匯率歷史失敗（%s）：%s", pair_key, e)
        return []


def get_forex_history(base: str, quote: str) -> list[dict]:
    """取得匯率歷史：1 base = ? quote 的每日收盤價。
    回傳 [{"date": "2026-02-05", "close": 32.15}, ...]。
    結果透過 L1 + L2 快取。
    """
    if base == quote:
        return []
    pair_key = f"{base}:{quote}"
    result = _cached_fetch(
        _forex_history_cache,
        pair_key,
        DISK_KEY_FOREX_HISTORY,
        DISK_FOREX_HISTORY_TTL,
        _fetch_forex_history,
    )
    return result if result else []


def _fetch_forex_history_long(pair_key: str) -> list[dict]:
    """從 yfinance 取得 3 個月匯率歷史（供 _cached_fetch 使用）。"""
    try:
        base, quote = pair_key.split(":")
        if base == quote:
            return []

        yf_ticker = f"{base}{quote}=X"
        hist = _yf_history_short(yf_ticker, FX_LONG_TERM_PERIOD)

        if hist is not None and not hist.empty:
            return [
                {
                    "date": pd.Timestamp(idx).strftime("%Y-%m-%d"),
                    "close": round(float(row["Close"]), 4),
                }
                for idx, row in hist.iterrows()
                if not _is_nan(row.get("Close"))
            ]

        yf_ticker_rev = f"{quote}{base}=X"
        hist_rev = _yf_history_short(yf_ticker_rev, FX_LONG_TERM_PERIOD)

        if hist_rev is not None and not hist_rev.empty:
            return [
                {
                    "date": pd.Timestamp(idx).strftime("%Y-%m-%d"),
                    "close": round(1.0 / float(row["Close"]), 4),
                }
                for idx, row in hist_rev.iterrows()
                if not _is_nan(row.get("Close")) and float(row["Close"]) > 0
            ]

        logger.warning("無法取得長期匯率歷史 %s/%s", base, quote)
        return []

    except Exception as e:
        logger.warning("取得長期匯率歷史失敗（%s）：%s", pair_key, e)
        return []


def get_forex_history_long(base: str, quote: str) -> list[dict]:
    """取得 3 個月匯率歷史：1 base = ? quote 的每日收盤價。
    結果透過 L1 + L2 快取（L1: 2hr, L2: 4hr）。
    """
    if base == quote:
        return []
    pair_key = f"{base}:{quote}"
    result = _cached_fetch(
        _forex_history_long_cache,
        pair_key,
        DISK_KEY_FOREX_HISTORY_LONG,
        DISK_FOREX_HISTORY_LONG_TTL,
        _fetch_forex_history_long,
    )
    return result if result else []
