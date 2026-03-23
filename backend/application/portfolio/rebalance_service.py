"""
Application — Rebalance Service：再平衡分析、匯率曝險、X-Ray、FX 警報。
"""

import json as _json
import threading
import time as _time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Protocol

from sqlmodel import Session, desc, select

from application.formatters import format_stock_display, resolve_display_names
from application.portfolio.alert_ack_service import (
    ACK_TYPE_XRAY,
    acknowledge_alert,
    should_suppress_alert,
)
from application.portfolio.eligibility_service import check_asset_eligibility
from application.portfolio.pricing_service import (
    build_nav_cache as _build_nav_cache,
)
from application.portfolio.pricing_service import (
    resolve_holding_price_with_prev as _resolve_holding_price_with_prev,
)
from application.portfolio.wrapper_service import get_all_wrapper_quotas
from application.stock.stock_service import StockNotFoundError
from domain.analysis import compute_daily_change_pct
from domain.constants import (
    DEFAULT_USER_ID,
    EQUITY_CATEGORIES,
    ERROR_INVALID_INPUT,
    REBALANCE_CACHE_MAXSIZE,
    REBALANCE_CACHE_TTL,
    SKIP_PRICE_FETCH_CATEGORIES,
    XRAY_ACK_STEP_PCT,
    XRAY_SINGLE_STOCK_WARN_PCT,
    XRAY_SKIP_CATEGORIES,
)
from domain.entities import PortfolioSnapshot, Stock, UserInvestmentProfile
from domain.enums import StockCategory
from domain.portfolio.allocation import (
    classify_cash_region,
    compute_asset_class_allocation,
    compute_geographic_allocation,
)
from domain.portfolio.asset_location import (
    compute_optimal_location,
    suggest_tsumitate_migration,
)
from domain.portfolio.tax_wrapper import QuotaStatus
from domain.rebalance import (
    calculate_rebalance as _pure_rebalance,
)
from domain.rebalance import (
    compute_portfolio_health_score,
)
from i18n import get_user_language, t
from infrastructure.common.cache import SWRCache
from infrastructure.database import engine
from infrastructure.market_data import (
    are_all_signals_in_l1,
    detect_is_etf,
    get_etf_sector_weights,
    get_etf_top_holdings,
    get_exchange_rates,
    get_ticker_name_cached,
    get_ticker_sector,
    prewarm_crypto_prices,
    prewarm_etf_holdings_batch,
    prewarm_etf_sector_weights_batch,
    prewarm_signals_batch,
    prewarm_ticker_sector_batch,
)
from infrastructure.notification import (
    is_notification_enabled,
    is_within_rate_limit,
    send_telegram_message_dual,
)
from infrastructure.repositories import (
    delete_drift_acknowledgment,
    find_all_accounts,
    find_all_drift_acknowledgments,
    find_fund_names_by_tickers,
    find_holdings_for_active_accounts,
    log_notification_sent,
)
from logging_config import get_logger

logger = get_logger(__name__)

# 再平衡計算結果的 SWR 快取（key = (display_currency, lang)）。
# stale 視窗可在背景刷新前先回傳舊值，避免前端冷啟動長時間 skeleton。
_REBALANCE_STALE_TTL = REBALANCE_CACHE_TTL * 3
_rebalance_cache: SWRCache[tuple, dict] = SWRCache(
    maxsize=REBALANCE_CACHE_MAXSIZE,
    fresh_ttl=REBALANCE_CACHE_TTL,
    stale_ttl=_REBALANCE_STALE_TTL,
)
_rebalance_cache_lock = threading.Lock()

# In-flight 去重：同一 cache_key 同時只允許一個計算在飛行中。
# 第二個到達的請求等待第一個完成後直接讀快取，避免重複的 yfinance 呼叫。
_rebalance_inflight_lock = threading.Lock()
_rebalance_inflight_events: dict[tuple, threading.Event] = {}

# 等待 in-flight 計算的最長時間；逾時後立即回傳快照降級結果。
_INFLIGHT_WAIT_TIMEOUT: float = 15.0

# 背景計算失敗保護：避免重複失敗時不斷生成新執行緒。
# 記錄最後一次背景計算失敗的時間戳（monotonic）。
_bg_last_failure_at: float = 0.0
_bg_last_failure_lock = threading.Lock()
_BG_RETRY_COOLDOWN: float = 30.0


def _record_bg_failure() -> None:
    """背景計算失敗時記錄時間戳，供冷卻期保護使用。"""
    global _bg_last_failure_at
    with _bg_last_failure_lock:
        _bg_last_failure_at = _time.monotonic()


def invalidate_rebalance_cache() -> None:
    """主動清除再平衡快取（持倉變動後呼叫）。"""
    with _rebalance_cache_lock:
        _rebalance_cache.clear()


def _try_get_snapshot_fallback(
    session: Session,
    display_currency: str,
    lang: str,
) -> dict | None:
    """嘗試以最新日快照作為即時降級回傳值。

    快取冷啟動時使用：讓前端立即看到上次已知的總市值，
    同時背景執行緒繼續計算完整再平衡資料。

    回傳符合 RebalanceResponse 格式的 dict（source='snapshot'），
    若資料庫中尚無快照則回傳 None。
    """
    try:
        snapshot = session.exec(
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.display_currency == display_currency)
            .order_by(desc(PortfolioSnapshot.snapshot_date))
        ).first()
        if snapshot is None:
            return None

        raw_categories: dict = _json.loads(snapshot.category_values or "{}")
        total = snapshot.total_value or 0.0
        categories: dict[str, dict] = {}
        for cat, mv in raw_categories.items():
            pct = (float(mv) / total * 100.0) if total > 0 else 0.0
            categories[cat] = {
                "target_pct": 0.0,
                "current_pct": round(pct, 2),
                "drift_pct": 0.0,
                "market_value": float(mv),
            }

        return {
            "total_value": total,
            "previous_total_value": None,
            "total_value_change": None,
            "total_value_change_pct": None,
            "display_currency": snapshot.display_currency,
            "categories": categories,
            "advice": [t("rebalance.snapshot_fallback_notice", lang=lang)],
            "holdings_detail": [],
            "source": "snapshot",
            "snapshot_at": snapshot.snapshot_date.isoformat(),
            "calculated_at": snapshot.created_at.isoformat(),
        }
    except Exception as exc:
        logger.debug("快照降級查詢失敗（非致命）：%s", exc)
        return None


# ===========================================================================
# 共用持倉市值計算
# ===========================================================================


class _HoldingLike(Protocol):
    """Structural type covering the Holding attributes used by price-resolution helpers."""

    ticker: str
    coingecko_id: str | None
    category: StockCategory
    quantity: float
    cost_basis: float | None
    currency: str


def _compute_holding_market_values(
    holdings: list,
    fx_rates: dict[str, float],
    account_name_by_id: dict[int, str] | None = None,
    *,
    nav_cache: dict[str, dict] | None = None,
) -> tuple[dict[str, float], dict[str, float], dict[str, dict], dict[tuple, dict]]:
    """
    共用邏輯：計算所有持倉的當前與前一交易日市值（已換算目標幣別）。
    回傳 (currency_values, cash_currency_values, ticker_agg, account_ticker_agg)。

    - currency_values: {幣別: 總市值} — 全部持倉（當前）
    - cash_currency_values: {幣別: 現金市值} — 僅現金部位
    - ticker_agg: {ticker: {category, currency, qty, mv, prev_mv, cost_sum, cost_qty, price, fx}}
      其中 prev_mv 為前一交易日市值，用於日漲跌計算
    """
    _nav = nav_cache or {}
    currency_values: dict[str, float] = {}
    cash_currency_values: dict[str, float] = {}
    ticker_agg: dict[str, dict] = {}
    account_ticker_agg: dict[tuple, dict] = {}

    for holding in holdings:
        category = (
            holding.category.value
            if hasattr(holding.category, "value")
            else str(holding.category)
        )
        fx = fx_rates.get(holding.currency, 1.0)

        price, previous_close, has_prev_close = _resolve_holding_price_with_prev(
            holding, _nav
        )
        if holding.is_cash:
            market_value = holding.quantity * fx
            cash_currency_values[holding.currency] = (
                cash_currency_values.get(holding.currency, 0.0) + market_value
            )
            previous_market_value = market_value
        elif price is not None:
            market_value = holding.quantity * price * fx
            if previous_close is not None:
                previous_market_value = holding.quantity * previous_close * fx
            else:
                previous_market_value = market_value
        else:
            # No live price (skip categories or unavailable) — fall back to cost_basis.
            market_value = (
                holding.quantity * holding.cost_basis * fx
                if holding.cost_basis is not None
                else 0.0
            )
            previous_market_value = market_value

        currency_values[holding.currency] = (
            currency_values.get(holding.currency, 0.0) + market_value
        )

        ticker_key = holding.ticker
        if ticker_key not in ticker_agg:
            ticker_agg[ticker_key] = {
                "category": category,
                "currency": holding.currency,
                "qty": 0.0,
                "mv": 0.0,
                "prev_mv": 0.0,
                "cost_sum": 0.0,
                "cost_qty": 0.0,
                "price": price,
                "fx": fx,
                "has_prev_close": False,
                "purchase_fx_rate": getattr(holding, "purchase_fx_rate", None),
            }
        ticker_agg[ticker_key]["qty"] += holding.quantity
        ticker_agg[ticker_key]["mv"] += market_value
        ticker_agg[ticker_key]["prev_mv"] += previous_market_value
        if has_prev_close:
            ticker_agg[ticker_key]["has_prev_close"] = True
        if holding.cost_basis is not None:
            ticker_agg[ticker_key]["cost_sum"] += holding.cost_basis * holding.quantity
            ticker_agg[ticker_key]["cost_qty"] += holding.quantity

        account_key = (holding.account_id, holding.ticker)
        if account_key not in account_ticker_agg:
            account_ticker_agg[account_key] = {
                "account_id": holding.account_id,
                "account_name": (
                    account_name_by_id.get(holding.account_id)
                    if (
                        account_name_by_id is not None
                        and holding.account_id is not None
                    )
                    else None
                ),
                "ticker": holding.ticker,
                "category": category,
                "currency": holding.currency,
                "qty": 0.0,
                "mv": 0.0,
                "prev_mv": 0.0,
                "cost_sum": 0.0,
                "cost_qty": 0.0,
                "price": price,
                "fx": fx,
                "has_prev_close": False,
                "purchase_fx_rate": getattr(holding, "purchase_fx_rate", None),
            }
        account_ticker_agg[account_key]["qty"] += holding.quantity
        account_ticker_agg[account_key]["mv"] += market_value
        account_ticker_agg[account_key]["prev_mv"] += previous_market_value
        if has_prev_close:
            account_ticker_agg[account_key]["has_prev_close"] = True
        if holding.cost_basis is not None:
            account_ticker_agg[account_key]["cost_sum"] += (
                holding.cost_basis * holding.quantity
            )
            account_ticker_agg[account_key]["cost_qty"] += holding.quantity

    return currency_values, cash_currency_values, ticker_agg, account_ticker_agg


def _build_quota_status_map(
    nisa_quotas: dict[str, dict],
    wrappers_present: set[str],
    total_value: float,
) -> dict[str, QuotaStatus]:
    quota_map: dict[str, QuotaStatus] = {}
    for wrapper in ("nisa_growth", "nisa_tsumitate"):
        raw = nisa_quotas.get(wrapper)
        if not raw:
            continue
        quota_map[wrapper] = QuotaStatus(
            wrapper_annual_remaining=float(raw.get("wrapper_annual_remaining", 0.0)),
            combined_annual_remaining=float(raw.get("combined_annual_remaining", 0.0)),
            lifetime_remaining=float(raw.get("lifetime_remaining", 0.0)),
            growth_sub_limit_remaining=(
                float(raw["growth_sub_limit_remaining"])
                if raw.get("growth_sub_limit_remaining") is not None
                else None
            ),
        )

    if "ideco" in wrappers_present:
        # Phase-5 bridge: iDeCo contribution cap model lands in Phase 6.
        ideco_capacity = max(0.0, float(total_value))
        quota_map["ideco"] = QuotaStatus(
            wrapper_annual_remaining=ideco_capacity,
            combined_annual_remaining=ideco_capacity,
            lifetime_remaining=ideco_capacity,
            growth_sub_limit_remaining=None,
        )
    return quota_map


def _compute_category_eligibility_map(
    session: Session,
    ticker_agg: dict[str, dict],
    categories: set[str],
) -> tuple[dict[str, dict[str, bool]], set[str]]:
    wrappers = ("nisa_growth", "nisa_tsumitate", "ideco")
    eligibility_map: dict[str, dict[str, bool]] = {
        wrapper: dict.fromkeys(categories, False) for wrapper in wrappers
    }
    tsumitate_eligible_tickers: set[str] = set()

    for ticker, agg in ticker_agg.items():
        category = str(agg.get("category", ""))
        if category not in categories:
            continue
        for wrapper in wrappers:
            eligibility = check_asset_eligibility(
                session, ticker=ticker, wrapper=wrapper
            )
            if eligibility.eligible:
                eligibility_map[wrapper][category] = True
                if wrapper == "nisa_tsumitate":
                    tsumitate_eligible_tickers.add(ticker.upper())

    return eligibility_map, tsumitate_eligible_tickers


# ===========================================================================
# 再平衡分析
# ===========================================================================


def calculate_rebalance(
    session: Session,
    display_currency: str = "USD",
    force_refresh: bool = False,
) -> dict:
    """
    計算再平衡分析：比較目標配置與實際持倉。
    1. 讀取啟用中的 UserInvestmentProfile（目標配置）
    2. 讀取所有 Holding（實際持倉）
    3. 取得匯率，將所有持倉轉換為 display_currency
    4. 對非現金持倉查詢即時價格
    5. 委託 domain.rebalance 純函式計算偏移與建議

    結果以 (display_currency, lang) 為 key 進行 SWR 快取，避免短時間內重複計算；
    stale 狀態會背景 revalidate。force_refresh=True 可強制同步重算。
    快取命中時更新 calculated_at 為當前時間，避免回傳過期的計算時間戳。
    """
    lang = get_user_language(session)
    _cache_key = (display_currency, lang)

    with _rebalance_cache_lock:
        refresh_fn = None
        if not force_refresh:

            def _refresh_fn() -> dict:
                return _refresh_rebalance_cache_entry(_cache_key)

            refresh_fn = _refresh_fn
        cached, cache_state = _rebalance_cache.get(_cache_key, refresh_fn=refresh_fn)
        if cached is not None and not force_refresh:
            logger.debug(
                "再平衡快取命中（%s）：%s (%s)",
                cache_state,
                display_currency,
                lang,
            )
            return {**cached, "calculated_at": datetime.now(UTC).isoformat()}

    # In-flight 去重：同一 cache_key 同時只有一個計算在飛行中。
    # 後續請求等待主計算完成；若主計算失敗，由一位等待者晉升為新的主計算，
    # 其餘等待者繼續等候，避免所有等待者同時湧入造成雷鳴群效應。
    # 等待最多 _INFLIGHT_WAIT_TIMEOUT 秒；逾時後立即回傳快照降級結果（若有）。
    while True:
        with _rebalance_inflight_lock:
            if _cache_key in _rebalance_inflight_events:
                event = _rebalance_inflight_events[_cache_key]
                is_owner = False
            else:
                event = threading.Event()
                _rebalance_inflight_events[_cache_key] = event
                is_owner = True

        if not is_owner:
            logger.debug("再平衡計算去重等待：%s (%s)", display_currency, lang)
            acquired = event.wait(timeout=_INFLIGHT_WAIT_TIMEOUT)
            with _rebalance_cache_lock:
                cached, state = _rebalance_cache.get(_cache_key)
                if cached is not None and state != "expired":
                    return {**cached, "calculated_at": datetime.now(UTC).isoformat()}
            if not acquired:
                # 等待逾時：優先回傳快照降級結果，讓使用者立即看到上次已知數值
                fallback = _try_get_snapshot_fallback(session, display_currency, lang)
                if fallback is not None:
                    logger.info(
                        "再平衡計算等待逾時，回傳快照降級結果（%s）", display_currency
                    )
                    return fallback
            continue

        # Owner: 若非 force_refresh 且有快照可用，立即回傳快照並在背景計算完整資料
        if not force_refresh:
            fallback = _try_get_snapshot_fallback(session, display_currency, lang)
            if fallback is not None:
                logger.info(
                    "再平衡快取冷啟動：回傳快照降級結果，背景計算完整資料（%s）",
                    display_currency,
                )

                with _bg_last_failure_lock:
                    since_last_failure = _time.monotonic() - _bg_last_failure_at
                    within_cooldown = since_last_failure < _BG_RETRY_COOLDOWN

                if within_cooldown:
                    logger.info(
                        "背景計算冷卻中（%.0f s 前失敗），跳過新執行緒（%s）",
                        since_last_failure,
                        display_currency,
                    )
                    # Clear the inflight entry so the next request can try again
                    # after the cooldown expires instead of waiting indefinitely.
                    event.set()
                    with _rebalance_inflight_lock:
                        _rebalance_inflight_events.pop(_cache_key, None)
                    return fallback

                def _bg_compute(
                    _ck: tuple = _cache_key,
                    _ev: threading.Event = event,
                    _dc: str = display_currency,
                    _lg: str = lang,
                ) -> None:
                    try:
                        with Session(engine) as bg_session:
                            _do_calculate_rebalance(bg_session, _dc, _lg, _ck)
                    except Exception as exc:
                        logger.warning("再平衡背景計算失敗：%s", exc)
                        _record_bg_failure()
                    finally:
                        _ev.set()
                        with _rebalance_inflight_lock:
                            _rebalance_inflight_events.pop(_ck, None)

                threading.Thread(target=_bg_compute, daemon=True).start()
                return fallback

        try:
            return _do_calculate_rebalance(session, display_currency, lang, _cache_key)
        finally:
            event.set()
            with _rebalance_inflight_lock:
                _rebalance_inflight_events.pop(_cache_key, None)


def _load_rebalance_inputs(
    session: Session,
    display_currency: str,
    lang: str,
) -> tuple[dict, list, dict[str, float], dict[int, str], list]:
    """讀取並預熱再平衡所需的所有輸入資料。

    回傳 (target_config, holdings, fx_rates, account_name_by_id, accounts)。
    若無活躍設定檔或無持倉，立即拋出 StockNotFoundError。
    """
    profile = session.exec(
        select(UserInvestmentProfile)
        .where(UserInvestmentProfile.user_id == DEFAULT_USER_ID)
        .where(UserInvestmentProfile.is_active == True)  # noqa: E712
    ).first()
    if not profile:
        raise StockNotFoundError(t("rebalance.no_profile", lang=lang))

    target_config: dict[str, float] = _json.loads(profile.config)

    holdings = find_holdings_for_active_accounts(
        session, include_unlinked=False, user_id=DEFAULT_USER_ID
    )
    if not holdings:
        raise StockNotFoundError(t("rebalance.no_holdings", lang=lang))

    holding_currencies = list({holding.currency for holding in holdings})
    fx_rates = get_exchange_rates(display_currency, holding_currencies)
    logger.info(
        "匯率轉換（→ %s）：%s",
        display_currency,
        {k: round(v, 4) for k, v in fx_rates.items()},
    )

    stock_tickers = list(
        {
            holding.ticker
            for holding in holdings
            if not holding.is_cash
            and holding.category != StockCategory.CRYPTO
            and holding.category.value not in SKIP_PRICE_FETCH_CATEGORIES
        }
    )
    crypto_ids = list(
        {
            holding.coingecko_id
            for holding in holdings
            if (
                not holding.is_cash
                and holding.category == StockCategory.CRYPTO
                and getattr(holding, "coingecko_id", None)
            )
        }
    )
    if stock_tickers:
        if are_all_signals_in_l1(stock_tickers):
            logger.debug(
                "所有 %d 檔股票技術訊號已在 L1 快取，略過預熱。", len(stock_tickers)
            )
        else:
            logger.info("並行預熱 %d 檔股票技術訊號...", len(stock_tickers))
            prewarm_signals_batch(stock_tickers)
    if crypto_ids:
        logger.info("並行預熱 %d 檔加密貨幣報價...", len(crypto_ids))
        prewarm_crypto_prices(crypto_ids)

    accounts = find_all_accounts(session)
    account_name_by_id = {
        account.id: account.name for account in accounts if account.id is not None
    }
    return target_config, holdings, fx_rates, account_name_by_id, accounts


def _build_holdings_detail_list(
    account_ticker_agg: dict[tuple, dict],
    total_value: float,
    fund_name_by_ticker: dict[str, str] | None = None,
) -> list[dict]:
    """個股明細（account+ticker，含佔比、損益、日漲跌）列表，依權重降序排列。"""
    fund_names = fund_name_by_ticker or {}
    holdings_detail = []
    for agg in account_ticker_agg.values():
        avg_cost = (
            round(agg["cost_sum"] / agg["cost_qty"], 2) if agg["cost_qty"] > 0 else None
        )
        weight_pct = (
            round((agg["mv"] / total_value) * 100, 2) if total_value > 0 else 0.0
        )
        cur_price = agg["price"]

        if agg["has_prev_close"]:
            holding_change_pct = compute_daily_change_pct(agg["mv"], agg["prev_mv"])
            holding_change_value = round(agg["mv"] - agg["prev_mv"], 2)
        else:
            holding_change_pct = None
            holding_change_value = None

        cost_total = (
            round(agg["cost_sum"] * agg["fx"], 2) if agg["cost_qty"] > 0 else None
        )
        total_gain_value = (
            round(agg["mv"] - cost_total, 2) if cost_total is not None else None
        )
        total_gain_pct = (
            round((total_gain_value / cost_total) * 100, 2)
            if total_gain_value is not None
            and cost_total is not None
            and cost_total > 0
            else None
        )

        ticker = agg["ticker"]
        category = agg["category"]
        display_name = fund_names.get(ticker.strip().upper()) or get_ticker_name_cached(
            ticker
        )

        holdings_detail.append(
            {
                "account_id": agg["account_id"],
                "account_name": agg.get("account_name"),
                "ticker": ticker,
                "name": display_name,
                "category": category,
                "currency": agg["currency"],
                "quantity": round(
                    agg["qty"],
                    8 if agg["category"] == StockCategory.CRYPTO else 4,
                ),
                "market_value": round(agg["mv"], 2),
                "weight_pct": weight_pct,
                "avg_cost": avg_cost,
                "cost_total": cost_total,
                "current_price": (
                    round(cur_price, 2)
                    if cur_price is not None and isinstance(cur_price, (int, float))
                    else None
                ),
                "fx": round(agg["fx"], 6),
                "change_pct": holding_change_pct,
                "change_value": holding_change_value,
                "total_gain_value": total_gain_value,
                "total_gain_pct": total_gain_pct,
                "purchase_fx_rate": agg.get("purchase_fx_rate"),
                "current_fx_rate": round(agg["fx"], 6),
            }
        )
    holdings_detail.sort(key=lambda x: x["weight_pct"], reverse=True)
    return holdings_detail


def _resolve_etf_holdings(
    ticker: str,
    known_etf_tickers: set[str],
    stock_is_etf_map: dict[str, bool],
    session: Session,
) -> tuple[list[dict] | None, dict[str, float] | None]:
    """Return (constituents, etf_sector_weights) for a ticker.

    If the ticker is a newly-detected ETF, persists the flag to the DB and
    updates the in-memory caches so subsequent tickers in the same loop see
    the updated state.
    """
    if ticker in known_etf_tickers:
        return (
            get_etf_top_holdings(ticker, is_known_etf=True),
            get_etf_sector_weights(ticker, is_known_etf=True),
        )

    if ticker in stock_is_etf_map and detect_is_etf(ticker):
        known_etf_tickers.add(ticker)
        stock_is_etf_map[ticker] = True
        stock_row = session.exec(select(Stock).where(Stock.ticker == ticker)).first()
        if stock_row and not bool(stock_row.is_etf):
            stock_row.is_etf = True
            session.add(stock_row)
            session.commit()
        return (
            get_etf_top_holdings(ticker, is_known_etf=True),
            get_etf_sector_weights(ticker, is_known_etf=True),
        )

    return None, None


def _compute_xray_analysis(
    ticker_agg: dict[str, dict],
    session: Session,
    known_etf_tickers: set[str],
    stock_is_etf_map: dict[str, bool],
) -> tuple[list[dict], float, list[dict]]:
    """X-Ray 穿透式持倉分析：解析 ETF 成分股，計算真實曝險。

    回傳 (xray_entries, xray_coverage_pct, xray_skipped_etfs)。
    known_etf_tickers 與 stock_is_etf_map 可能被更新（自我修復）。
    """
    all_xray_tickers = [
        ticker
        for ticker, agg in ticker_agg.items()
        if agg["category"] not in XRAY_SKIP_CATEGORIES and agg["mv"] > 0
    ]
    xray_tickers = [
        ticker for ticker in all_xray_tickers if ticker in known_etf_tickers
    ]
    if xray_tickers:
        logger.info(
            "X-Ray 預熱：%d/%d 檔符合條件標的為已知 ETF，開始預熱成分股與板塊權重。",
            len(xray_tickers),
            len(all_xray_tickers),
        )
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(prewarm_etf_holdings_batch, xray_tickers),
                pool.submit(prewarm_etf_sector_weights_batch, xray_tickers),
            ]
            for future in futures:
                future.result()

    xray_map: dict[str, dict] = {}
    xray_analyzed_value = 0.0
    xray_skipped_etfs: list[dict[str, object]] = []
    xray_denominator = sum(
        aggregate["mv"]
        for aggregate in ticker_agg.values()
        if aggregate["category"] not in XRAY_SKIP_CATEGORIES and aggregate["mv"] > 0
    )
    xray_pct = (
        (lambda val: round((val / xray_denominator) * 100, 2))
        if xray_denominator > 0
        else (lambda _val: 0.0)
    )

    for ticker, aggregate in ticker_agg.items():
        category = aggregate["category"]
        market_value = aggregate["mv"]
        if category in XRAY_SKIP_CATEGORIES or market_value <= 0:
            continue

        constituents, etf_sector_weights = _resolve_etf_holdings(
            ticker, known_etf_tickers, stock_is_etf_map, session
        )

        if constituents:
            constituent_weight_sum = sum(
                constituent["weight"] for constituent in constituents
            )
            coverage_weight_sum = (
                sum(etf_sector_weights.values())
                if etf_sector_weights
                else constituent_weight_sum
            )
            xray_analyzed_value += market_value * min(coverage_weight_sum, 1.0)
            for constituent in constituents:
                sym = constituent["symbol"]
                weight = constituent["weight"]
                indirect_mv = market_value * weight
                if sym not in xray_map:
                    xray_map[sym] = {
                        "name": constituent.get("name", ""),
                        "direct": 0.0,
                        "indirect": 0.0,
                        "sources": [],
                    }
                xray_map[sym]["indirect"] += indirect_mv
                src_pct = round(weight * 100, 2)
                xray_map[sym]["sources"].append(f"{ticker} ({src_pct}%)")
        elif ticker in known_etf_tickers and not etf_sector_weights:
            skipped_weight_pct = xray_pct(market_value)
            xray_skipped_etfs.append(
                {"ticker": ticker, "weight_pct": skipped_weight_pct}
            )
            logger.warning(
                "X-Ray：%s 為已知 ETF 但成分股無法取得，略過此持倉（不計入直接曝險）。",
                ticker,
            )
        elif ticker in known_etf_tickers and etf_sector_weights:
            coverage_weight_sum = sum(etf_sector_weights.values())
            xray_analyzed_value += market_value * min(coverage_weight_sum, 1.0)
        else:
            xray_analyzed_value += market_value
            if ticker not in xray_map:
                xray_map[ticker] = {
                    "name": "",
                    "direct": 0.0,
                    "indirect": 0.0,
                    "sources": [],
                }
            xray_map[ticker]["direct"] += market_value

    # Batch-resolve missing names for all symbols in xray_map.
    # Use .strip() check to also catch whitespace-only names from ETF data.
    symbols_needing_names = [
        sym for sym, d in xray_map.items() if not (d.get("name") or "").strip()
    ]
    if symbols_needing_names:
        resolved = resolve_display_names(symbols_needing_names, session)
        # resolved keys are uppercase; xray_map keys may use original casing,
        # so look up by normalized key but write back using the original sym.
        for sym in symbols_needing_names:
            resolved_name = resolved.get(sym.strip().upper())
            if resolved_name:
                xray_map[sym]["name"] = resolved_name

    xray_entries = []
    for symbol, data in xray_map.items():
        total_val = data["direct"] + data["indirect"]
        if total_val <= 0:
            continue
        direct_pct = xray_pct(data["direct"])
        indirect_pct = xray_pct(data["indirect"])
        total_pct = xray_pct(total_val)
        xray_entries.append(
            {
                "symbol": symbol,
                "name": data["name"],
                "direct_value": round(data["direct"], 2),
                "direct_weight_pct": direct_pct,
                "indirect_value": round(data["indirect"], 2),
                "indirect_weight_pct": indirect_pct,
                "total_value": round(total_val, 2),
                "total_weight_pct": total_pct,
                "indirect_sources": data["sources"],
            }
        )
    xray_entries.sort(key=lambda x: x["total_weight_pct"], reverse=True)

    return (
        xray_entries,
        xray_pct(xray_analyzed_value),
        sorted(xray_skipped_etfs, key=lambda x: float(x["weight_pct"]), reverse=True),
    )


def _compute_sector_exposure(
    ticker_agg: dict[str, dict],
    known_etf_tickers: set[str],
    etf_constituents_cache: dict[str, list[dict]],
    total_value: float,
) -> list[dict]:
    """行業板塊曝險（僅股票持倉）。

    ETF 穿透：Approach B（板塊權重）優先，A（成分股查詢）後備，兜底歸 ETF。
    """
    sector_values: dict[str, float] = {}
    for ticker, aggregate in ticker_agg.items():
        if aggregate["category"] not in EQUITY_CATEGORIES or aggregate["mv"] <= 0:
            continue
        market_value = aggregate["mv"]

        constituents = etf_constituents_cache.get(ticker)
        etf_sector_weights = (
            get_etf_sector_weights(ticker, is_known_etf=True)
            if ticker in known_etf_tickers
            else None
        )
        if etf_sector_weights:
            for sector_name, weight in etf_sector_weights.items():
                sector_values[sector_name] = (
                    sector_values.get(sector_name, 0.0) + market_value * weight
                )
            logger.debug(
                "%s 使用 ETF 板塊權重分佈（%d 板塊）", ticker, len(etf_sector_weights)
            )
            continue

        if constituents:
            constituent_sector_map: dict[str, float] = {}
            covered_weight = 0.0
            for constituent in constituents:
                constituent_sector = (
                    get_ticker_sector(constituent["symbol"]) or "Unknown"
                )
                constituent_mv = market_value * constituent["weight"]
                constituent_sector_map[constituent_sector] = (
                    constituent_sector_map.get(constituent_sector, 0.0) + constituent_mv
                )
                covered_weight += constituent["weight"]
            for sector_name, sector_mv in constituent_sector_map.items():
                sector_values[sector_name] = (
                    sector_values.get(sector_name, 0.0) + sector_mv
                )

            uncovered_weight = max(0.0, 1.0 - covered_weight)
            if uncovered_weight > 0 and constituent_sector_map:
                known_sectors_excl_unknown = {
                    sector: mv
                    for sector, mv in constituent_sector_map.items()
                    if sector != "Unknown"
                }
                distribute_base = known_sectors_excl_unknown or constituent_sector_map
                base_total = sum(distribute_base.values())
                residual_mv = market_value * uncovered_weight
                if base_total > 0:
                    for sector_name, sector_mv in distribute_base.items():
                        allocated = residual_mv * (sector_mv / base_total)
                        sector_values[sector_name] = (
                            sector_values.get(sector_name, 0.0) + allocated
                        )
                else:
                    sector_values["Unknown"] = (
                        sector_values.get("Unknown", 0.0) + residual_mv
                    )
            logger.debug(
                "%s 使用成分股板塊查詢（%d 檔，覆蓋率 %.1f%%）",
                ticker,
                len(constituents),
                covered_weight * 100,
            )
            continue

        if ticker in known_etf_tickers or detect_is_etf(ticker):
            sector_values["ETF"] = sector_values.get("ETF", 0.0) + market_value
            logger.warning(
                "行業板塊：%s 為 ETF 但板塊權重與成分股皆無法取得，歸類為 ETF。", ticker
            )
            continue

        sector = get_ticker_sector(ticker) or "Unknown"
        sector_values[sector] = sector_values.get(sector, 0.0) + market_value

    equity_total = sum(sector_values.values())
    return [
        {
            "sector": sector,
            "value": round(value, 2),
            "weight_pct": round(value / total_value * 100, 2)
            if total_value > 0
            else 0.0,
            "equity_pct": round(value / equity_total * 100, 2)
            if equity_total > 0
            else 0.0,
        }
        for sector, value in sorted(
            sector_values.items(), key=lambda x: x[1], reverse=True
        )
        if value > 0
    ]


def _build_wrapper_location_result(
    session: Session,
    accounts: list,
    ticker_agg: dict[str, dict],
    account_ticker_agg: dict[tuple, dict],
    total_value: float,
    target_config: dict,
) -> dict:
    """Phase 8: Tax-aware asset location optimization.

    Returns a dict of wrapper-related keys to merge into the rebalance result.
    Returns an empty dict when no tax-advantaged accounts are present.
    """
    wrappers_present = {
        (account.tax_wrapper or "").strip().lower()
        for account in accounts
        if account.tax_wrapper
    }
    if not wrappers_present:
        return {}

    today = datetime.now(UTC).date()
    nisa_quotas = get_all_wrapper_quotas(
        session=session,
        user_id=DEFAULT_USER_ID,
        year=today.year,
        as_of=today,
    )
    quota_map = _build_quota_status_map(nisa_quotas, wrappers_present, total_value)

    category_targets = {
        category: round((float(pct) / 100.0) * total_value, 2)
        for category, pct in target_config.items()
        if float(pct) > 0
    }
    eligibility_map, tsumitate_eligible_tickers = _compute_category_eligibility_map(
        session=session,
        ticker_agg=ticker_agg,
        categories=set(category_targets.keys()),
    )

    account_wrapper_by_id = {
        account.id: (account.tax_wrapper or "tokutei").strip().lower()
        for account in accounts
        if account.id is not None
    }
    current_placements: dict[str, dict[str, float]] = {}
    ticker_categories: dict[str, str] = {}
    growth_holdings: list[dict[str, float | str]] = []
    tokutei_holdings: list[dict[str, float | str]] = []
    for agg in account_ticker_agg.values():
        raw_account_id = agg.get("account_id")
        ticker = str(agg.get("ticker", ""))
        category = str(agg.get("category", ""))
        mv = float(agg.get("mv", 0.0))
        if not ticker or mv <= 0:
            continue
        account_id = raw_account_id if isinstance(raw_account_id, int) else None
        wrapper = (
            account_wrapper_by_id.get(account_id, "tokutei")
            if account_id is not None
            else "tokutei"
        )
        current_placements.setdefault(ticker, {})
        current_placements[ticker][wrapper] = (
            float(current_placements[ticker].get(wrapper, 0.0)) + mv
        )
        ticker_categories[ticker] = category
        if wrapper == "nisa_growth":
            growth_holdings.append({"ticker": ticker, "amount": mv})
        elif wrapper == "tokutei":
            tokutei_holdings.append({"ticker": ticker, "amount": mv})

    location_plan = compute_optimal_location(
        category_targets=category_targets,
        quotas=quota_map,
        eligibility=eligibility_map,
        current_placements=current_placements,
        ticker_categories=ticker_categories,
    )
    tsumitate_quota = quota_map.get(
        "nisa_tsumitate",
        QuotaStatus(
            wrapper_annual_remaining=0.0,
            combined_annual_remaining=0.0,
            lifetime_remaining=0.0,
            growth_sub_limit_remaining=None,
        ),
    )
    location_plan.tsumitate_migration = suggest_tsumitate_migration(
        growth_holdings=growth_holdings,
        tokutei_holdings=tokutei_holdings,
        tsumitate_eligible=tsumitate_eligible_tickers,
        tsumitate_quota=tsumitate_quota,
    )

    return {
        "wrapper_allocations": [
            {
                "wrapper": item.wrapper,
                "categories": item.categories,
                "total": item.total,
            }
            for item in location_plan.wrapper_allocations
        ],
        "placement_suggestions": [
            {
                "ticker": item.ticker,
                "category": item.category,
                "from_wrapper": item.from_wrapper,
                "to_wrapper": item.to_wrapper,
                "amount": item.amount,
                "reason": item.reason,
            }
            for item in location_plan.suggestions
        ],
        "tax_savings_estimate": {
            "annual_nisa_benefit": location_plan.tax_savings_estimate.annual_nisa_benefit,
            "annual_detax_benefit": location_plan.tax_savings_estimate.annual_detax_benefit,
            "annual_ideco_deduction": location_plan.tax_savings_estimate.annual_ideco_deduction,
            "total_annual": location_plan.tax_savings_estimate.total_annual,
            "projected_10yr": location_plan.tax_savings_estimate.projected_10yr,
            "projected_20yr": location_plan.tax_savings_estimate.projected_20yr,
        },
        "tax_efficiency_score": location_plan.tax_efficiency_score,
        "tsumitate_migration": (
            {
                "monthly_amount": location_plan.tsumitate_migration.monthly_amount,
                "source_wrapper": location_plan.tsumitate_migration.source_wrapper,
                "eligible_tickers": location_plan.tsumitate_migration.eligible_tickers,
                "reason": location_plan.tsumitate_migration.reason,
            }
            if location_plan.tsumitate_migration
            else None
        ),
    }


def _build_xray_and_health(
    session: Session,
    ticker_agg: dict[str, dict],
    categories: dict,
) -> tuple[dict, set[str]]:
    """Phase 9: X-Ray ETF look-through analysis and portfolio health score.

    Returns (result_fields, known_etf_tickers).
    known_etf_tickers is passed downstream to the sector/geo allocation phases.
    """
    # 從 DB 取得已知 ETF 集合；stock_is_etf_map 可能在分析中自我修復更新。
    stock_rows = session.exec(select(Stock.ticker, Stock.is_etf)).all()
    stock_is_etf_map: dict[str, bool] = {
        ticker.upper(): bool(is_etf) for ticker, is_etf in stock_rows
    }
    known_etf_tickers: set[str] = {
        ticker for ticker, is_etf in stock_is_etf_map.items() if is_etf
    }
    xray_entries, xray_coverage_pct, xray_skipped_etfs = _compute_xray_analysis(
        ticker_agg, session, known_etf_tickers, stock_is_etf_map
    )
    health_score, health_level = compute_portfolio_health_score(
        categories, xray_entries
    )
    logger.info("投資組合健康分數：%d (%s)", health_score, health_level)
    return (
        {
            "xray": xray_entries,
            "xray_coverage_pct": xray_coverage_pct,
            "xray_skipped_etfs": xray_skipped_etfs,
            "health_score": health_score,
            "health_level": health_level,
        },
        known_etf_tickers,
    )


def _build_spatial_allocation(
    ticker_agg: dict[str, dict],
    known_etf_tickers: set[str],
    total_value: float,
    categories: dict,
) -> dict:
    """Phases 10-12: Sector exposure, geographic allocation, asset class allocation.

    Returns a dict of the three allocation keys to merge into the rebalance result.
    """
    # 10) 行業板塊曝險 — 並行預熱 equity ticker 的 sector 快取
    equity_tickers_for_sector = [
        ticker
        for ticker, agg in ticker_agg.items()
        if agg["category"] in EQUITY_CATEGORIES and agg["mv"] > 0
    ]
    etf_constituents_cache: dict[str, list[dict]] = {}
    constituent_symbols_for_sector: list[str] = []
    for ticker in equity_tickers_for_sector:
        if ticker not in known_etf_tickers:
            continue
        constituents = get_etf_top_holdings(ticker, is_known_etf=True)
        if constituents:
            etf_constituents_cache[ticker] = constituents
            constituent_symbols_for_sector.extend(c["symbol"] for c in constituents)
    all_sector_tickers = list(
        set(equity_tickers_for_sector + constituent_symbols_for_sector)
    )
    if all_sector_tickers:
        logger.info("並行預熱 %d 個 ticker 的 sector 快取...", len(all_sector_tickers))
        prewarm_ticker_sector_batch(all_sector_tickers)

    # 11) 地理區域配置（股票按 ticker 後綴，現金按幣別）
    holding_market_data: list[dict] = []
    for ticker, agg in ticker_agg.items():
        if agg["mv"] <= 0:
            continue
        if agg["category"] == StockCategory.CASH:
            holding_market_data.append(
                {
                    "region": classify_cash_region(agg.get("currency", ticker)),
                    "market_value": agg["mv"],
                }
            )
        else:
            holding_market_data.append({"ticker": ticker, "market_value": agg["mv"]})

    return {
        "sector_exposure": _compute_sector_exposure(
            ticker_agg, known_etf_tickers, etf_constituents_cache, total_value
        ),
        "geographic_allocation": compute_geographic_allocation(holding_market_data),
        # 12) 資產類別配置（Folio 分類 → 標準資產類別）
        "asset_class_allocation": compute_asset_class_allocation(
            {cat: info.get("market_value", 0.0) for cat, info in categories.items()}
        ),
    }


def _do_calculate_rebalance(
    session: Session,
    display_currency: str,
    lang: str,
    _cache_key: tuple,
) -> dict:
    """再平衡計算的實際邏輯（由 calculate_rebalance 呼叫，已完成去重後執行）。

    session 安全性：晉升的等待者仍使用呼叫端注入的 Session。此處安全因為：
    (1) SQLAlchemy 不會回收已被 Session 持有的連線；
    (2) 呼叫端（FastAPI Depends）的 with Session(engine) 區塊在請求結束前不會關閉；
    (3) SQLite 無伺服器端連線逾時；
    (4) 等待時間受限於主計算耗時（數秒）。
    若未來遷移至 PostgreSQL 且啟用連線池 idle timeout，需改為此處開啟獨立 Session。
    """
    # 1-3.5) 讀取設定檔、持倉、匯率、並行預熱
    target_config, holdings, fx_rates, account_name_by_id, accounts = (
        _load_rebalance_inputs(session, display_currency, lang)
    )

    # 4) 計算各持倉市值（含前日市值，用於日漲跌）
    _nav_cache = _build_nav_cache(session, holdings)
    _currency_values, _cash_values, ticker_agg, account_ticker_agg = (
        _compute_holding_market_values(
            holdings,
            fx_rates,
            account_name_by_id,
            nav_cache=_nav_cache,
        )
    )

    # 4.5) 每個分類的市值合計 → 5) domain 純函式計算再平衡建議
    category_values: dict[str, float] = {}
    for aggregate in ticker_agg.values():
        category_values[aggregate["category"]] = (
            category_values.get(aggregate["category"], 0.0) + aggregate["mv"]
        )
    result = _pure_rebalance(category_values, target_config)
    result["advice"] = [
        t(item["key"], lang=lang, **item["params"]) for item in result["advice"]
    ]

    # 6) 投資組合日漲跌
    total_value = result["total_value"]
    previous_total_value = sum(agg["prev_mv"] for agg in ticker_agg.values())
    total_value_change = round(total_value - previous_total_value, 2)
    total_value_change_pct = compute_daily_change_pct(total_value, previous_total_value)
    logger.debug(
        "投資組合日漲跌：previous=%.2f, current=%.2f, change=%.2f (%.2f%%)",
        previous_total_value,
        total_value,
        total_value_change,
        total_value_change_pct if total_value_change_pct is not None else 0.0,
    )
    result["previous_total_value"] = round(previous_total_value, 2)
    result["total_value_change"] = round(total_value_change, 2)
    result["total_value_change_pct"] = total_value_change_pct

    # 7) 個股明細（含公司名稱，供前端顯示）
    mf_tickers = [
        t_ticker
        for t_ticker, agg in ticker_agg.items()
        if agg["category"] == StockCategory.MUTUAL_FUND.value
    ]
    fund_name_by_ticker: dict[str, str] = {}
    if mf_tickers:
        fund_name_by_ticker = find_fund_names_by_tickers(session, mf_tickers)
    result["holdings_detail"] = _build_holdings_detail_list(
        account_ticker_agg, total_value, fund_name_by_ticker
    )
    result["display_currency"] = display_currency

    # 8) Tax-aware asset location optimization
    result.update(
        _build_wrapper_location_result(
            session,
            accounts,
            ticker_agg,
            account_ticker_agg,
            total_value,
            target_config,
        )
    )

    # 9) X-Ray ETF look-through + portfolio health score
    xray_health, known_etf_tickers = _build_xray_and_health(
        session, ticker_agg, result["categories"]
    )
    result.update(xray_health)

    # 10-12) Sector exposure, geographic allocation, asset class allocation
    result.update(
        _build_spatial_allocation(
            ticker_agg, known_etf_tickers, total_value, result["categories"]
        )
    )

    result["calculated_at"] = datetime.now(UTC).isoformat()
    with _rebalance_cache_lock:
        _rebalance_cache.set(_cache_key, result)
    return result


def _refresh_rebalance_cache_entry(cache_key: tuple) -> dict:
    display_currency, lang = cache_key
    with Session(engine) as bg_session:
        return _do_calculate_rebalance(bg_session, display_currency, lang, cache_key)


def send_xray_warnings(
    xray_entries: list[dict],
    display_currency: str,
    session: Session,
) -> list[str]:
    """
    檢查 X-Ray 結果，對超過單一標的風險門檻的持倉發送 Telegram 警告。
    回傳已發送的警告訊息列表。
    """
    lang = get_user_language(session)

    # Cleanup pass: clear stale acks whose concentration has since recovered.
    # Runs *before* the warning loop so recovered symbols can alert again.
    xray_pct_map = {
        str(entry.get("symbol", "")).upper().strip(): float(
            entry.get("total_weight_pct", 0.0) or 0.0
        )
        for entry in xray_entries
    }
    for ack in find_all_drift_acknowledgments(session, alert_type=ACK_TYPE_XRAY):
        current_pct = xray_pct_map.get(ack.alert_key, 0.0)
        if current_pct <= float(XRAY_SINGLE_STOCK_WARN_PCT):
            delete_drift_acknowledgment(
                session, alert_type=ACK_TYPE_XRAY, alert_key=ack.alert_key
            )

    # Resolve names for symbols above the threshold before building messages
    warn_symbols = [
        str(entry["symbol"])
        for entry in xray_entries
        if (
            entry.get("total_weight_pct", 0.0) > XRAY_SINGLE_STOCK_WARN_PCT
            and entry.get("indirect_value", 0.0) > 0
        )
    ]
    xray_names = resolve_display_names(warn_symbols, session)

    warnings: list[str] = []
    suppressed_symbols: list[str] = []
    for entry in xray_entries:
        total_pct = entry.get("total_weight_pct", 0.0)
        indirect_val = entry.get("indirect_value", 0.0)
        if total_pct > XRAY_SINGLE_STOCK_WARN_PCT and indirect_val > 0:
            symbol = entry["symbol"]
            if should_suppress_alert(
                session,
                alert_type=ACK_TYPE_XRAY,
                alert_key=symbol,
                current_value=float(total_pct),
                step_threshold=float(XRAY_ACK_STEP_PCT),
                clear_if_below=float(XRAY_SINGLE_STOCK_WARN_PCT),
            ):
                suppressed_symbols.append(str(symbol))
                continue
            direct_pct = entry.get("direct_weight_pct", 0.0)
            sources = ", ".join(entry.get("indirect_sources", []))
            symbol_display = format_stock_display(
                xray_names.get(str(symbol).strip().upper()), str(symbol)
            )
            msg = t(
                "rebalance.xray_warning",
                lang=lang,
                symbol=symbol_display,
                direct_pct=direct_pct,
                sources=sources,
                total_pct=total_pct,
                threshold=XRAY_SINGLE_STOCK_WARN_PCT,
            )
            warnings.append(msg)
    if suppressed_symbols:
        logger.info(
            "X-Ray alerts suppressed for acknowledged symbols: %s", suppressed_symbols
        )

    if warnings:
        if is_notification_enabled(session, "xray_alerts"):
            if not is_within_rate_limit(session, "xray_alerts"):
                logger.info("X-Ray 通知已達頻率上限，跳過發送。")
                return warnings
            full_msg = (
                t("rebalance.xray_header", lang=lang) + "\n\n" + "\n\n".join(warnings)
            )
            try:
                send_telegram_message_dual(full_msg, session)
                logger.info("已發送 X-Ray 警告（%d 筆）", len(warnings))
                log_notification_sent(session, "xray_alerts")
            except Exception as e:
                logger.warning("X-Ray Telegram 警告發送失敗：%s", e)
        else:
            logger.info("X-Ray 通知已被使用者停用，跳過發送。")

    return warnings


def acknowledge_xray_alert(
    session: Session,
    *,
    symbol: str,
    total_weight_pct: float | None = None,
    display_currency: str = "USD",
) -> dict:
    """Acknowledge one concentrated symbol to suppress repeated X-Ray alerts."""
    normalized_symbol = symbol.upper().strip()
    if not normalized_symbol:
        raise ValueError(ERROR_INVALID_INPUT)

    current_weight = total_weight_pct
    if current_weight is None:
        rebalance = calculate_rebalance(session, display_currency=display_currency)
        xray_entries = rebalance.get("xray", [])
        match = next(
            (
                row
                for row in xray_entries
                if str(row.get("symbol", "")).upper().strip() == normalized_symbol
            ),
            None,
        )
        if match is None:
            raise ValueError(ERROR_INVALID_INPUT)
        current_weight = float(match.get("total_weight_pct", 0.0) or 0.0)

    if float(current_weight) <= float(XRAY_SINGLE_STOCK_WARN_PCT):
        raise ValueError(ERROR_INVALID_INPUT)

    return acknowledge_alert(
        session,
        alert_type=ACK_TYPE_XRAY,
        alert_key=normalized_symbol,
        acknowledged_value=float(current_weight),
    )


# ---------------------------------------------------------------------------
# Backward-compat re-exports from extracted submodules
# (these must come AFTER all local definitions to avoid circular imports)
# ---------------------------------------------------------------------------
from application.portfolio.fx_exposure_service import (  # noqa: E402, F401
    FXAdviceContext,
    calculate_currency_exposure,
    check_fx_alerts,
    send_fx_alerts,
)
from application.portfolio.withdrawal_service import (  # noqa: E402, F401
    calculate_withdrawal,
)
