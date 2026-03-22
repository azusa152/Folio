"""
Infrastructure — 市場資料適配器 (yfinance)。
負責外部 API 呼叫、快取管理、速率限制。
所有呼叫皆以 try/except 包裹，失敗時回傳結構化降級結果。

Submodule layout (shared infrastructure in _market_data_shared.py):
  forex.py     — 外匯匯率 + 匯率歷史
  etf.py       — ETF 成分股 + 行業板塊權重
  sentiment.py — VIX + Fear & Greed 指數 + JP/TW 波動率
"""

import contextlib
import math
import threading
from datetime import UTC, date, datetime, timedelta

import pandas as pd
import yfinance as yf
from cachetools import TTLCache

from domain.analysis import (
    compute_beta,
    compute_bias,
    compute_daily_change_pct,
    compute_moving_average,
    compute_rsi,
    compute_volume_ratio,
    determine_market_sentiment,
    determine_moat_status,
)
from domain.constants import (
    BACKFILL_MIN_HISTORY_DAYS,
    BETA_CACHE_MAXSIZE,
    BETA_CACHE_TTL,
    DEFAULT_LANGUAGE,
    DISK_BETA_TTL,
    DISK_DIVIDEND_TTL,
    DISK_EARNINGS_TTL,
    DISK_EXCHANGE_TTL,
    DISK_FUNDAMENTALS_TTL,
    DISK_KEY_BETA,
    DISK_KEY_DIVIDEND,
    DISK_KEY_DIVIDEND_EVENTS,
    DISK_KEY_EARNINGS,
    DISK_KEY_ETF_HOLDINGS,  # noqa: F401 — re-exported for backward compat
    DISK_KEY_EXCHANGE,
    DISK_KEY_FUNDAMENTALS,
    DISK_KEY_MOAT,
    DISK_KEY_NAME,
    DISK_KEY_PRICE_HISTORY,
    DISK_KEY_PRICE_PAIR,
    DISK_KEY_ROGUE_WAVE,
    DISK_KEY_SECTOR,
    DISK_KEY_SIGNALS,
    DISK_KEY_STOCK_SPLIT,
    DISK_MOAT_FAILURE_TTL,
    DISK_MOAT_PERSISTENT_TTL,
    DISK_MOAT_TTL,
    DISK_NAME_TTL,
    DISK_PRICE_HISTORY_TTL,
    DISK_PRICE_PAIR_TTL,
    DISK_ROGUE_WAVE_TTL,
    DISK_SECTOR_TTL,
    DISK_SIGNALS_TTL,
    DIVIDEND_CACHE_MAXSIZE,
    DIVIDEND_CACHE_TTL,
    DIVIDEND_LOOKBACK_DAYS,
    EARNINGS_CACHE_MAXSIZE,
    EARNINGS_CACHE_TTL,
    FG_SPY_TICKER,
    FUNDAMENTALS_CACHE_MAXSIZE,
    FUNDAMENTALS_CACHE_TTL,
    INSTITUTIONAL_HOLDERS_TOP_N,
    MA60_WINDOW,
    MA200_WINDOW,
    MARGIN_TREND_QUARTERS,
    MIN_CLOSE_PRICES_FOR_CHANGE,
    MIN_HISTORY_DAYS_FOR_SIGNALS,
    MOAT_CACHE_MAXSIZE,
    MOAT_CACHE_TTL,
    MOAT_PERSISTENT_FAILURE_THRESHOLD,
    PRICE_HISTORY_CACHE_MAXSIZE,
    PRICE_HISTORY_CACHE_TTL,
    ROGUE_WAVE_CACHE_MAXSIZE,
    ROGUE_WAVE_CACHE_TTL,
    ROGUE_WAVE_HISTORY_PERIOD,
    ROGUE_WAVE_MIN_HISTORY_DAYS,
    SCAN_THREAD_POOL_SIZE,
    SIGNALS_CACHE_MAXSIZE,
    SIGNALS_CACHE_TTL,
    STOCK_SPLIT_CACHE_MAXSIZE,
    STOCK_SPLIT_CACHE_TTL,
    STOCK_SPLIT_LOOKBACK_DAYS,
    YFINANCE_HISTORY_PERIOD,
)
from domain.enums import MarketSentiment, MoatStatus
from i18n import t
from infrastructure.market_data._market_data_shared import (
    _cached_fetch,
    _disk_cache,
    _disk_get,
    _disk_set,
    _FastShutdownExecutor,
    _fg_component_failures,
    _fg_component_failures_lock,
    _get_session,
    _is_dividend_error,
    _is_error_dict,
    _is_transient_yf_error,
    _rate_limiter,
    _run_batch_with_timeout,
    _yf_calendar,
    _yf_dividend_data,
    _yf_dividends,
    _yf_download,
    _yf_history,
    _yf_info,
    _yf_info_cache,
    _yf_quarterly_financials,
    _yf_splits,
)
from infrastructure.market_data.etf import (  # noqa: F401
    _ETF_NOT_FOUND_SENTINEL,
    _ETF_SECTOR_KEY_MAP,
    _ETF_SECTOR_WEIGHTS_NOT_FOUND,
    _etf_holdings_cache,
    _etf_sector_weights_cache,
    _fetch_etf_top_holdings,
    detect_is_etf,
    get_etf_sector_weights,
    get_etf_top_holdings,
    prewarm_etf_holdings_batch,
    prewarm_etf_sector_weights_batch,
)
from infrastructure.market_data.forex import (  # noqa: F401
    _forex_cache,
    _forex_history_cache,
    _forex_history_long_cache,
    clear_forex_caches,
    get_exchange_rate,
    get_exchange_rates,
    get_forex_history,
    get_forex_history_long,
)
from infrastructure.market_data.formatters import (
    build_moat_details,
    build_signal_status,
)
from infrastructure.market_data.sentiment import (  # noqa: F401
    _fear_greed_cache,
    _fetch_fg_component_history_safe,
    get_cnn_fear_greed,
    get_fear_greed_index,
    get_jp_volatility_index,
    get_tw_volatility_index,
    get_vix_data,
)
from logging_config import get_logger

logger = get_logger(__name__)


_BEARISH_TIERS: frozenset = frozenset(
    {MarketSentiment.BEARISH, MarketSentiment.STRONG_BEARISH}
)


# ---------------------------------------------------------------------------
# L1 快取（記憶體）：domain-specific caches owned by this module
# (forex/etf/sentiment/yf_info caches are imported from their submodules above)
# ---------------------------------------------------------------------------
_signals_cache: TTLCache = TTLCache(
    maxsize=SIGNALS_CACHE_MAXSIZE, ttl=SIGNALS_CACHE_TTL
)
_moat_cache: TTLCache = TTLCache(maxsize=MOAT_CACHE_MAXSIZE, ttl=MOAT_CACHE_TTL)
_earnings_cache: TTLCache = TTLCache(
    maxsize=EARNINGS_CACHE_MAXSIZE, ttl=EARNINGS_CACHE_TTL
)
_dividend_cache: TTLCache = TTLCache(
    maxsize=DIVIDEND_CACHE_MAXSIZE, ttl=DIVIDEND_CACHE_TTL
)
_dividend_events_cache: TTLCache = TTLCache(
    maxsize=DIVIDEND_CACHE_MAXSIZE, ttl=DIVIDEND_CACHE_TTL
)
_stock_split_cache: TTLCache = TTLCache(
    maxsize=STOCK_SPLIT_CACHE_MAXSIZE, ttl=STOCK_SPLIT_CACHE_TTL
)
_fundamentals_cache: TTLCache = TTLCache(
    maxsize=FUNDAMENTALS_CACHE_MAXSIZE, ttl=FUNDAMENTALS_CACHE_TTL
)
_price_history_cache: TTLCache = TTLCache(
    maxsize=PRICE_HISTORY_CACHE_MAXSIZE, ttl=PRICE_HISTORY_CACHE_TTL
)
_beta_cache: TTLCache = TTLCache(maxsize=BETA_CACHE_MAXSIZE, ttl=BETA_CACHE_TTL)
_rogue_wave_cache: TTLCache = TTLCache(
    maxsize=ROGUE_WAVE_CACHE_MAXSIZE, ttl=ROGUE_WAVE_CACHE_TTL
)


def clear_all_caches() -> dict:
    """清除所有 L1 記憶體快取與 L2 磁碟快取（包含所有子模組的快取）。"""
    l1_caches = [
        _signals_cache,
        _moat_cache,
        _earnings_cache,
        _dividend_cache,
        _dividend_events_cache,
        _stock_split_cache,
        _fundamentals_cache,
        _yf_info_cache,
        _price_history_cache,
        _forex_cache,
        _etf_holdings_cache,
        _etf_sector_weights_cache,
        _forex_history_cache,
        _forex_history_long_cache,
        _fear_greed_cache,
        _beta_cache,
        _rogue_wave_cache,
    ]
    for cache in l1_caches:
        cache.clear()
    with _fg_component_failures_lock:
        _fg_component_failures.clear()
    # Also reset sticky failure counters so cache clear fully resets runtime state.
    with _moat_failure_lock:
        _moat_failure_counts.clear()
    _disk_cache.clear()
    logger.info("已清除所有快取（L1×%d + L2 磁碟）。", len(l1_caches))
    return {"l1_cleared": len(l1_caches), "l2_cleared": True}


# ===========================================================================
# 技術面訊號
# ===========================================================================


def _fetch_signals_from_yf(ticker: str, pre_fetched_hist=None) -> dict:
    """實際從 yfinance 取得技術訊號（供 _cached_fetch 使用）。
    pre_fetched_hist: 若提供，略過 _yf_history 呼叫，直接使用此 DataFrame（批次掃描優化路徑）。
    機構持倉在批次預熱路徑中跳過（省去每檔一次額外的限流 API 呼叫），待首次 cache miss 時再補抓。
    """
    try:
        if pre_fetched_hist is not None:
            hist = pre_fetched_hist
            stock = (
                None  # 批次預熱路徑：跳過 yf.Ticker()，機構持倉留待 cache miss 時再取
            )
        else:
            stock, hist = _yf_history(ticker, YFINANCE_HISTORY_PERIOD)

        if hist.empty or len(hist) < MIN_HISTORY_DAYS_FOR_SIGNALS:
            logger.warning(
                "%s 歷史資料不足（%d 筆），無法計算技術指標。", ticker, len(hist)
            )
            return {
                "error": t(
                    "market.insufficient_history", lang=DEFAULT_LANGUAGE, ticker=ticker
                )
            }

        # Piggyback：將收盤價歷史寫入 price_history 快取，避免後續重複呼叫 yfinance
        _piggyback_price_history(ticker, hist)

        closes = hist["Close"].tolist()
        volumes = hist["Volume"].tolist() if "Volume" in hist.columns else []
        current_price = round(closes[-1], 2)

        # 計算日漲跌（前一交易日 vs. 當日收盤價）
        previous_close = None
        change_pct = None
        if len(closes) >= MIN_CLOSE_PRICES_FOR_CHANGE:
            previous_close = round(closes[-2], 2)
            change_pct = compute_daily_change_pct(current_price, previous_close)
            logger.debug(
                "%s 日漲跌：previous=%.2f, current=%.2f, change=%.2f%%",
                ticker,
                previous_close,
                current_price,
                change_pct if change_pct is not None else 0.0,
            )
        else:
            logger.debug(
                "%s 歷史資料不足（%d 筆），無法計算日漲跌", ticker, len(closes)
            )

        # 使用 domain 層的純計算函式
        rsi = compute_rsi(closes)
        ma200 = compute_moving_average(closes, MA200_WINDOW)
        ma60 = compute_moving_average(closes, MA60_WINDOW)
        bias = compute_bias(current_price, ma60) if ma60 else None
        bias_200 = compute_bias(current_price, ma200) if ma200 else None
        volume_ratio = compute_volume_ratio(volumes)

        logger.info(
            "%s 技術訊號：price=%.2f, RSI=%s, 200MA=%s, 60MA=%s, Bias=%s%%, Bias200=%s%%, VolRatio=%s",
            ticker,
            current_price,
            rsi,
            ma200,
            ma60,
            bias,
            bias_200,
            volume_ratio,
        )

        # 機構持倉 (best-effort；批次預熱路徑 stock=None 故跳過，待首次 cache miss 時再補抓)
        institutional_holders = None
        if stock is not None and not ticker.startswith("^"):
            try:
                _rate_limiter.wait()
                holders_df = stock.institutional_holders
                if holders_df is not None and not holders_df.empty:
                    top5 = holders_df.head(INSTITUTIONAL_HOLDERS_TOP_N)
                    institutional_holders = []
                    for _, row in top5.iterrows():
                        holder_entry = {}
                        for col in top5.columns:
                            val = row[col]
                            # 將 Timestamp / NaT 等轉為字串
                            if hasattr(val, "isoformat"):
                                holder_entry[col] = val.isoformat()[:10]  # type: ignore[union-attr]
                            elif val is None or (
                                hasattr(val, "item") and str(val) == "NaT"
                            ):
                                holder_entry[col] = "N/A"
                            else:
                                holder_entry[col] = (
                                    val if not hasattr(val, "item") else val.item()
                                )
                        institutional_holders.append(holder_entry)
                    logger.debug(
                        "%s 機構持倉：取得 %d 筆", ticker, len(institutional_holders)
                    )
            except Exception as holder_err:
                logger.debug("%s 機構持倉取得失敗（非致命）：%s", ticker, holder_err)

        raw_signals = {
            "ticker": ticker,
            "price": current_price,
            "previous_close": previous_close,
            "change_pct": change_pct,
            "rsi": rsi,
            "ma200": ma200,
            "ma60": ma60,
            "bias": bias,
            "bias_200": bias_200,
            "volume_ratio": volume_ratio,
            "institutional_holders": institutional_holders,
            "fetched_at": datetime.now(UTC).isoformat(),
        }
        return {**raw_signals, "status": build_signal_status(raw_signals)}

    except Exception as e:
        if _is_transient_yf_error(e):
            logger.warning(
                "技術訊號暫時抓取失敗（%s），改以錯誤回應優雅降級：%s", ticker, e
            )
        else:
            logger.error("無法取得 %s 技術訊號：%s", ticker, e, exc_info=True)
        return {
            "error": t(
                "market.signals_fetch_error",
                lang=DEFAULT_LANGUAGE,
                ticker=ticker,
                error=str(e),
            )
        }


def get_technical_signals(ticker: str) -> dict | None:
    """
    取得技術面訊號：RSI(14)、現價、200MA、60MA、Bias(%)、Volume Ratio。
    結果快取 5 分鐘。錯誤結果僅寫入 L1（短暫），不寫入 L2/磁碟。
    """
    return _cached_fetch(
        _signals_cache,
        ticker,
        DISK_KEY_SIGNALS,
        DISK_SIGNALS_TTL,
        _fetch_signals_from_yf,
        is_error=_is_error_dict,
    )


def batch_download_history(
    tickers: list[str], period: str = YFINANCE_HISTORY_PERIOD
) -> dict:
    """
    使用 yf.download() 一次批次下載多檔股票的價格歷史，大幅減少 HTTP 請求數量。
    回傳 {ticker: DataFrame}，僅包含有效且資料量足夠的股票。
    失敗時靜默回傳空字典（呼叫端應回退至個別呼叫）。
    """
    if not tickers:
        return {}
    try:
        _rate_limiter.wait()
        data = _yf_download(
            tickers,
            period=period,
            group_by="ticker",
            threads=True,
            progress=False,
            auto_adjust=True,
            session=_get_session(),
        )
        result: dict = {}
        for ticker in tickers:
            try:
                df = data[ticker] if len(tickers) > 1 else data
                df = df.dropna(how="all")
                if not df.empty and len(df) >= MIN_HISTORY_DAYS_FOR_SIGNALS:
                    result[ticker] = df
                else:
                    logger.debug(
                        "%s 批次下載資料不足（%d 筆），將回退至個別呼叫。",
                        ticker,
                        len(df),
                    )
            except Exception as e:
                logger.debug("批次下載 %s 資料擷取失敗（已略過）：%s", ticker, e)
        logger.info("批次下載完成：%d/%d 檔股票有效。", len(result), len(tickers))
        return result
    except Exception as e:
        logger.warning("批次下載歷史資料失敗，回退至個別呼叫：%s", e)
        return {}


def batch_download_history_extended(
    tickers: list[str],
    period: str,
    min_days: int = BACKFILL_MIN_HISTORY_DAYS,
) -> dict[str, list[dict]]:
    """
    使用 yf.download() 一次下載多檔延長歷史資料（回填用途）。

    回傳 {ticker: [{"date": "...", "close": ...}, ...]}。
    僅保留資料筆數 >= min_days 的 ticker；失敗時回傳空 dict。
    """
    if not tickers:
        return {}
    try:
        _rate_limiter.wait()
        data = _yf_download(
            tickers,
            period=period,
            group_by="ticker",
            threads=True,
            progress=False,
            auto_adjust=True,
            session=_get_session(),
        )
        result: dict[str, list[dict]] = {}
        for ticker in tickers:
            try:
                df = data[ticker] if len(tickers) > 1 else data
                df = df.dropna(how="all")
                if df.empty:
                    continue
                prices = _extract_price_history(df)
                if len(prices) < min_days:
                    logger.debug(
                        "%s 回填歷史資料不足（%d 筆，需 >= %d），略過。",
                        ticker,
                        len(prices),
                        min_days,
                    )
                    continue
                result[ticker] = prices
            except Exception as exc:
                logger.debug("回填擷取 %s 歷史資料失敗（略過）：%s", ticker, exc)
        logger.info("回填批次下載完成：%d/%d 檔有效。", len(result), len(tickers))
        return result
    except Exception as exc:
        logger.warning("回填批次下載失敗（略過，不重試）：%s", exc)
        return {}


def prime_signals_cache_batch(
    ticker_hist_map: dict,
    max_workers: int = SCAN_THREAD_POOL_SIZE,
) -> int:
    """
    從批次下載的歷史資料預熱訊號 L1 + L2 快取。
    預熱路徑結果缺少 institutional_holders，但 price/RSI/MA 等核心欄位完整。
    寫入 L2 讓容器重啟後的暖啟動（warm restart）無需重新下載，訊號預熱耗時從 ~25s 降至 ~0s。
    L1 過期（5 分鐘）後首次 cache miss 會走正常路徑，補完 institutional_holders 並覆寫 L2。
    跳過已在 L1 快取中的 ticker。
    回傳成功預熱的股票數量（不含已在快取中的）。
    """

    def _prime_one(ticker: str, hist) -> str:
        """回傳 'primed' | 'cached' | 'failed'。"""
        if _signals_cache.get(ticker) is not None:
            logger.debug("%s 訊號已在 L1 快取，略過預熱。", ticker)
            return "cached"
        result = _fetch_signals_from_yf(ticker, pre_fetched_hist=hist)
        _signals_cache[ticker] = result
        if not _is_error_dict(result):
            disk_key = f"{DISK_KEY_SIGNALS}:{ticker}"
            _disk_set(disk_key, result, DISK_SIGNALS_TTL)
        return "primed"

    primed = already_cached = 0
    with _FastShutdownExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_prime_one, ticker, hist): ticker
            for ticker, hist in ticker_hist_map.items()
        }
        completed, _ = _run_batch_with_timeout(futures, executor, label="訊號快取預熱")
    for future in completed:
        try:
            outcome = future.result()
            if outcome == "primed":
                primed += 1
            elif outcome == "cached":
                already_cached += 1
        except Exception as e:
            logger.warning("預熱 %s 訊號快取失敗：%s", completed[future], e)
    logger.info(
        "訊號快取預熱完成：%d 新增，%d 已在快取，共 %d 檔。",
        primed,
        already_cached,
        len(ticker_hist_map),
    )
    return primed


def prewarm_signals_batch(
    tickers: list[str], max_workers: int = SCAN_THREAD_POOL_SIZE
) -> dict[str, dict | None]:
    """
    並行預熱多檔股票的技術訊號快取。
    已在 L1/L2 快取中的 ticker 不會重複呼叫 yfinance。
    回傳 {ticker: signals_dict} 對照表。
    """

    results: dict[str, dict | None] = {}
    with _FastShutdownExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(get_technical_signals, t): t for t in tickers}
        completed, timed_out = _run_batch_with_timeout(
            futures, executor, label="訊號預熱"
        )
    for future in completed:
        ticker = completed[future]
        try:
            results[ticker] = future.result()
        except Exception as exc:
            logger.error("預熱 %s 訊號失敗：%s", ticker, exc, exc_info=True)
            results[ticker] = None
    for ticker in timed_out:
        results[ticker] = None
    return results


def count_signals_in_l1(tickers: list[str]) -> int:
    """回傳在 L1 訊號快取中已存在且有效的 ticker 數量。

    僅計入非錯誤結果（不含 {"error": ...}），避免因短暫錯誤快取造成
    scan_service 誤判「L1 已經很暖」而略過 batch download。
    """
    count = 0
    for ticker in tickers:
        cached = _signals_cache.get(ticker)
        if cached is None:
            continue
        if _is_error_dict(cached):
            continue
        count += 1
    return count


def are_all_signals_in_l1(tickers: list[str]) -> bool:
    """若所有 ticker 都已在 L1 訊號快取中，回傳 True。"""
    return all(_signals_cache.get(t) is not None for t in tickers)


# ===========================================================================
# 股價歷史（Price History）
# ===========================================================================


def _extract_price_history(hist) -> list[dict]:
    """從 yfinance history DataFrame 中提取收盤價列表（共用 helper）。"""
    result = []
    for idx, row in hist.iterrows():
        date_str = (
            idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)[:10]
        )
        result.append({"date": date_str, "close": round(row["Close"], 2)})
    return result


def _piggyback_price_history(ticker: str, hist) -> None:
    """將 signals 取得的歷史資料順便寫入 price_history 快取（避免重複 yfinance 呼叫）。"""
    try:
        price_history = _extract_price_history(hist)
        _price_history_cache[ticker] = price_history
        _disk_set(
            f"{DISK_KEY_PRICE_HISTORY}:{ticker}", price_history, DISK_PRICE_HISTORY_TTL
        )
        logger.debug(
            "%s 已 piggyback 寫入 price_history 快取（%d 筆）。",
            ticker,
            len(price_history),
        )
    except Exception as e:
        logger.debug("%s piggyback price_history 失敗（非致命）：%s", ticker, e)


def _fetch_price_history_from_yf(ticker: str) -> list[dict]:
    """獨立 fetcher — 僅在 L1 + L2 皆未命中時才呼叫。"""
    try:
        _stock, hist = _yf_history(ticker, YFINANCE_HISTORY_PERIOD)
        if hist.empty:
            return []
        return _extract_price_history(hist)
    except Exception as e:
        logger.error("無法取得 %s 股價歷史：%s", ticker, e, exc_info=True)
        return []


def get_price_history(ticker: str) -> list[dict] | None:
    """
    取得股價收盤價歷史（1 年）。
    通常由 signals 的 piggyback 預先填充快取，幾乎不需額外 yfinance 呼叫。
    """
    return _cached_fetch(
        _price_history_cache,
        ticker,
        DISK_KEY_PRICE_HISTORY,
        DISK_PRICE_HISTORY_TTL,
        _fetch_price_history_from_yf,
    )


def get_benchmark_close_history(
    ticker: str,
    start: date,
    end: date,
) -> object:
    """
    取得指定基準指數在 [start, end] 日期範圍內的每日收盤價序列。

    回傳 pandas Series（index: DatetimeIndex, values: float），
    僅包含有交易的日期。呼叫端可使用 .asof() 處理市場休日。
    失敗或無資料時回傳 None。
    """
    try:
        _rate_limiter.wait()
        hist = yf.Ticker(ticker, session=_get_session()).history(
            start=start,
            end=end + timedelta(days=1),
            auto_adjust=True,
        )
        if hist.empty:
            return None
        return hist["Close"]
    except Exception as exc:
        logger.warning(
            "無法取得基準指數 %s 歷史資料（%s～%s）：%s", ticker, start, end, exc
        )
        return None


# ===========================================================================
# 護城河趨勢（毛利率 YoY）
# ===========================================================================


def _safe_loc(df, row_labels: list[str], col) -> float | None:
    """Try multiple row labels and return the first non-null value."""
    import math

    for label in row_labels:
        try:
            val = df.loc[label, col]
            if val is not None and not (isinstance(val, float) and math.isnan(val)):
                return float(val)
        except KeyError:
            continue
    return None


def _fetch_moat_from_yf(ticker: str) -> dict:
    """實際從 yfinance 分析護城河趨勢（供 _cached_fetch 使用）。"""
    try:
        financials = _yf_quarterly_financials(ticker)

        if financials is None or financials.empty:
            logger.warning("%s 無法取得季報資料。", ticker)
            return {
                "ticker": ticker,
                "moat": MoatStatus.NOT_AVAILABLE.value,
                "details": "N/A failed to get new data",
            }

        columns = financials.columns.tolist()

        if len(columns) < 2:
            logger.warning("%s 季報資料不足（%d 季），無法分析。", ticker, len(columns))
            return {
                "ticker": ticker,
                "moat": MoatStatus.NOT_AVAILABLE.value,
                "details": "N/A failed to get new data",
            }

        _gross_profit_labels = ["Gross Profit"]
        _operating_profit_labels = ["Operating Profit"]
        _revenue_labels = ["Total Revenue", "Operating Revenue", "Revenue", "Net Sales"]

        def _get_gross_margin(col) -> tuple[float | None, str]:
            """Return (margin_pct, margin_type) where margin_type is 'gross' or 'operating'."""
            gross_profit = _safe_loc(financials, _gross_profit_labels, col)
            margin_type = "gross"
            if gross_profit is None:
                gross_profit = _safe_loc(financials, _operating_profit_labels, col)
                margin_type = "operating"
            revenue = _safe_loc(financials, _revenue_labels, col)
            if gross_profit is not None and revenue and revenue != 0:
                return round(float(gross_profit) / float(revenue) * 100, 2), margin_type
            return None, margin_type

        def _quarter_label(col) -> str:
            if hasattr(col, "month"):
                q = (col.month - 1) // 3 + 1
                return f"{col.year}Q{q}"
            return str(col)[:7]

        # --- 5 季毛利率走勢（防呆：取實際可用筆數與 5 取小）---
        quarters_to_fetch = min(len(columns), MARGIN_TREND_QUARTERS)
        margin_trend: list[dict] = []
        for col in columns[:quarters_to_fetch]:
            gm, _ = _get_gross_margin(col)
            margin_trend.append({"date": _quarter_label(col), "value": gm})
        margin_trend.reverse()  # 最舊在左，最新在右（圖表用）

        # --- YoY 比較 ---
        latest_col = columns[0]
        current_margin, margin_type = _get_gross_margin(latest_col)

        # 優先拿第 5 季（去年同期），不足則拿最舊一季
        if len(columns) >= MARGIN_TREND_QUARTERS:
            yoy_col = columns[MARGIN_TREND_QUARTERS - 1]
        else:
            yoy_col = columns[-1]
        previous_margin, _ = _get_gross_margin(yoy_col)

        # 使用 domain 層的純判定函式
        moat_status, change = determine_moat_status(current_margin, previous_margin)

        if moat_status == MoatStatus.NOT_AVAILABLE:
            return {
                "ticker": ticker,
                "moat": MoatStatus.NOT_AVAILABLE.value,
                "details": "N/A failed to get new data",
                "margin_trend": margin_trend,
            }

        result: dict = {
            "ticker": ticker,
            "current_quarter": str(latest_col.date())
            if hasattr(latest_col, "date")
            else str(latest_col),
            "yoy_quarter": str(yoy_col.date())
            if hasattr(yoy_col, "date")
            else str(yoy_col),
            "current_margin": current_margin,
            "previous_margin": previous_margin,
            "change": change,
            "moat": moat_status.value,
            "margin_trend": margin_trend,
            "margin_type": margin_type,
        }

        result["details"] = build_moat_details(
            moat_status.value, current_margin, previous_margin, change
        )
        if margin_type == "operating":
            result["details"] += " (operating margin)"

        if moat_status == MoatStatus.DETERIORATING:
            logger.warning(
                "%s 護城河惡化：毛利率 %.2f%% → 去年同期 %.2f%%（下降 %.2f pp）",
                ticker,
                current_margin,
                previous_margin,
                abs(change),
            )
        else:
            logger.info(
                "%s 護城河穩健：毛利率 %.2f%% vs 去年同期 %.2f%%（%+.2f pp）",
                ticker,
                current_margin,
                previous_margin,
                change,
            )

        return result

    except Exception as e:
        logger.error("無法分析 %s 護城河：%s", ticker, e, exc_info=True)
        return {
            "ticker": ticker,
            "moat": MoatStatus.NOT_AVAILABLE.value,
            "details": "N/A failed to get new data",
        }


def _is_moat_error(result) -> bool:
    """判斷護城河結果是否為失敗回應（NOT_AVAILABLE 狀態）。"""
    return (
        isinstance(result, dict)
        and result.get("moat") == MoatStatus.NOT_AVAILABLE.value
    )


_moat_failure_counts: dict[str, int] = {}
_moat_failure_lock = threading.Lock()


def analyze_moat_trend(ticker: str) -> dict:
    """分析護城河趨勢。結果快取 1 小時（季報不會頻繁變動）。錯誤結果不寫入 L2/磁碟。

    持續失敗策略：同一 ticker 連續失敗達 MOAT_PERSISTENT_FAILURE_THRESHOLD 次後，
    將錯誤哨兵寫入 L2（1天），避免每次 L1 過期後重複觸發 3 秒的速率限制 API 呼叫。
    成功時重置失敗計數，確保 L2 哨兵過期後可正常恢復。
    """
    result = _cached_fetch(
        _moat_cache,
        ticker,
        DISK_KEY_MOAT,
        DISK_MOAT_TTL,
        _fetch_moat_from_yf,
        is_error=_is_moat_error,
    )

    if _is_moat_error(result):
        with _moat_failure_lock:
            count = _moat_failure_counts.get(ticker, 0) + 1
            _moat_failure_counts[ticker] = count
        # Write the persistent sentinel only once when crossing the threshold.
        if count == MOAT_PERSISTENT_FAILURE_THRESHOLD:
            disk_key = f"{DISK_KEY_MOAT}:{ticker}"
            _disk_set(disk_key, result, DISK_MOAT_PERSISTENT_TTL)
            logger.info(
                "%s 護城河持續失敗 %d 次，寫入 L2 延長快取（TTL=%ds）。",
                ticker,
                count,
                DISK_MOAT_PERSISTENT_TTL,
            )
    else:
        fail_key = f"{DISK_KEY_MOAT}:fail:{ticker}"
        with contextlib.suppress(Exception):
            _disk_cache.delete(fail_key)
        with _moat_failure_lock:
            _moat_failure_counts.pop(ticker, None)

    return result


def prewarm_moat_batch(
    tickers: list[str], max_workers: int = SCAN_THREAD_POOL_SIZE
) -> dict[str, dict | None]:
    """
    並行預熱多檔股票的護城河快取。
    已在 L1/L2 快取中的 ticker 不會重複呼叫 yfinance。
    回傳 {ticker: moat_dict} 對照表。
    """

    results: dict[str, dict | None] = {}
    pending_tickers: list[str] = []
    for ticker in tickers:
        fail_key = f"{DISK_KEY_MOAT}:fail:{ticker}"
        fail_cached = _disk_get(fail_key)
        if fail_cached is not None and _is_moat_error(fail_cached):
            _moat_cache[ticker] = fail_cached
            results[ticker] = fail_cached
            continue
        pending_tickers.append(ticker)

    if not pending_tickers:
        return results

    with _FastShutdownExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(analyze_moat_trend, t): t for t in pending_tickers}
        completed, timed_out = _run_batch_with_timeout(
            futures, executor, label="護城河預熱"
        )
    for future in completed:
        ticker = completed[future]
        try:
            result = future.result()
            results[ticker] = result
            if result is not None and _is_moat_error(result):
                fail_key = f"{DISK_KEY_MOAT}:fail:{ticker}"
                _disk_set(fail_key, result, DISK_MOAT_FAILURE_TTL)
        except Exception as exc:
            logger.error("預熱 %s 護城河失敗：%s", ticker, exc, exc_info=True)
            results[ticker] = None
    for ticker in timed_out:
        results[ticker] = None
    return results


# ===========================================================================
# 市場情緒分析
# ===========================================================================


def analyze_market_sentiment(ticker_list: list[str]) -> dict:
    """
    分析風向球股票的整體市場情緒（5 階段）。
    接受動態的 ticker_list，計算跌破 60MA 的比例。
    """
    if not ticker_list:
        return {
            "status": MarketSentiment.BULLISH.value,
            "details": t("market.no_trend_stocks", lang=DEFAULT_LANGUAGE),
            "below_60ma_pct": 0.0,
        }

    try:
        below_count = 0
        valid_count = 0

        for ticker in ticker_list:
            signals = get_technical_signals(ticker)
            if signals and "error" not in signals:
                valid_count += 1
                price = signals.get("price")
                ma60 = signals.get("ma60")
                if price is not None and ma60 is not None and price < ma60:
                    below_count += 1

        sentiment, pct = determine_market_sentiment(below_count, valid_count)

        if sentiment in _BEARISH_TIERS:
            logger.warning(
                "市場情緒：%s — %.1f%% 的風向球跌破 60MA（%d/%d）",
                sentiment.value,
                pct,
                below_count,
                valid_count,
            )
        else:
            logger.info(
                "市場情緒：%s — %.1f%% 的風向球跌破 60MA（%d/%d）",
                sentiment.value,
                pct,
                below_count,
                valid_count,
            )

        detail_key = f"market.{sentiment.value.lower()}_details"
        return {
            "status": sentiment.value,
            "details": t(
                detail_key,
                lang=DEFAULT_LANGUAGE,
                below=below_count,
                total=valid_count,
            ),
            "below_60ma_pct": pct,
        }

    except Exception as e:
        logger.error("市場情緒分析失敗：%s", e, exc_info=True)
        return {
            "status": MarketSentiment.BULLISH.value,
            "details": t("market.fallback_optimistic", lang=DEFAULT_LANGUAGE),
            "below_60ma_pct": 0.0,
        }


# ===========================================================================
# 財報日曆 (Earnings Calendar)
# ===========================================================================


def _fetch_earnings_from_yf(ticker: str) -> dict:
    """實際從 yfinance 取得財報日期（供 _cached_fetch 使用）。"""
    try:
        cal = _yf_calendar(ticker)

        result: dict = {"ticker": ticker}

        if cal is not None:
            if isinstance(cal, dict):
                earnings_dates = cal.get("Earnings Date", [])
                if earnings_dates:
                    next_date = earnings_dates[0]
                    result["earnings_date"] = (
                        next_date.isoformat()[:10]
                        if hasattr(next_date, "isoformat")
                        else str(next_date)[:10]
                    )
            else:
                if "Earnings Date" in cal.index:
                    val = cal.loc["Earnings Date"].iloc[0]
                    result["earnings_date"] = (
                        val.isoformat()[:10]
                        if hasattr(val, "isoformat")
                        else str(val)[:10]
                    )

        if "earnings_date" not in result:
            result["earnings_date"] = None

        return result

    except Exception as e:
        logger.debug("無法取得 %s 財報日期：%s", ticker, e)
        return {"ticker": ticker, "earnings_date": None}


def get_earnings_date(ticker: str) -> dict:
    """取得下次財報日期。結果快取 24 小時。"""
    return _cached_fetch(
        _earnings_cache,
        ticker,
        DISK_KEY_EARNINGS,
        DISK_EARNINGS_TTL,
        _fetch_earnings_from_yf,
    )


# ===========================================================================
# 股票分割 (Stock Splits)
# ===========================================================================


def _fetch_stock_splits_from_yf(cache_key: str) -> list[dict]:
    """實際從 yfinance 取得股票分割（供 _cached_fetch 使用）。"""
    try:
        ticker, lookback_raw = cache_key.rsplit(":", 1)
        lookback_days = max(1, int(lookback_raw))
    except (ValueError, TypeError):
        ticker = cache_key
        lookback_days = STOCK_SPLIT_LOOKBACK_DAYS

    try:
        splits = _yf_splits(ticker)
    except Exception as exc:
        logger.warning("無法取得 %s 股票分割資訊：%s", ticker, exc)
        return []

    if splits is None or getattr(splits, "empty", True):
        return []

    cutoff = date.today() - timedelta(days=lookback_days)
    rows: list[dict] = []
    for raw_date, raw_ratio in splits.items():
        try:
            ratio = float(raw_ratio)
        except (TypeError, ValueError):
            continue
        if ratio <= 0 or math.isnan(ratio):
            continue

        split_date: date | None = None
        if hasattr(raw_date, "date"):
            split_date = raw_date.date()  # type: ignore[attr-defined]
        elif isinstance(raw_date, date):
            split_date = raw_date
        else:
            try:
                split_date = date.fromisoformat(str(raw_date)[:10])
            except ValueError:
                split_date = None
        if split_date is None or split_date < cutoff:
            continue

        rows.append(
            {
                "ticker": ticker,
                "split_date": split_date.isoformat(),
                "ratio": round(ratio, 8),
            }
        )

    rows.sort(key=lambda x: str(x["split_date"]), reverse=True)
    return rows


def get_stock_splits(
    ticker: str, lookback_days: int = STOCK_SPLIT_LOOKBACK_DAYS
) -> list[dict]:
    """取得近期股票分割事件（含快取）。"""
    normalized_ticker = ticker.upper().strip()
    normalized_lookback = max(1, int(lookback_days))
    cache_key = f"{normalized_ticker}:{normalized_lookback}"
    return _cached_fetch(
        _stock_split_cache,
        cache_key,
        DISK_KEY_STOCK_SPLIT,
        STOCK_SPLIT_CACHE_TTL,
        _fetch_stock_splits_from_yf,
    )


def _fetch_dividend_events_from_yf(
    ticker: str, lookback_days: int = DIVIDEND_LOOKBACK_DAYS
) -> list[dict]:
    """取得近期股息事件（供自動偵測/入帳使用）。"""
    ticker = ticker.upper().strip()
    if lookback_days < 1:
        lookback_days = DIVIDEND_LOOKBACK_DAYS

    try:
        dividends = _yf_dividends(ticker)
    except Exception as exc:
        logger.warning("無法取得 %s 股息事件：%s", ticker, exc)
        return []

    if dividends is None or getattr(dividends, "empty", True):
        return []

    cutoff = date.today() - timedelta(days=lookback_days)
    rows: list[dict] = []
    for raw_date, raw_amount in dividends.items():
        try:
            amount = float(raw_amount)
        except (TypeError, ValueError):
            continue
        if amount <= 0 or math.isnan(amount):
            continue

        ex_date: date | None = None
        if hasattr(raw_date, "date"):
            ex_date = raw_date.date()  # type: ignore[attr-defined]
        elif isinstance(raw_date, date):
            ex_date = raw_date
        else:
            try:
                ex_date = date.fromisoformat(str(raw_date)[:10])
            except ValueError:
                ex_date = None
        if ex_date is None or ex_date < cutoff:
            continue

        rows.append(
            {
                "ticker": ticker,
                "ex_dividend_date": ex_date.isoformat(),
                "amount_per_share": round(amount, 8),
            }
        )
    rows.sort(key=lambda x: x["ex_dividend_date"])
    return rows


def get_dividend_events(
    ticker: str, lookback_days: int = DIVIDEND_LOOKBACK_DAYS
) -> list[dict]:
    """取得近期股息事件（含快取）。"""
    normalized_ticker = ticker.upper().strip()
    normalized_lookback = max(1, int(lookback_days))
    cache_key = f"{normalized_ticker}:{normalized_lookback}"
    return _cached_fetch(
        _dividend_events_cache,
        cache_key,
        DISK_KEY_DIVIDEND_EVENTS,
        DIVIDEND_CACHE_TTL,
        _fetch_dividend_events_from_yf,
    )


# ===========================================================================
# 股息資訊 (Dividend Info)
# ===========================================================================


def _fetch_dividend_from_yf(ticker: str) -> dict:
    """實際從 yfinance 取得股息資訊（供 _cached_fetch 使用）。"""
    try:
        info, dividends = _yf_dividend_data(ticker)

        dividend_yield = info.get("dividendYield")
        ex_date_raw = info.get("exDividendDate")

        ex_dividend_date = None
        if ex_date_raw:
            try:
                if isinstance(ex_date_raw, (int, float)):
                    ex_dividend_date = datetime.fromtimestamp(
                        ex_date_raw, tz=UTC
                    ).strftime("%Y-%m-%d")
                else:
                    ex_dividend_date = str(ex_date_raw)[:10]
            except Exception:
                ex_dividend_date = str(ex_date_raw)[:10]

        # Compute actual YTD dividend per share from payment history (ex-dividend dates).
        # Uses real payments rather than yield-based proration for accuracy.
        ytd_dividend_per_share: float | None = None
        try:
            if dividends is not None and not dividends.empty:
                current_year = datetime.now(tz=UTC).year
                dtidx = pd.DatetimeIndex(dividends.index)
                ytd_divs: pd.Series = dividends[dtidx.year == current_year]  # type: ignore[index,assignment]
                ytd_dividend_per_share = (
                    round(float(ytd_divs.sum()), 6) if not ytd_divs.empty else 0.0
                )
            else:
                ytd_dividend_per_share = 0.0
        except Exception as e:
            logger.debug("無法取得 %s 年初至今股息歷史：%s", ticker, e)

        return {
            "ticker": ticker,
            "dividend_yield": round(dividend_yield * 100, 2)
            if dividend_yield
            else None,
            "ex_dividend_date": ex_dividend_date,
            "ytd_dividend_per_share": ytd_dividend_per_share,
        }

    except Exception as e:
        logger.debug("無法取得 %s 股息資訊：%s", ticker, e)
        return {
            "ticker": ticker,
            "dividend_yield": None,
            "ex_dividend_date": None,
            "ytd_dividend_per_share": None,
        }


def get_dividend_info(ticker: str) -> dict:
    """取得股息資訊。結果快取避免重複呼叫 yfinance。"""
    result = _cached_fetch(
        _dividend_cache,
        ticker,
        DISK_KEY_DIVIDEND,
        DISK_DIVIDEND_TTL,
        _fetch_dividend_from_yf,
        is_error=_is_dividend_error,
    )
    # Evict and re-fetch stale cache entries that predate the ytd_dividend_per_share field.
    if isinstance(result, dict) and "ytd_dividend_per_share" not in result:
        logger.debug(
            "%s 股息快取過期（缺少 ytd_dividend_per_share），清除並重新取得。", ticker
        )
        _dividend_cache.pop(ticker, None)
        _disk_cache.delete(f"{DISK_KEY_DIVIDEND}:{ticker}")
        result = _fetch_dividend_from_yf(ticker)
        _dividend_cache[ticker] = result
        _disk_set(f"{DISK_KEY_DIVIDEND}:{ticker}", result, DISK_DIVIDEND_TTL)
    return result


def _fetch_fundamentals_from_yf(ticker: str) -> dict:
    """從 yfinance 取得股票基本面指標。"""
    try:
        info = _yf_info(ticker)
        return {
            "ticker": ticker,
            "trailing_pe": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "trailing_eps": info.get("trailingEps"),
            "forward_eps": info.get("forwardEps"),
            "market_cap": info.get("marketCap"),
            "price_to_book": info.get("priceToBook"),
            "price_to_sales": info.get("priceToSalesTrailing12Months"),
            "profit_margins": info.get("profitMargins"),
            "operating_margins": info.get("operatingMargins"),
            "return_on_equity": info.get("returnOnEquity"),
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),
        }
    except Exception as exc:
        logger.warning("無法取得 %s 基本面資料：%s", ticker, exc)
        return {
            "ticker": ticker,
            "trailing_pe": None,
            "forward_pe": None,
            "trailing_eps": None,
            "forward_eps": None,
            "market_cap": None,
            "price_to_book": None,
            "price_to_sales": None,
            "profit_margins": None,
            "operating_margins": None,
            "return_on_equity": None,
            "revenue_growth": None,
            "earnings_growth": None,
        }


def get_fundamentals(ticker: str) -> dict:
    """取得股票基本面資料（L1 + L2 快取）。"""
    return _cached_fetch(
        _fundamentals_cache,
        ticker,
        DISK_KEY_FUNDAMENTALS,
        DISK_FUNDAMENTALS_TTL,
        _fetch_fundamentals_from_yf,
    )


# (Forex functions are in infrastructure.market_data.forex — imported above)
# (ETF functions are in infrastructure.market_data.etf — imported above)
# (Sentiment/VIX functions are in infrastructure.market_data.sentiment — imported above)

_BETA_NOT_AVAILABLE: float = (
    -999.0
)  # sentinel: yfinance has no Beta value for this ticker


# ===========================================================================
# 股票 Beta（壓力測試用）
# ===========================================================================


def _fetch_beta_from_yf(ticker: str) -> float:
    """
    從 yfinance info 取得 Beta 值（供 _cached_fetch 使用）。
    回傳實際 Beta 或 _BETA_NOT_AVAILABLE 哨兵值（永不回傳 None，確保可快取）。
    """
    try:
        info = _yf_info(ticker)
        beta = info.get("beta")
        if beta is not None:
            beta = round(float(beta), 2)
            logger.info("%s Beta = %.2f", ticker, beta)
            return beta
        logger.debug("%s yfinance 未提供 Beta 值，使用哨兵值。", ticker)
        return _BETA_NOT_AVAILABLE
    except Exception as e:
        logger.warning("無法取得 %s Beta：%s，使用哨兵值。", ticker, e)
        return _BETA_NOT_AVAILABLE


def get_stock_beta(ticker: str) -> float | None:
    """
    取得股票 Beta 值。
    結果透過 L1 + L2 快取（L1: 24 小時，L2: 7 天）。
    回傳 None 表示 yfinance 無提供（呼叫端應使用 CATEGORY_FALLBACK_BETA）。

    內部使用哨兵值 _BETA_NOT_AVAILABLE 以確保「無 Beta」狀態可被快取，
    避免對無 Beta 的 ticker（如加密貨幣、新 IPO）反覆呼叫 yfinance。
    """
    result = _cached_fetch(
        _beta_cache,
        ticker,
        DISK_KEY_BETA,
        DISK_BETA_TTL,
        _fetch_beta_from_yf,
    )
    # 將哨兵值轉回 None 給呼叫端
    return None if result == _BETA_NOT_AVAILABLE else result


def _compute_and_cache_beta_from_history(
    ticker: str,
    stock_hist,
    market_hist,
) -> float | None:
    """
    從批次下載的價格歷史 DataFrame 計算 Beta，並寫入 L1 + L2 快取。
    stock_hist / market_hist 為 yf.download 回傳的 DataFrame（含 Close 欄）。

    L1/L2 命中時直接回傳快取值，不重複計算。
    計算失敗或資料不足時回退至 get_stock_beta（yfinance info）。
    """
    cached = _beta_cache.get(ticker)
    if cached is not None:
        return None if cached == _BETA_NOT_AVAILABLE else cached
    disk_key = f"{DISK_KEY_BETA}:{ticker}"
    disk_cached = _disk_get(disk_key)
    if disk_cached is not None:
        _beta_cache[ticker] = disk_cached
        return None if disk_cached == _BETA_NOT_AVAILABLE else disk_cached

    try:
        stock_closes = stock_hist["Close"].dropna().tolist()
        market_closes = market_hist["Close"].dropna().tolist()
        beta = compute_beta(
            [float(c) for c in stock_closes],
            [float(c) for c in market_closes],
        )
        if beta is not None:
            logger.info("%s Beta（歷史計算）= %.2f", ticker, beta)
            _beta_cache[ticker] = beta
            _disk_set(disk_key, beta, DISK_BETA_TTL)
            return beta
        logger.debug("%s 歷史資料不足以計算 Beta，回退至 yfinance info。", ticker)
    except Exception as exc:
        logger.warning(
            "從歷史資料計算 %s Beta 失敗，回退至 yfinance info：%s", ticker, exc
        )
    return get_stock_beta(ticker)


def prewarm_beta_batch(
    tickers: list[str],
    max_workers: int = SCAN_THREAD_POOL_SIZE,
    hist_batch: dict | None = None,
) -> dict[str, float | None]:
    """
    並行預熱多檔股票的 Beta 快取。

    快速路徑（hist_batch 提供）：以 OLS 回歸從已下載的價格歷史計算 Beta，
    從 ~267s（逐一呼叫 yfinance info）降至 ~1s。
    hist_batch 需包含 FG_SPY_TICKER（SPY）作為市場基準；若缺少則另行下載。
    快速路徑會先檢查 L1/L2 快取，命中時直接回傳；計算失敗或資料不足時
    自動回退至 yfinance info（慢速路徑）。

    慢速路徑（hist_batch 未提供，或該 ticker 不在 hist_batch 中）：
    回退至原有的 yfinance info 呼叫（已含 L1/L2 快取檢查）。

    回傳 {ticker: beta_or_None} 對照表。
    """

    market_hist = None
    if hist_batch is not None:
        market_hist = hist_batch.get(FG_SPY_TICKER)
        if market_hist is None:
            try:
                spy_batch = batch_download_history([FG_SPY_TICKER])
                market_hist = spy_batch.get(FG_SPY_TICKER)
                if market_hist is not None:
                    logger.info("已額外下載 SPY 歷史資料作為 Beta 計算基準。")
            except Exception as exc:
                logger.warning("下載 SPY 歷史資料失敗，將回退至 yfinance info：%s", exc)

    results: dict[str, float | None] = {}
    with _FastShutdownExecutor(max_workers=max_workers) as executor:
        futures: dict = {}
        for ticker in tickers:
            if (
                hist_batch is not None
                and market_hist is not None
                and ticker in hist_batch
                and ticker != FG_SPY_TICKER
            ):
                futures[
                    executor.submit(
                        _compute_and_cache_beta_from_history,
                        ticker,
                        hist_batch[ticker],
                        market_hist,
                    )
                ] = ticker
            else:
                futures[executor.submit(get_stock_beta, ticker)] = ticker
        completed, timed_out = _run_batch_with_timeout(
            futures, executor, label="Beta 預熱"
        )
    for future in completed:
        ticker = completed[future]
        try:
            results[ticker] = future.result()
        except Exception as exc:
            logger.error("預熱 %s Beta 失敗：%s", ticker, exc, exc_info=True)
            results[ticker] = None
    for ticker in timed_out:
        results[ticker] = None
    return results


# ===========================================================================
# Rogue Wave (瘋狗浪) — 歷史乖離率分佈
# ===========================================================================


def _fetch_bias_distribution_from_yf(ticker: str) -> dict:
    """
    從 yfinance 取得 3 年日線歷史，計算每日乖離率分佈（供 _cached_fetch 使用）。

    回傳：
        {"historical_biases": sorted_list, "count": int, "p95": float, "fetched_at": str}
    失敗時回傳空 dict {}（graceful fallback）。
    """
    try:
        _stock, hist = _yf_history(ticker, ROGUE_WAVE_HISTORY_PERIOD)

        if hist.empty:
            logger.warning("%s 瘋狗浪：yfinance 回傳空資料。", ticker)
            return {}

        closes = hist["Close"].tolist()

        # 計算每日乖離率：每天用截至當天所有資料的 MA60
        biases: list[float] = []
        for i in range(len(closes)):
            if i + 1 < MA60_WINDOW:
                continue  # MA60 尚不可用
            window_closes = closes[i + 1 - MA60_WINDOW : i + 1]
            ma60 = sum(window_closes) / MA60_WINDOW
            bias = compute_bias(closes[i], ma60)
            if bias is None:
                continue
            biases.append(bias)

        if len(biases) < ROGUE_WAVE_MIN_HISTORY_DAYS:
            logger.warning(
                "%s 瘋狗浪：乖離率樣本不足（%d 筆，需 %d 筆）。",
                ticker,
                len(biases),
                ROGUE_WAVE_MIN_HISTORY_DAYS,
            )
            return {}

        biases.sort()
        p95_idx = int(len(biases) * 0.95)
        p95 = biases[min(p95_idx, len(biases) - 1)]

        logger.info(
            "%s 瘋狗浪分佈：%d 筆，P95=%.2f%%",
            ticker,
            len(biases),
            p95,
        )

        return {
            "historical_biases": biases,
            "count": len(biases),
            "p95": round(p95, 2),
            "fetched_at": datetime.now(UTC).isoformat(),
        }

    except Exception as e:
        logger.error("無法取得 %s 瘋狗浪分佈：%s", ticker, e, exc_info=True)
        return {}


def _is_rogue_wave_error(result) -> bool:
    """判斷瘋狗浪分佈結果是否為空（失敗）回應。"""
    return not result  # empty dict is falsy


def get_bias_distribution(ticker: str) -> dict:
    """
    取得股票 3 年歷史乖離率分佈。

    回傳 {"historical_biases": sorted_list, "count": int, "p95": float, "fetched_at": str}
    或空 dict {}（yfinance 失敗 / 資料不足時）。

    結果透過 L1 + L2 快取（L1: 24 小時，L2: 48 小時）。
    歷史偏態分佈變動緩慢，長 TTL 適合此場景。
    錯誤結果（空 dict）僅寫入 L1（短暫），不寫入 L2。
    """
    return _cached_fetch(
        _rogue_wave_cache,
        ticker,
        DISK_KEY_ROGUE_WAVE,
        DISK_ROGUE_WAVE_TTL,
        _fetch_bias_distribution_from_yf,
        is_error=_is_rogue_wave_error,
    )


# ===========================================================================
# 行業板塊（Sector）
# ===========================================================================

_SECTOR_NOT_FOUND: str = "__none__"  # 哨兵值：無法取得 sector 時的快取標記
_NAME_NOT_FOUND: str = "__none__"  # 哨兵值：無法取得 company name 時的快取標記
_EXCHANGE_NOT_FOUND: str = "__none__"  # 哨兵值：無法取得 exchange 時的快取標記


def _fetch_sector_from_yf(ticker: str) -> str:
    """
    從 yfinance info 取得行業板塊。
    回傳行業板塊字串，或 _SECTOR_NOT_FOUND 哨兵值（確保可快取 None 狀態）。
    """
    try:
        _rate_limiter.wait()
        info = _yf_info(ticker)
        sector = info.get("sector")
        if sector:
            logger.info("%s 行業板塊 = %s", ticker, sector)
            return str(sector)
        logger.debug("%s yfinance 未提供 sector，使用哨兵值。", ticker)
        return _SECTOR_NOT_FOUND
    except Exception as e:
        logger.debug("無法取得 %s sector：%s，使用哨兵值。", ticker, e)
        return _SECTOR_NOT_FOUND


def get_ticker_sector(ticker: str) -> str | None:
    """
    取得股票行業板塊（GICS sector）。
    行業板塊極少變動，透過 L2 磁碟快取（30 天 TTL）。
    若快取未命中，會發起 yfinance 網路請求（可能耗時 10–15 秒）。

    回傳板塊名稱字串（如 "Technology"）或 None（無資料 / 非股票）。
    """
    if not ticker:
        return None

    disk_key = f"{DISK_KEY_SECTOR}:{ticker}"
    cached = _disk_get(disk_key)
    if cached is not None:
        return None if cached == _SECTOR_NOT_FOUND else cached

    result = _fetch_sector_from_yf(ticker)
    _disk_set(disk_key, result, DISK_SECTOR_TTL)
    return None if result == _SECTOR_NOT_FOUND else result


def get_ticker_sector_cached(ticker: str) -> str | None:
    """
    從磁碟快取讀取行業板塊（非阻塞版本）。
    若快取未命中，直接回傳 None — 不發起任何 yfinance 網路請求。

    專供熱路徑（如 `/rebalance` 端點）使用，避免因 yfinance 呼叫而阻塞請求。
    背景預熱（prewarm_service）負責填充快取，確保後續呼叫可命中。
    """
    if not ticker:
        return None
    cached = _disk_get(f"{DISK_KEY_SECTOR}:{ticker}")
    if cached is not None:
        return None if cached == _SECTOR_NOT_FOUND else cached
    return None


def prewarm_ticker_sector_batch(
    tickers: list[str], max_workers: int = SCAN_THREAD_POOL_SIZE
) -> None:
    """
    並行預熱多檔股票的行業板塊快取。
    已有磁碟快取的 ticker 直接跳過，避免不必要的 yfinance 請求。
    用於 Approach A 前的批次預熱，讓後續逐一查詢可命中快取。
    """

    uncached = [
        ticker for ticker in tickers if _disk_get(f"{DISK_KEY_SECTOR}:{ticker}") is None
    ]
    if not uncached:
        return

    with _FastShutdownExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(get_ticker_sector, ticker): ticker for ticker in uncached
        }
        completed, _ = _run_batch_with_timeout(futures, executor, label="sector 預熱")
    for future in completed:
        ticker = completed[future]
        try:
            future.result()
        except Exception as exc:
            logger.warning("預熱 %s sector 失敗：%s", ticker, exc)


def _fetch_name_from_yf(ticker: str) -> str:
    """從 yfinance info 取得公司名稱（shortName 優先，fallback longName）。"""
    try:
        _rate_limiter.wait()
        info = _yf_info(ticker)
        short_name = info.get("shortName")
        long_name = info.get("longName")
        name = short_name or long_name
        if name:
            logger.info("%s 公司名稱 = %s", ticker, name)
            return str(name)
        logger.debug("%s yfinance 未提供 company name，使用哨兵值。", ticker)
        return _NAME_NOT_FOUND
    except Exception as e:
        logger.debug("無法取得 %s company name：%s，使用哨兵值。", ticker, e)
        return _NAME_NOT_FOUND


def get_ticker_name(ticker: str) -> str | None:
    """
    取得股票公司名稱（shortName 優先，fallback longName）。
    公司名稱變動極少，透過 L2 磁碟快取（30 天 TTL）。
    """
    if not ticker:
        return None

    disk_key = f"{DISK_KEY_NAME}:{ticker}"
    cached = _disk_get(disk_key)
    if cached is not None:
        return None if cached == _NAME_NOT_FOUND else cached

    result = _fetch_name_from_yf(ticker)
    _disk_set(disk_key, result, DISK_NAME_TTL)
    return None if result == _NAME_NOT_FOUND else result


def get_ticker_name_cached(ticker: str) -> str | None:
    """從磁碟快取讀取股票公司名稱（非阻塞，不發起 yfinance 請求）。"""
    if not ticker:
        return None
    cached = _disk_get(f"{DISK_KEY_NAME}:{ticker}")
    if cached is not None:
        return None if cached == _NAME_NOT_FOUND else cached
    return None


def _fetch_exchange_from_yf(ticker: str) -> str:
    """從 yfinance info 取得交易所代碼（如 NMS, NYQ, TSE）。"""
    try:
        _rate_limiter.wait()
        info = _yf_info(ticker)
        exchange = info.get("exchange")
        if exchange:
            logger.info("%s 交易所 = %s", ticker, exchange)
            return str(exchange)
        logger.debug("%s yfinance 未提供 exchange，使用哨兵值。", ticker)
        return _EXCHANGE_NOT_FOUND
    except Exception as e:
        logger.debug("無法取得 %s exchange：%s，使用哨兵值。", ticker, e)
        return _EXCHANGE_NOT_FOUND


def get_ticker_exchange(ticker: str) -> str | None:
    """
    取得股票交易所代碼（如 NMS, NYQ, TSE）。
    交易所資訊變動極少，透過 L2 磁碟快取（30 天 TTL）。
    """
    if not ticker:
        return None

    disk_key = f"{DISK_KEY_EXCHANGE}:{ticker}"
    cached = _disk_get(disk_key)
    if cached is not None:
        return None if cached == _EXCHANGE_NOT_FOUND else cached

    result = _fetch_exchange_from_yf(ticker)
    _disk_set(disk_key, result, DISK_EXCHANGE_TTL)
    return None if result == _EXCHANGE_NOT_FOUND else result


def get_ticker_exchange_cached(ticker: str) -> str | None:
    """從磁碟快取讀取股票交易所代碼（非阻塞，不發起 yfinance 請求）。"""
    if not ticker:
        return None
    cached = _disk_get(f"{DISK_KEY_EXCHANGE}:{ticker}")
    if cached is not None:
        return None if cached == _EXCHANGE_NOT_FOUND else cached
    return None


def prewarm_ticker_name_batch(
    tickers: list[str], max_workers: int = SCAN_THREAD_POOL_SIZE
) -> None:
    """並行預熱多檔股票的公司名稱快取。"""
    uncached = [
        ticker for ticker in tickers if _disk_get(f"{DISK_KEY_NAME}:{ticker}") is None
    ]
    if not uncached:
        return

    with _FastShutdownExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(get_ticker_name, ticker): ticker for ticker in uncached
        }
        completed, _ = _run_batch_with_timeout(futures, executor, label="name 預熱")
    for future in completed:
        ticker = completed[future]
        try:
            future.result()
        except Exception as exc:
            logger.warning("預熱 %s name 失敗：%s", ticker, exc)


def prewarm_ticker_exchange_batch(
    tickers: list[str], max_workers: int = SCAN_THREAD_POOL_SIZE
) -> None:
    """並行預熱多檔股票的交易所代碼快取。"""
    uncached = [t for t in tickers if _disk_get(f"{DISK_KEY_EXCHANGE}:{t}") is None]
    if not uncached:
        return

    with _FastShutdownExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(get_ticker_exchange, t): t for t in uncached}
        completed, _ = _run_batch_with_timeout(futures, executor, label="exchange 預熱")
    for future in completed:
        ticker = completed[future]
        try:
            future.result()
        except Exception as exc:
            logger.warning("預熱 %s exchange 失敗：%s", ticker, exc)


# ---------------------------------------------------------------------------
# Phase 7 — Performance Since Filing (price pair fetch with disk cache)
# ---------------------------------------------------------------------------


def fetch_price_pair(tickers: list[str], report_date: str) -> dict[str, dict]:
    """Fetch (report_date close, current close) for each ticker using yfinance.

    Uses L2 disk cache with permanent TTL for historical close prices — they are
    immutable once the market closes. Current prices are never cached (always live).
    Returns {ticker: {report_price: float|None, current_price: float|None}}.
    All failures are silently set to None (never raises).
    """
    from datetime import timedelta

    result: dict[str, dict] = {
        t: {"report_price": None, "current_price": None} for t in tickers
    }

    if not tickers:
        return result

    # Load historical (report_date) close prices — try disk cache first
    uncached_tickers: list[str] = []
    report_prices: dict[str, float | None] = {}
    for ticker in tickers:
        disk_key = f"{DISK_KEY_PRICE_PAIR}:{report_date}:{ticker}"
        cached = _disk_get(disk_key)
        if cached is not None:
            report_prices[ticker] = cached.get("report_price")
        else:
            uncached_tickers.append(ticker)

    # Batch-fetch historical prices for uncached tickers
    if uncached_tickers:
        try:
            _rate_limiter.wait()
            end_date = (
                (datetime.fromisoformat(report_date) + timedelta(days=5))
                .date()
                .isoformat()
            )
            hist = _yf_download(
                uncached_tickers,
                start=report_date,
                end=end_date,
                auto_adjust=True,
                progress=False,
                threads=True,
                session=_get_session(),
            )
            for ticker in uncached_tickers:
                rp: float | None = None
                try:
                    if len(uncached_tickers) == 1:
                        rp = float(hist["Close"].iloc[0]) if not hist.empty else None
                    else:
                        col = hist["Close"].get(ticker)
                        if col is not None:
                            dropped = col.dropna()
                            rp = float(dropped.iloc[0]) if not dropped.empty else None
                except Exception as exc:
                    logger.debug("解析 %s 歷史收盤價失敗，設為 None：%s", ticker, exc)
                    rp = None
                report_prices[ticker] = rp
                # Persist to disk cache permanently (historical prices are immutable)
                disk_key = f"{DISK_KEY_PRICE_PAIR}:{report_date}:{ticker}"
                _disk_set(disk_key, {"report_price": rp}, DISK_PRICE_PAIR_TTL)
        except Exception as exc:
            logger.warning(
                "批次下載 %s 歷史收盤價失敗，所有 report_prices 設為 None：%s",
                uncached_tickers,
                exc,
            )
            for ticker in uncached_tickers:
                report_prices[ticker] = None

    # Fetch current prices (never cached — always live)
    current_prices: dict[str, float | None] = dict.fromkeys(tickers)
    try:
        _rate_limiter.wait()
        current = _yf_download(
            tickers,
            period="5d",
            auto_adjust=True,
            progress=False,
            threads=True,
            session=_get_session(),
        )
        for ticker in tickers:
            cp: float | None = None
            try:
                if len(tickers) == 1:
                    cp = float(current["Close"].iloc[-1]) if not current.empty else None
                else:
                    col = current["Close"].get(ticker)
                    if col is not None:
                        dropped = col.dropna()
                        cp = float(dropped.iloc[-1]) if not dropped.empty else None
            except Exception as exc:
                logger.debug("解析 %s 當前收盤價失敗，設為 None：%s", ticker, exc)
                cp = None
            current_prices[ticker] = cp
    except Exception as exc:
        logger.warning("批次下載當前收盤價失敗，所有 current_prices 設為 None：%s", exc)

    for ticker in tickers:
        result[ticker] = {
            "report_price": report_prices.get(ticker),
            "current_price": current_prices.get(ticker),
        }

    return result
