"""Application — Stock Enrichment Service.

Parallel batch enrichment (signals + earnings + dividends + fundamentals),
single-ticker market data wrappers, and market sentiment aggregation.
"""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlmodel import Session

from application.portfolio.nav_sync_service import sync_single_fund_nav
from domain.analysis import (
    compute_bias_percentile,
    detect_rogue_wave,
    determine_scan_signal,
)
from domain.constants import (
    ENRICHED_CACHE_MAXSIZE,
    ENRICHED_CACHE_TTL,
    ENRICHED_PER_TICKER_TIMEOUT,
    ENRICHED_THREAD_POOL_SIZE,
    SKIP_PRICE_FETCH_CATEGORIES,
)
from domain.entities import Stock
from domain.enums import StockCategory
from infrastructure import repositories as repo
from infrastructure.common.cache import SWRCache
from infrastructure.database import engine
from infrastructure.market_data import (
    analyze_moat_trend,
    get_bias_distribution,
    get_crypto_price,
    get_dividend_info,
    get_earnings_date,
    get_fear_greed_index,
    get_fundamentals,
    get_jp_volatility_index,
    get_technical_signals,
    get_ticker_exchange_cached,
    get_ticker_name_cached,
    get_ticker_sector_cached,
    get_tw_volatility_index,
)
from infrastructure.market_data import (
    clear_all_caches as _clear_market_data_caches,
)
from infrastructure.market_data import (
    get_price_history as _get_price_history,
)
from logging_config import get_logger

logger = get_logger(__name__)

_SKIP_DIVIDEND_CATEGORIES = {"Trend_Setter", "Growth", "Cash", "Mutual_Fund"}

# ---------------------------------------------------------------------------
# Enriched-stocks SWR cache + thundering-herd guard
# ---------------------------------------------------------------------------

_ENRICHED_STALE_TTL = ENRICHED_CACHE_TTL * 3
_enriched_cache: SWRCache[str, list[dict]] = SWRCache(
    maxsize=ENRICHED_CACHE_MAXSIZE,
    fresh_ttl=ENRICHED_CACHE_TTL,
    stale_ttl=_ENRICHED_STALE_TTL,
)
_enriched_cache_lock = threading.Lock()
_enriched_in_progress: threading.Event | None = None


def clear_market_data_caches() -> dict:
    """Clear all market-data L1 and L2 caches."""
    return _clear_market_data_caches()


def invalidate_enriched_cache() -> None:
    """主動清除豐富資料快取（股票新增 / 移除 / 停用後呼叫）。"""
    global _enriched_in_progress
    with _enriched_cache_lock:
        _enriched_cache.clear()
        if _enriched_in_progress is not None:
            _enriched_in_progress.set()
        _enriched_in_progress = None


def get_enriched_stocks(session: Session, force_refresh: bool = False) -> list[dict]:
    """
    取得所有啟用中股票，並行附加技術訊號、最近財報日與股息資訊。
    前端可一次取得所有資料，避免逐卡 N+1 API 呼叫。
    結果透過 SWR 快取，在 fresh/stale 視窗內重複請求可快速回應；
    stale 狀態會背景 revalidate。force_refresh=True 可強制同步重算。
    並行 cache miss/force refresh 時，後續請求等待第一個計算完成，避免 thundering herd。
    """
    global _enriched_in_progress
    _cache_key = "enriched"

    while True:
        with _enriched_cache_lock:
            refresh_fn = None if force_refresh else _refresh_enriched_cache_background
            cached, cache_state = _enriched_cache.get(_cache_key, refresh_fn=refresh_fn)
            if cached is not None and not force_refresh:
                logger.debug("豐富資料快取命中（%s）", cache_state)
                return cached

            if _enriched_in_progress is None:
                _enriched_in_progress = threading.Event()
                event_owner = True
            else:
                event_to_wait = _enriched_in_progress
                event_owner = False

        if not event_owner:
            logger.debug("等待豐富資料計算完成...")
            event_to_wait.wait(timeout=120)
            continue

        break

    try:
        stocks = repo.find_active_stocks(session)
    except Exception:
        with _enriched_cache_lock:
            _enriched_in_progress = None
        raise

    if not stocks:
        with _enriched_cache_lock:
            _enriched_in_progress = None
        return []

    try:
        result = _compute_enriched_stocks(stocks)
    except Exception:
        with _enriched_cache_lock:
            if _enriched_in_progress is not None:
                _enriched_in_progress.set()
            _enriched_in_progress = None
        raise

    with _enriched_cache_lock:
        _enriched_cache.set(_cache_key, result)
        if _enriched_in_progress is not None:
            _enriched_in_progress.set()
        _enriched_in_progress = None
    return result


def _refresh_enriched_cache_background() -> list[dict]:
    """Background revalidate path for stale enriched cache entries."""
    with Session(engine) as bg_session:
        stocks = repo.find_active_stocks(bg_session)
        if not stocks:
            return []
        return _compute_enriched_stocks(stocks)


def build_nav_signals(nav_row: object, *, include_nav_date: bool = False) -> dict:
    """Convert a MutualFundNav row into an enrichment-compatible signals dict.

    Shared by stock_service (enrichment pipeline) and scan_service (scan loop).
    """
    prev = nav_row.nav_previous  # type: ignore[attr-defined]
    change_pct = ((nav_row.nav - prev) / prev * 100) if prev else None  # type: ignore[attr-defined]
    result: dict = {
        "price": nav_row.nav,  # type: ignore[attr-defined]
        "previous_close": prev,
        "change_pct": change_pct,
        "rsi": None,
        "bias": None,
        "bias_200": None,
        "volume_ratio": None,
    }
    if include_nav_date:
        result["nav_date"] = str(nav_row.nav_date)  # type: ignore[attr-defined]
    return result


def _get_category_value(stock: Stock) -> str:
    """Return the string value of a stock's category regardless of its runtime type."""
    return (
        stock.category.value
        if hasattr(stock.category, "value")
        else str(stock.category)
    )


def _build_base_stock_dict(stock: Stock, fund_name_by_ticker: dict[str, str]) -> dict:
    """Build the initial enriched dict for a single stock (no network I/O)."""
    from application.stock.stock_service import _str_to_tags

    return {
        "ticker": stock.ticker,
        "category": _get_category_value(stock),
        "current_thesis": stock.current_thesis,
        "current_tags": _str_to_tags(stock.current_tags),
        "display_order": stock.display_order,
        "last_scan_signal": stock.last_scan_signal,
        "is_active": stock.is_active,
        "is_etf": stock.is_etf,
        "name": get_ticker_name_cached(stock.ticker),
        "exchange": get_ticker_exchange_cached(stock.ticker),
        "sector": get_ticker_sector_cached(stock.ticker),
        "signals": None,
        "earnings": None,
        "dividend": None,
        "fundamentals": None,
        "computed_signal": None,
        "price": None,
        "change_pct": None,
        "rsi": None,
        "market_cap": None,
        "trailing_pe": None,
        "nav_date": None,
        "fund_name": fund_name_by_ticker.get(stock.ticker.strip().upper()),
    }


def _merge_enrichment(
    entry: dict,
    signals: dict | None,
    earnings: dict | None,
    dividend: dict | None,
    fundamentals: dict | None,
) -> None:
    """Merge signals/earnings/dividends/fundamentals into a base stock dict in-place."""
    entry["signals"] = signals
    entry["earnings"] = earnings
    entry["dividend"] = dividend
    entry["fundamentals"] = fundamentals
    entry["price"] = (signals or {}).get("price")
    entry["change_pct"] = (signals or {}).get("change_pct")
    entry["rsi"] = (signals or {}).get("rsi")
    entry["nav_date"] = (signals or {}).get("nav_date")
    entry["market_cap"] = (fundamentals or {}).get("market_cap")
    entry["trailing_pe"] = (fundamentals or {}).get("trailing_pe")

    persisted_signal = entry.get("last_scan_signal", "NORMAL")
    if persisted_signal != "THESIS_BROKEN":
        computed = determine_scan_signal(
            moat="NOT_AVAILABLE",
            rsi=(signals or {}).get("rsi"),
            bias=(signals or {}).get("bias"),
            volume_ratio=(signals or {}).get("volume_ratio"),
        )
        entry["computed_signal"] = computed.value
    else:
        entry["computed_signal"] = "THESIS_BROKEN"


def _compute_enriched_stocks(stocks: list[Stock]) -> list[dict]:
    """Inner computation: fetch signals/earnings/dividends for all stocks in parallel."""
    logger.info("批次取得 %d 檔股票的豐富資料...", len(stocks))

    nav_cache: dict[str, dict] = {}
    fund_name_by_ticker: dict[str, str] = {}
    mf_tickers = [
        stock.ticker
        for stock in stocks
        if _get_category_value(stock) == StockCategory.MUTUAL_FUND.value
    ]
    if mf_tickers:
        with Session(engine) as nav_session:
            fund_name_by_ticker = repo.find_fund_names_by_tickers(
                nav_session, mf_tickers
            )
            for ticker in mf_tickers:
                nav_row = repo.get_latest_nav(nav_session, ticker)
                if nav_row:
                    nav_cache[ticker] = build_nav_signals(
                        nav_row, include_nav_date=True
                    )

            missing_mf = [tk for tk in mf_tickers if tk not in nav_cache]
            for ticker in missing_mf:
                try:
                    if sync_single_fund_nav(nav_session, ticker):
                        nav_row = repo.get_latest_nav(nav_session, ticker)
                        if nav_row:
                            nav_cache[ticker] = build_nav_signals(
                                nav_row, include_nav_date=True
                            )
                except Exception:
                    logger.debug("Enrichment NAV fallback failed for %s", ticker)

    enriched: dict[str, dict] = {
        stock.ticker: _build_base_stock_dict(stock, fund_name_by_ticker)
        for stock in stocks
    }

    def _fetch_enrichment(
        ticker: str, cat_value: str, coingecko_id: str | None
    ) -> tuple[str, dict | None, dict | None, dict | None, dict | None]:
        """並行取得單一股票的附加資料。"""
        signals = None
        earnings = None
        dividend = None
        fundamentals = None

        if cat_value == StockCategory.CRYPTO.value:
            crypto_data = get_crypto_price(coingecko_id, ticker)
            price = (
                crypto_data.get("price_usd")
                if crypto_data
                and isinstance(crypto_data.get("price_usd"), (int, float))
                else None
            )
            change_pct = (
                crypto_data.get("change_24h_pct")
                if crypto_data
                and isinstance(crypto_data.get("change_24h_pct"), (int, float))
                else None
            )
            signals = {
                "price": price,
                "change_pct": change_pct,
                "rsi": None,
                "bias": None,
                "bias_200": None,
                "volume_ratio": None,
            }
        elif cat_value == StockCategory.MUTUAL_FUND.value:
            signals = nav_cache.get(ticker)
        elif cat_value not in SKIP_PRICE_FETCH_CATEGORIES:
            signals = get_technical_signals(ticker)

        if cat_value not in SKIP_PRICE_FETCH_CATEGORIES:
            try:
                earnings = get_earnings_date(ticker)
            except Exception as exc:
                logger.debug("取得 %s 除息日失敗，設為 None：%s", ticker, exc)
                earnings = None

        if cat_value not in _SKIP_DIVIDEND_CATEGORIES:
            try:
                dividend = get_dividend_info(ticker)
            except Exception as exc:
                logger.debug("取得 %s 股息資訊失敗，設為 None：%s", ticker, exc)
                dividend = None

        if cat_value not in SKIP_PRICE_FETCH_CATEGORIES:
            try:
                fundamentals = get_fundamentals(ticker)
            except Exception as exc:
                logger.debug("取得 %s 基本面資料失敗，設為 None：%s", ticker, exc)
                fundamentals = None

        return ticker, signals, earnings, dividend, fundamentals

    with ThreadPoolExecutor(max_workers=ENRICHED_THREAD_POOL_SIZE) as executor:
        futures = {
            executor.submit(
                _fetch_enrichment,
                stock.ticker,
                _get_category_value(stock),
                stock.coingecko_id,
            ): stock.ticker
            for stock in stocks
        }
        for future in as_completed(futures):
            tk = futures[future]
            try:
                ticker, signals, earnings, dividend, fundamentals = future.result(
                    timeout=ENRICHED_PER_TICKER_TIMEOUT
                )
                if ticker in enriched:
                    _merge_enrichment(
                        enriched[ticker], signals, earnings, dividend, fundamentals
                    )
            except TimeoutError:
                logger.warning(
                    "批次取得 %s 豐富資料超時（%ds），跳過。",
                    tk,
                    ENRICHED_PER_TICKER_TIMEOUT,
                )
            except Exception as exc:
                logger.error("批次取得 %s 豐富資料失敗：%s", tk, exc, exc_info=True)

    logger.info("批次豐富資料取得完成。")
    return list(enriched.values())


# ---------------------------------------------------------------------------
# Market Data Wrappers (single-ticker)
# ---------------------------------------------------------------------------


def get_signals_for_ticker(session: Session, ticker: str) -> dict | None:
    """Category-aware signals routing — single entry point for all callers.

    Mutual_Fund -> NAV from DB; SKIP categories -> empty; others -> yfinance.
    """
    upper = ticker.upper()
    cat = _resolve_stock_category(session, upper)
    if cat == StockCategory.MUTUAL_FUND.value:
        nav_row = repo.get_latest_nav(session, upper)
        return build_nav_signals(nav_row) if nav_row else {}
    if cat and cat in SKIP_PRICE_FETCH_CATEGORIES:
        return {}
    signals = get_technical_signals(upper)
    if signals:
        signals["bias_distribution"] = get_bias_distribution(upper)
    return signals


def get_enriched_signals_for_ticker(session: Session, ticker: str) -> dict:
    """Return technical signals enriched with bias_percentile and is_rogue_wave flags."""
    signals = get_signals_for_ticker(session, ticker) or {}
    if signals and "error" not in signals:
        bias = signals.get("bias")
        volume_ratio = signals.get("volume_ratio")
        dist = signals.get("bias_distribution")
        bias_percentile: float | None = None
        if dist and bias is not None:
            bias_percentile = compute_bias_percentile(bias, dist["historical_biases"])
        signals["bias_percentile"] = bias_percentile
        signals["is_rogue_wave"] = detect_rogue_wave(bias_percentile, volume_ratio)
    return signals


def get_price_history_for_ticker(session: Session, ticker: str) -> list[dict]:
    """Resolve category once and return the appropriate price history."""
    upper = ticker.upper()
    cat = _resolve_stock_category(session, upper)
    if cat == StockCategory.MUTUAL_FUND.value:
        rows = repo.get_nav_history(session, upper)
        return [
            {"date": str(nav_row.nav_date), "close": nav_row.nav}
            for nav_row in reversed(rows)
        ]
    if cat and cat in SKIP_PRICE_FETCH_CATEGORIES:
        return []
    return _get_price_history(upper) or []


def _resolve_stock_category(session: Session, ticker: str) -> str | None:
    """Look up a stock's category from Stock table, falling back to Holding table."""
    upper = ticker.upper()
    stock = repo.find_stock_by_ticker(session, upper)
    if stock:
        return (
            stock.category.value
            if hasattr(stock.category, "value")
            else str(stock.category)
        )
    holding = repo.find_holding_by_ticker(session, upper)
    if holding:
        return (
            holding.category.value
            if hasattr(holding.category, "value")
            else str(holding.category)
        )
    return None


def get_earnings_for_ticker(session: Session, ticker: str) -> dict | None:
    """Category-aware earnings fetch. Returns None for non-yfinance categories."""
    cat = _resolve_stock_category(session, ticker)
    if cat and cat in SKIP_PRICE_FETCH_CATEGORIES:
        return None
    return get_earnings_date(ticker.upper())


def get_dividend_for_ticker(session: Session, ticker: str) -> dict | None:
    """Category-aware dividend fetch. Returns None for non-yfinance categories."""
    cat = _resolve_stock_category(session, ticker)
    if cat and cat in _SKIP_DIVIDEND_CATEGORIES:
        return None
    return get_dividend_info(ticker.upper())


def get_fundamentals_for_ticker(session: Session, ticker: str) -> dict:
    """Category-aware fundamentals fetch. Returns ticker-only dict for non-yfinance categories."""
    cat = _resolve_stock_category(session, ticker)
    if cat and cat in SKIP_PRICE_FETCH_CATEGORIES:
        return {"ticker": ticker.upper()}
    return get_fundamentals(ticker.upper())


def get_moat_for_ticker(session: Session, ticker: str) -> dict:
    """取得指定股票的護城河趨勢。Bond / Cash 類別直接回傳 N/A。"""
    from domain.constants import SKIP_MOAT_CATEGORIES

    upper_ticker = ticker.upper()
    stock = repo.find_stock_by_ticker(session, upper_ticker)
    if stock and stock.category.value in SKIP_MOAT_CATEGORIES:
        from i18n import get_user_language, t

        lang = get_user_language(session)
        return {
            "ticker": upper_ticker,
            "moat": "N/A",
            "details": t(
                "stock.moat_not_applicable", lang=lang, category=stock.category.value
            ),
        }
    return analyze_moat_trend(upper_ticker)


def get_market_sentiment_multi(session: Session) -> dict:
    """Return sentiment for each market the user has stocks in."""
    result: dict = {"US": get_fear_greed_index()}

    stocks = repo.find_active_stocks(session)

    has_jp = any(stock.ticker.endswith(".T") for stock in stocks)
    if has_jp:
        result["JP"] = get_jp_volatility_index()

    has_tw = any(stock.ticker.endswith(".TW") for stock in stocks)
    if has_tw:
        result["TW"] = get_tw_volatility_index()

    return result
