"""
Application — Rebalance Service：再平衡分析、匯率曝險、X-Ray、FX 警報。
"""

import json as _json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

from sqlmodel import Session, select

from application.portfolio.eligibility_service import check_asset_eligibility
from application.portfolio.wrapper_service import get_all_wrapper_quotas
from application.stock.stock_service import StockNotFoundError
from domain.analysis import compute_daily_change_pct
from domain.constants import (
    DEFAULT_USER_ID,
    EQUITY_CATEGORIES,
    FX_HISTORY_PERIOD,
    REBALANCE_CACHE_MAXSIZE,
    REBALANCE_CACHE_TTL,
    SKIP_PRICE_FETCH_CATEGORIES,
    XRAY_SINGLE_STOCK_WARN_PCT,
    XRAY_SKIP_CATEGORIES,
)
from domain.entities import Stock, UserInvestmentProfile
from domain.enums import FX_ALERT_LABEL, StockCategory
from domain.fx_analysis import (
    FXRateAlert,
    analyze_fx_rate_changes,
    determine_fx_risk_level,
)
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
from infrastructure.cache import SWRCache
from infrastructure.database import engine
from infrastructure.market_data import (
    are_all_signals_in_l1,
    detect_is_etf,
    get_crypto_price,
    get_etf_sector_weights,
    get_etf_top_holdings,
    get_exchange_rates,
    get_forex_history,
    get_forex_history_long,
    get_technical_signals,
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
    find_all_accounts,
    find_holdings_for_active_accounts,
    get_latest_nav,
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


def invalidate_rebalance_cache() -> None:
    """主動清除再平衡快取（持倉變動後呼叫）。"""
    with _rebalance_cache_lock:
        _rebalance_cache.clear()


def _build_nav_cache(session: Session, holdings: list) -> dict[str, dict]:
    """Pre-fetch latest NAV for all Mutual_Fund holdings."""
    cache: dict[str, dict] = {}
    for h in holdings:
        cat = h.category.value if hasattr(h.category, "value") else str(h.category)
        if cat != StockCategory.MUTUAL_FUND.value or h.ticker in cache:
            continue
        nav_row = get_latest_nav(session, h.ticker)
        if nav_row:
            cache[h.ticker] = {
                "nav": nav_row.nav,
                "nav_previous": nav_row.nav_previous,
            }
    return cache


def _resolve_holding_price(
    h: object,
    nav_cache: dict[str, dict],
) -> float | None:
    """Resolve current price for a holding based on its category.

    Returns the raw price (not FX-adjusted). Returns None if unavailable
    (caller should fall back to cost_basis).
    """
    cat = h.category.value if hasattr(h.category, "value") else str(h.category)  # type: ignore[attr-defined]
    if h.is_cash:  # type: ignore[attr-defined]
        return 1.0
    if h.category == StockCategory.CRYPTO:  # type: ignore[attr-defined]
        crypto_data = get_crypto_price(
            getattr(h, "coingecko_id", None),
            h.ticker,  # type: ignore[attr-defined]
        )
        p = crypto_data.get("price_usd") if crypto_data else None
        return float(p) if isinstance(p, (int, float)) else None
    if cat == StockCategory.MUTUAL_FUND.value:
        nav_data = nav_cache.get(h.ticker)  # type: ignore[attr-defined]
        p = nav_data.get("nav") if nav_data else None
        return float(p) if isinstance(p, (int, float)) else None
    if cat in SKIP_PRICE_FETCH_CATEGORIES:
        return None
    signals = get_technical_signals(h.ticker)  # type: ignore[attr-defined]
    p = signals.get("price") if signals else None
    return float(p) if isinstance(p, (int, float)) else None


# ===========================================================================
# 共用持倉市值計算
# ===========================================================================


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

    for h in holdings:
        cat = h.category.value if hasattr(h.category, "value") else str(h.category)
        fx = fx_rates.get(h.currency, 1.0)
        price: float | None = None
        previous_close: float | None = None

        has_prev_close = False

        if h.is_cash:
            # 現金部位無日內價格變動
            market_value = h.quantity * fx
            previous_market_value = market_value  # 現金前後市值相同
            has_prev_close = True  # 現金視為「有前日資料」（變動固定為 0）
            price = 1.0
            cash_currency_values[h.currency] = (
                cash_currency_values.get(h.currency, 0.0) + market_value
            )
        elif h.category == StockCategory.CRYPTO:
            crypto_data = get_crypto_price(
                getattr(h, "coingecko_id", None),
                h.ticker,
            )
            price = crypto_data.get("price_usd") if crypto_data else None
            change_24h_pct = crypto_data.get("change_24h_pct") if crypto_data else None
            if (
                price is not None
                and isinstance(price, (int, float))
                and change_24h_pct is not None
                and isinstance(change_24h_pct, (int, float))
                and (1 + change_24h_pct / 100) != 0
            ):
                previous_close = price / (1 + change_24h_pct / 100)
            else:
                previous_close = None

            if price is not None and isinstance(price, (int, float)):
                market_value = h.quantity * price * fx
            elif h.cost_basis is not None:
                market_value = h.quantity * h.cost_basis * fx
            else:
                market_value = 0.0

            if previous_close is not None and isinstance(previous_close, (int, float)):
                previous_market_value = h.quantity * previous_close * fx
                has_prev_close = True
            else:
                previous_market_value = market_value
        elif cat == StockCategory.MUTUAL_FUND.value:
            nav_data = _nav.get(h.ticker)
            price = nav_data.get("nav") if nav_data else None
            previous_close = nav_data.get("nav_previous") if nav_data else None

            if price is not None and isinstance(price, (int, float)):
                market_value = h.quantity * price * fx
            elif h.cost_basis is not None:
                market_value = h.quantity * h.cost_basis * fx
            else:
                market_value = 0.0

            if previous_close is not None and isinstance(previous_close, (int, float)):
                previous_market_value = h.quantity * previous_close * fx
                has_prev_close = True
            else:
                previous_market_value = market_value
        elif cat in SKIP_PRICE_FETCH_CATEGORIES:
            if h.cost_basis is not None:
                market_value = h.quantity * h.cost_basis * fx
            else:
                market_value = 0.0
            previous_market_value = market_value
            has_prev_close = True
        else:
            # 一般持倉：取得當前與前一交易日價格
            signals = get_technical_signals(h.ticker)
            price = signals.get("price") if signals else None
            previous_close = signals.get("previous_close") if signals else None

            if price is not None and isinstance(price, (int, float)):
                market_value = h.quantity * price * fx
            elif h.cost_basis is not None:
                market_value = h.quantity * h.cost_basis * fx
            else:
                market_value = 0.0

            if previous_close is not None and isinstance(previous_close, (int, float)):
                previous_market_value = h.quantity * previous_close * fx
                has_prev_close = True
            else:
                previous_market_value = market_value

        currency_values[h.currency] = (
            currency_values.get(h.currency, 0.0) + market_value
        )

        key = h.ticker
        if key not in ticker_agg:
            ticker_agg[key] = {
                "category": cat,
                "currency": h.currency,
                "qty": 0.0,
                "mv": 0.0,
                "prev_mv": 0.0,
                "cost_sum": 0.0,
                "cost_qty": 0.0,
                "price": price,
                "fx": fx,
                "has_prev_close": False,
                "purchase_fx_rate": getattr(h, "purchase_fx_rate", None),
            }
        ticker_agg[key]["qty"] += h.quantity
        ticker_agg[key]["mv"] += market_value
        ticker_agg[key]["prev_mv"] += previous_market_value
        if has_prev_close:
            ticker_agg[key]["has_prev_close"] = True
        if h.cost_basis is not None:
            ticker_agg[key]["cost_sum"] += h.cost_basis * h.quantity
            ticker_agg[key]["cost_qty"] += h.quantity
        account_key = (h.account_id, h.ticker)
        if account_key not in account_ticker_agg:
            account_ticker_agg[account_key] = {
                "account_id": h.account_id,
                "account_name": (
                    account_name_by_id.get(h.account_id)
                    if (account_name_by_id is not None and h.account_id is not None)
                    else None
                ),
                "ticker": h.ticker,
                "category": cat,
                "currency": h.currency,
                "qty": 0.0,
                "mv": 0.0,
                "prev_mv": 0.0,
                "cost_sum": 0.0,
                "cost_qty": 0.0,
                "price": price,
                "fx": fx,
                "has_prev_close": False,
                "purchase_fx_rate": getattr(h, "purchase_fx_rate", None),
            }
        account_ticker_agg[account_key]["qty"] += h.quantity
        account_ticker_agg[account_key]["mv"] += market_value
        account_ticker_agg[account_key]["prev_mv"] += previous_market_value
        if has_prev_close:
            account_ticker_agg[account_key]["has_prev_close"] = True
        if h.cost_basis is not None:
            account_ticker_agg[account_key]["cost_sum"] += h.cost_basis * h.quantity
            account_ticker_agg[account_key]["cost_qty"] += h.quantity

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
            event.wait()
            with _rebalance_cache_lock:
                cached, state = _rebalance_cache.get(_cache_key)
                if cached is not None and state != "expired":
                    return {**cached, "calculated_at": datetime.now(UTC).isoformat()}
            continue

        try:
            return _do_calculate_rebalance(session, display_currency, lang, _cache_key)
        finally:
            event.set()
            with _rebalance_inflight_lock:
                _rebalance_inflight_events.pop(_cache_key, None)


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

    # 1) 取得目標配置
    profile = session.exec(
        select(UserInvestmentProfile)
        .where(UserInvestmentProfile.user_id == DEFAULT_USER_ID)
        .where(UserInvestmentProfile.is_active == True)  # noqa: E712
    ).first()

    if not profile:
        raise StockNotFoundError(t("rebalance.no_profile", lang=lang))

    target_config: dict[str, float] = _json.loads(profile.config)

    # 2) 取得持倉（僅啟用帳戶）
    holdings = find_holdings_for_active_accounts(
        session,
        include_unlinked=False,
        user_id=DEFAULT_USER_ID,
    )

    if not holdings:
        raise StockNotFoundError(t("rebalance.no_holdings", lang=lang))

    # 3) 取得匯率：收集所有持倉幣別，批次取得相對 display_currency 的匯率
    holding_currencies = list({h.currency for h in holdings})
    fx_rates = get_exchange_rates(display_currency, holding_currencies)
    logger.info(
        "匯率轉換（→ %s）：%s",
        display_currency,
        {k: round(v, 4) for k, v in fx_rates.items()},
    )

    # 3.5) 並行預熱：股票技術訊號 + 加密貨幣價格
    stock_tickers = list(
        {
            h.ticker
            for h in holdings
            if not h.is_cash and h.category != StockCategory.CRYPTO
        }
    )
    crypto_ids = list(
        {
            h.coingecko_id
            for h in holdings
            if (
                not h.is_cash
                and h.category == StockCategory.CRYPTO
                and getattr(h, "coingecko_id", None)
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

    # 4) 使用共用邏輯計算各持倉市值
    _nav_cache = _build_nav_cache(session, holdings)
    _currency_values, _cash_values, ticker_agg, account_ticker_agg = (
        _compute_holding_market_values(
            holdings,
            fx_rates,
            account_name_by_id,
            nav_cache=_nav_cache,
        )
    )

    # 4.5) 取得每個分類的市值合計
    category_values: dict[str, float] = {}
    for agg in ticker_agg.values():
        cat = agg["category"]
        category_values[cat] = category_values.get(cat, 0.0) + agg["mv"]

    # 5) 委託 domain 純函式計算
    result = _pure_rebalance(category_values, target_config)

    # 5.5) 將 domain 回傳的結構化建議翻譯為用戶語言字串
    result["advice"] = [
        t(item["key"], lang=lang, **item["params"]) for item in result["advice"]
    ]

    # 6) 計算投資組合日漲跌
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

    # 加入結果
    result["previous_total_value"] = round(previous_total_value, 2)
    result["total_value_change"] = round(total_value_change, 2)
    result["total_value_change_pct"] = total_value_change_pct

    # 7) 建立個股明細（account+ticker，含佔比）
    holdings_detail = []
    for agg in account_ticker_agg.values():
        avg_cost = (
            round(agg["cost_sum"] / agg["cost_qty"], 2) if agg["cost_qty"] > 0 else None
        )
        weight_pct = (
            round((agg["mv"] / total_value) * 100, 2) if total_value > 0 else 0.0
        )
        cur_price = agg["price"]

        # 計算個股日漲跌百分比（無前日資料時回傳 None → 前端顯示 N/A）
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

        holdings_detail.append(
            {
                "account_id": agg["account_id"],
                "account_name": agg.get("account_name"),
                "ticker": agg["ticker"],
                "category": agg["category"],
                "currency": agg["currency"],
                "quantity": round(
                    agg["qty"], 8 if agg["category"] == StockCategory.CRYPTO else 4
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

    # 依權重降序排列（最大持倉在前）
    holdings_detail.sort(key=lambda x: x["weight_pct"], reverse=True)
    result["holdings_detail"] = holdings_detail
    result["display_currency"] = display_currency

    # 8) Tax-aware asset location optimization (Phase 5)
    wrappers_present = {
        (account.tax_wrapper or "").strip().lower()
        for account in accounts
        if account.tax_wrapper
    }
    has_wrappers = bool(wrappers_present)
    if has_wrappers:
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
        all_categories = set(category_targets.keys())
        eligibility_map, tsumitate_eligible_tickers = _compute_category_eligibility_map(
            session=session,
            ticker_agg=ticker_agg,
            categories=all_categories,
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

        result["wrapper_allocations"] = [
            {
                "wrapper": item.wrapper,
                "categories": item.categories,
                "total": item.total,
            }
            for item in location_plan.wrapper_allocations
        ]
        result["placement_suggestions"] = [
            {
                "ticker": item.ticker,
                "category": item.category,
                "from_wrapper": item.from_wrapper,
                "to_wrapper": item.to_wrapper,
                "amount": item.amount,
                "reason": item.reason,
            }
            for item in location_plan.suggestions
        ]
        result["tax_savings_estimate"] = {
            "annual_nisa_benefit": location_plan.tax_savings_estimate.annual_nisa_benefit,
            "annual_detax_benefit": location_plan.tax_savings_estimate.annual_detax_benefit,
            "annual_ideco_deduction": location_plan.tax_savings_estimate.annual_ideco_deduction,
            "total_annual": location_plan.tax_savings_estimate.total_annual,
            "projected_10yr": location_plan.tax_savings_estimate.projected_10yr,
            "projected_20yr": location_plan.tax_savings_estimate.projected_20yr,
        }
        result["tax_efficiency_score"] = location_plan.tax_efficiency_score
        result["tsumitate_migration"] = (
            {
                "monthly_amount": location_plan.tsumitate_migration.monthly_amount,
                "source_wrapper": location_plan.tsumitate_migration.source_wrapper,
                "eligible_tickers": location_plan.tsumitate_migration.eligible_tickers,
                "reason": location_plan.tsumitate_migration.reason,
            }
            if location_plan.tsumitate_migration
            else None
        )

    # 9) X-Ray: 穿透式持倉分析（解析 ETF 成分股，計算真實曝險）
    # 從 DB 取得已知 ETF 集合，用於識別成分股暫時無法取得的 ETF 持倉。
    # 這樣當 yfinance 暫時故障時，不會將 ETF 誤標記為直接持倉。
    stock_rows = session.exec(select(Stock.ticker, Stock.is_etf)).all()
    stock_is_etf_map: dict[str, bool] = {
        ticker.upper(): bool(is_etf) for ticker, is_etf in stock_rows
    }
    known_etf_tickers: set[str] = {
        ticker for ticker, is_etf in stock_is_etf_map.items() if is_etf
    }
    # 先計算所有符合 X-Ray 條件的股票，再過濾為已知 ETF 進行預熱。
    all_xray_tickers = [
        t
        for t, agg in ticker_agg.items()
        if agg["category"] not in XRAY_SKIP_CATEGORIES and agg["mv"] > 0
    ]
    xray_tickers = [t for t in all_xray_tickers if t in known_etf_tickers]
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

    xray_map: dict[str, dict] = {}  # symbol -> {direct, indirect, sources, name}
    xray_analyzed_value = 0.0
    xray_skipped_etfs: list[dict[str, object]] = []
    xray_denominator = sum(
        agg["mv"]
        for agg in ticker_agg.values()
        if agg["category"] not in XRAY_SKIP_CATEGORIES and agg["mv"] > 0
    )
    xray_pct = (
        (lambda val: round((val / xray_denominator) * 100, 2))
        if xray_denominator > 0
        else (lambda _val: 0.0)
    )

    for ticker, agg in ticker_agg.items():
        cat = agg["category"]
        mv = agg["mv"]
        if cat in XRAY_SKIP_CATEGORIES or mv <= 0:
            continue

        if ticker in known_etf_tickers:
            # 僅已知 ETF 需要查詢成分股與板塊權重。
            constituents = get_etf_top_holdings(ticker, is_known_etf=True)
            etf_sector_weights = get_etf_sector_weights(ticker, is_known_etf=True)
        elif ticker in stock_is_etf_map and detect_is_etf(ticker):
            # 自我修復：DB 中舊資料可能把 ETF 標成非 ETF（如早期匯入或暫時性偵測失敗）。
            # 此處做 runtime 偵測，立即啟用 X-Ray 穿透，並回寫本次 session。
            known_etf_tickers.add(ticker)
            stock_is_etf_map[ticker] = True
            stock_row = session.exec(
                select(Stock).where(Stock.ticker == ticker)
            ).first()
            if stock_row and not bool(stock_row.is_etf):
                stock_row.is_etf = True
                session.add(stock_row)
                session.commit()
            constituents = get_etf_top_holdings(ticker, is_known_etf=True)
            etf_sector_weights = get_etf_sector_weights(ticker, is_known_etf=True)
        else:
            constituents = None
            etf_sector_weights = None

        if constituents:
            constituent_weight_sum = sum(c["weight"] for c in constituents)
            if etf_sector_weights:
                coverage_weight_sum = sum(etf_sector_weights.values())
            else:
                coverage_weight_sum = constituent_weight_sum
            xray_analyzed_value += mv * min(coverage_weight_sum, 1.0)
            for c in constituents:
                sym = c["symbol"]
                weight = c["weight"]
                indirect_mv = mv * weight
                if sym not in xray_map:
                    xray_map[sym] = {
                        "name": c.get("name", ""),
                        "direct": 0.0,
                        "indirect": 0.0,
                        "sources": [],
                    }
                xray_map[sym]["indirect"] += indirect_mv
                src_pct = round(weight * 100, 2)
                xray_map[sym]["sources"].append(f"{ticker} ({src_pct}%)")
        elif ticker in known_etf_tickers and not etf_sector_weights:
            # 已知 ETF 但成分股暫時無法取得（yfinance 故障或快取失效）。
            # 排除此 ETF，避免將其誤標記為直接持倉，導致 X-Ray 失真。
            skipped_weight_pct = xray_pct(mv)
            xray_skipped_etfs.append(
                {"ticker": ticker, "weight_pct": skipped_weight_pct}
            )
            logger.warning(
                "X-Ray：%s 為已知 ETF 但成分股無法取得，略過此持倉（不計入直接曝險）。",
                ticker,
            )
        elif ticker in known_etf_tickers and etf_sector_weights:
            # 已知 ETF 雖無成分股明細，但有板塊權重可分析曝險覆蓋率。
            coverage_weight_sum = sum(etf_sector_weights.values())
            xray_analyzed_value += mv * min(coverage_weight_sum, 1.0)
        else:
            xray_analyzed_value += mv
            # 非 ETF 或未納入 Stock 表的 ETF 一律視為直接持倉。
            # 若要啟用 ETF 穿透分析，需先將該標的加入 watchlist 並設定 is_etf=True。
            if ticker not in xray_map:
                xray_map[ticker] = {
                    "name": "",
                    "direct": 0.0,
                    "indirect": 0.0,
                    "sources": [],
                }
            xray_map[ticker]["direct"] += mv

    # 組合 X-Ray 結果
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
    result["xray"] = xray_entries
    result["xray_coverage_pct"] = xray_pct(xray_analyzed_value)
    result["xray_skipped_etfs"] = sorted(
        xray_skipped_etfs,
        key=lambda x: float(x["weight_pct"]),
        reverse=True,
    )

    # 9) 投資組合健康分數
    health_score, health_level = compute_portfolio_health_score(
        result["categories"],
        xray_entries,
    )
    result["health_score"] = health_score
    result["health_level"] = health_level
    logger.info("投資組合健康分數：%d (%s)", health_score, health_level)

    # 10) 行業板塊曝險（僅股票持倉，Bond/Cash 排除）
    # ETF 穿透策略：
    #   Approach B（主要）：使用 yfinance funds_data.sector_weightings，涵蓋 ETF 全部資產。
    #   Approach A（後備）：若 B 無資料，分解 top-N 成分股並查詢各自板塊，
    #                       未覆蓋的剩餘比例按已辨識板塊比例分配（避免膨脹 Unknown）。
    #   ETF 兜底：若為已知 ETF 且 A/B 都無資料，歸類到 ETF（資料不足）而非 Unknown。
    #   直接持股：使用 get_ticker_sector() 磁碟快取（30 天 TTL）。

    # 並行預熱所有 equity 持倉及已知 ETF 成分股的 sector 快取，
    # 讓後續逐一查詢（Approach A 及直接持股）直接命中磁碟快取。
    # 同時快取 get_etf_top_holdings 結果，避免下方主迴圈重複呼叫。
    equity_tickers_for_sector = [
        ticker
        for ticker, agg in ticker_agg.items()
        if agg["category"] in EQUITY_CATEGORIES and agg["mv"] > 0
    ]
    # Collect constituent results once — reused in sector loop below
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

    sector_values: dict[str, float] = {}
    for ticker, agg in ticker_agg.items():
        if agg["category"] not in EQUITY_CATEGORIES or agg["mv"] <= 0:
            continue
        mv = agg["mv"]

        # 從預熱時收集的快取讀取成分股，避免重複呼叫 get_etf_top_holdings
        constituents = etf_constituents_cache.get(ticker)
        # Approach B：先嘗試 ETF 官方板塊權重分佈（與成分股資料來源獨立）
        etf_sector_weights = (
            get_etf_sector_weights(ticker, is_known_etf=True)
            if ticker in known_etf_tickers
            else None
        )
        if etf_sector_weights:
            for sector_name, weight in etf_sector_weights.items():
                sector_values[sector_name] = (
                    sector_values.get(sector_name, 0.0) + mv * weight
                )
            logger.debug(
                "%s 使用 ETF 板塊權重分佈（%d 板塊）",
                ticker,
                len(etf_sector_weights),
            )
            continue

        if constituents:
            # Approach A：分解成分股，逐一查詢板塊
            constituent_sector_map: dict[str, float] = {}
            covered_weight = 0.0
            for c in constituents:
                c_sector = get_ticker_sector(c["symbol"]) or "Unknown"
                c_mv = mv * c["weight"]
                constituent_sector_map[c_sector] = (
                    constituent_sector_map.get(c_sector, 0.0) + c_mv
                )
                covered_weight += c["weight"]

            # 將已辨識板塊的 MV 加入總計
            for sector_name, s_mv in constituent_sector_map.items():
                sector_values[sector_name] = sector_values.get(sector_name, 0.0) + s_mv

            # 未覆蓋的剩餘比例（top-N 不足 100%）按已辨識板塊比例分配
            uncovered_weight = max(0.0, 1.0 - covered_weight)
            if uncovered_weight > 0 and constituent_sector_map:
                known_sectors_excl_unknown = {
                    s: v for s, v in constituent_sector_map.items() if s != "Unknown"
                }
                distribute_base = known_sectors_excl_unknown or constituent_sector_map
                base_total = sum(distribute_base.values())
                residual_mv = mv * uncovered_weight
                if base_total > 0:
                    for sector_name, s_mv in distribute_base.items():
                        allocated = residual_mv * (s_mv / base_total)
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
            sector_values["ETF"] = sector_values.get("ETF", 0.0) + mv
            logger.warning(
                "行業板塊：%s 為 ETF 但板塊權重與成分股皆無法取得，歸類為 ETF。",
                ticker,
            )
            continue

        # 直接持股：查詢該股票的板塊
        sector = get_ticker_sector(ticker) or "Unknown"
        sector_values[sector] = sector_values.get(sector, 0.0) + mv

    equity_total = sum(sector_values.values())
    result["sector_exposure"] = [
        {
            "sector": s,
            "value": round(v, 2),
            "weight_pct": round(v / total_value * 100, 2) if total_value > 0 else 0.0,
            "equity_pct": round(v / equity_total * 100, 2) if equity_total > 0 else 0.0,
        }
        for s, v in sorted(sector_values.items(), key=lambda x: x[1], reverse=True)
        if v > 0
    ]

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
            continue

        holding_market_data.append({"ticker": ticker, "market_value": agg["mv"]})
    result["geographic_allocation"] = compute_geographic_allocation(holding_market_data)

    # 12) 資產類別配置（Folio 分類 → 標準資產類別）
    result["asset_class_allocation"] = compute_asset_class_allocation(
        {
            cat: info.get("market_value", 0.0)
            for cat, info in result["categories"].items()
        }
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
    warnings: list[str] = []
    for entry in xray_entries:
        total_pct = entry.get("total_weight_pct", 0.0)
        indirect_val = entry.get("indirect_value", 0.0)
        if total_pct > XRAY_SINGLE_STOCK_WARN_PCT and indirect_val > 0:
            symbol = entry["symbol"]
            direct_pct = entry.get("direct_weight_pct", 0.0)
            sources = ", ".join(entry.get("indirect_sources", []))
            msg = t(
                "rebalance.xray_warning",
                lang=lang,
                symbol=symbol,
                direct_pct=direct_pct,
                sources=sources,
                total_pct=total_pct,
                threshold=XRAY_SINGLE_STOCK_WARN_PCT,
            )
            warnings.append(msg)

    if warnings:
        if is_notification_enabled(session, "xray_alerts"):
            full_msg = (
                t("rebalance.xray_header", lang=lang) + "\n\n" + "\n\n".join(warnings)
            )
            try:
                send_telegram_message_dual(full_msg, session)
                logger.info("已發送 X-Ray 警告（%d 筆）", len(warnings))
            except Exception as e:
                logger.warning("X-Ray Telegram 警告發送失敗：%s", e)
        else:
            logger.info("X-Ray 通知已被使用者停用，跳過發送。")

    return warnings


# ===========================================================================
# Currency Exposure Monitor
# ===========================================================================


def calculate_currency_exposure(
    session: Session, home_currency: str | None = None
) -> dict:
    """
    計算匯率曝險分析：
    1. 讀取使用者 Profile 的 home_currency（或使用參數覆寫）
    2. 將所有持倉按幣別分組，計算以本幣計價的市值
    3. 偵測近期匯率變動
    4. 產出風險等級與建議
    """
    # 1) 決定本幣
    if not home_currency:
        profile = session.exec(
            select(UserInvestmentProfile)
            .where(UserInvestmentProfile.user_id == DEFAULT_USER_ID)
            .where(UserInvestmentProfile.is_active == True)  # noqa: E712
        ).first()
        home_currency = profile.home_currency if profile else "TWD"

    # 2) 取得持倉（僅啟用帳戶）
    holdings = find_holdings_for_active_accounts(
        session,
        include_unlinked=False,
        user_id=DEFAULT_USER_ID,
    )

    if not holdings:
        return {
            "home_currency": home_currency,
            "total_value_home": 0.0,
            "breakdown": [],
            "non_home_pct": 0.0,
            "cash_breakdown": [],
            "cash_non_home_pct": 0.0,
            "total_cash_home": 0.0,
            "net_cash_impact": 0.0,
            "net_investment_impact": 0.0,
            "fx_movement_period": FX_HISTORY_PERIOD,
            "fx_movements": [],
            "risk_level": "low",
            "advice": [
                t("rebalance.no_holdings_data", lang=get_user_language(session))
            ],
            "calculated_at": datetime.now(UTC).isoformat(),
        }

    # 3) 取得匯率（all currencies → home_currency）
    holding_currencies = list({h.currency for h in holdings})
    fx_rates = get_exchange_rates(home_currency, holding_currencies)
    logger.info(
        "匯率曝險分析 → %s：%s",
        home_currency,
        {k: round(v, 4) for k, v in fx_rates.items()},
    )

    # 3.5) 並行預熱所有非現金持倉的技術訊號
    stock_tickers = list(
        {
            h.ticker
            for h in holdings
            if not h.is_cash and h.category != StockCategory.CRYPTO
        }
    )
    crypto_ids = list(
        {
            h.coingecko_id
            for h in holdings
            if (
                not h.is_cash
                and h.category == StockCategory.CRYPTO
                and getattr(h, "coingecko_id", None)
            )
        }
    )
    if stock_tickers:
        prewarm_signals_batch(stock_tickers)
    if crypto_ids:
        prewarm_crypto_prices(crypto_ids)

    # 4) 使用共用邏輯計算市值（以本幣計價），同時追蹤現金部位
    _nav_cache_ce = _build_nav_cache(session, holdings)
    currency_values, cash_currency_values, _ticker_agg, _account_ticker_agg = (
        _compute_holding_market_values(
            holdings,
            fx_rates,
            nav_cache=_nav_cache_ce,
        )
    )

    total_value_home = sum(currency_values.values())
    total_cash_home = sum(cash_currency_values.values())

    # 5) 建立幣別分佈（全資產）
    breakdown = []
    for cur, val in sorted(currency_values.items(), key=lambda x: x[1], reverse=True):
        pct = round((val / total_value_home) * 100, 2) if total_value_home > 0 else 0.0
        breakdown.append(
            {
                "currency": cur,
                "value": round(val, 2),
                "percentage": pct,
                "is_home": cur == home_currency,
            }
        )

    non_home_pct = round(
        sum(b["percentage"] for b in breakdown if not b["is_home"]),
        2,
    )

    # 5b) 建立現金幣別分佈
    cash_breakdown = []
    for cur, val in sorted(
        cash_currency_values.items(), key=lambda x: x[1], reverse=True
    ):
        pct = round((val / total_cash_home) * 100, 2) if total_cash_home > 0 else 0.0
        cash_breakdown.append(
            {
                "currency": cur,
                "value": round(val, 2),
                "percentage": pct,
                "is_home": cur == home_currency,
            }
        )

    cash_non_home_pct = round(
        sum(b["percentage"] for b in cash_breakdown if not b["is_home"]),
        2,
    )

    # 6) 偵測近期匯率變動（非本幣 → 本幣）
    fx_movements = []
    non_home_currencies = [cur for cur in currency_values if cur != home_currency]
    currency_histories: dict[str, list[dict]] = {}
    for cur in non_home_currencies:
        history = get_forex_history(cur, home_currency)
        currency_histories[cur] = history
        if len(history) >= 2:
            first_close = history[0]["close"]
            last_close = history[-1]["close"]
            if first_close > 0:
                change_pct = round(((last_close - first_close) / first_close) * 100, 2)
                direction = (
                    "up" if change_pct > 0 else ("down" if change_pct < 0 else "flat")
                )
                currency_value_home = currency_values.get(cur, 0.0)
                cash_value_home = cash_currency_values.get(cur, 0.0)
                investment_value_home = max(currency_value_home - cash_value_home, 0.0)
                impact_home_value = round(currency_value_home * (change_pct / 100.0), 2)
                impact_cash_home_value = round(
                    cash_value_home * (change_pct / 100.0), 2
                )
                impact_investment_home_value = round(
                    investment_value_home * (change_pct / 100.0),
                    2,
                )
                fx_movements.append(
                    {
                        "pair": f"{cur}/{home_currency}",
                        "current_rate": last_close,
                        "change_pct": change_pct,
                        "direction": direction,
                        "impact_home_value": impact_home_value,
                        "impact_cash_home_value": impact_cash_home_value,
                        "impact_investment_home_value": impact_investment_home_value,
                    }
                )

    # 6b) 三層匯率變動警報（單日 / 5日 / 3月）
    all_fx_alerts: list[FXRateAlert] = []
    for cur in non_home_currencies:
        short_hist = currency_histories.get(cur, [])
        long_hist = get_forex_history_long(cur, home_currency)
        current_rate = short_hist[-1]["close"] if short_hist else 0.0
        alerts_for_pair = analyze_fx_rate_changes(
            pair=f"{cur}/{home_currency}",
            current_rate=current_rate,
            short_history=short_hist,
            long_history=long_hist,
        )
        all_fx_alerts.extend(alerts_for_pair)

    # 7) 風險等級（基於匯率變動警報嚴重程度）
    risk_level = determine_fx_risk_level(all_fx_alerts)

    # 8) 序列化警報
    fx_rate_alerts_serialized = [
        {
            "pair": a.pair,
            "alert_type": a.alert_type.value,
            "change_pct": a.change_pct,
            "direction": a.direction,
            "current_rate": a.current_rate,
            "period_label": a.period_label,
        }
        for a in all_fx_alerts
    ]

    # 9) 建議（包含現金部位資訊）
    lang = get_user_language(session)
    advice = _generate_fx_advice(
        home_currency,
        breakdown,
        non_home_pct,
        risk_level,
        fx_movements,
        fx_rate_alerts=all_fx_alerts,
        cash_breakdown=cash_breakdown,
        cash_non_home_pct=cash_non_home_pct,
        total_cash_home=total_cash_home,
        lang=lang,
    )

    return {
        "home_currency": home_currency,
        "total_value_home": round(total_value_home, 2),
        "breakdown": breakdown,
        "non_home_pct": non_home_pct,
        "cash_breakdown": cash_breakdown,
        "cash_non_home_pct": cash_non_home_pct,
        "total_cash_home": round(total_cash_home, 2),
        "net_cash_impact": round(
            sum(m.get("impact_cash_home_value", 0.0) for m in fx_movements),
            2,
        ),
        "net_investment_impact": round(
            sum(m.get("impact_investment_home_value", 0.0) for m in fx_movements),
            2,
        ),
        "fx_movement_period": FX_HISTORY_PERIOD,
        "fx_movements": fx_movements,
        "fx_rate_alerts": fx_rate_alerts_serialized,
        "risk_level": risk_level,
        "advice": advice,
        "calculated_at": datetime.now(UTC).isoformat(),
    }


def _generate_fx_advice(
    home_currency: str,
    breakdown: list[dict],
    non_home_pct: float,
    risk_level: str,
    fx_movements: list[dict],
    *,
    fx_rate_alerts: list[FXRateAlert] | None = None,
    cash_breakdown: list[dict] | None = None,
    cash_non_home_pct: float = 0.0,
    total_cash_home: float = 0.0,
    lang: str = "zh-TW",
) -> list[str]:
    """根據匯率變動警報產出建議文字。"""
    advice: list[str] = []
    fx_rate_alerts = fx_rate_alerts or []

    # 匯率變動風險摘要
    if risk_level == "high":
        advice.append(t("rebalance.fx_risk_high", lang=lang))
    elif risk_level == "medium":
        advice.append(t("rebalance.fx_risk_medium", lang=lang))
    else:
        advice.append(t("rebalance.fx_risk_low", lang=lang))

    # 非本幣佔比資訊（保留但不作為警報觸發）
    if non_home_pct > 0:
        advice.append(
            t("rebalance.non_home_pct", lang=lang, home=home_currency, pct=non_home_pct)
        )

    # 現金部位專屬建議
    if cash_breakdown:
        foreign_cash = [b for b in cash_breakdown if not b["is_home"]]
        if foreign_cash and cash_non_home_pct > 0:
            top_cash_cur = foreign_cash[0]["currency"]
            top_cash_val = foreign_cash[0]["value"]
            advice.append(
                t(
                    "rebalance.foreign_cash_warning",
                    lang=lang,
                    pct=cash_non_home_pct,
                    currency=top_cash_cur,
                    value=top_cash_val,
                    home=home_currency,
                )
            )

    # 個別警報詳情
    cash_by_cur = {b["currency"]: b["value"] for b in (cash_breakdown or [])}
    for alert in fx_rate_alerts:
        base_cur = alert.pair.split("/")[0]
        cash_amt = cash_by_cur.get(base_cur, 0.0)
        cash_note = (
            t(
                "rebalance.cash_impact",
                lang=lang,
                currency=base_cur,
                amount=cash_amt,
                home=home_currency,
            )
            if cash_amt > 0
            else ""
        )
        type_label_key = FX_ALERT_LABEL.get(
            alert.alert_type.value, alert.alert_type.value
        )
        type_label = t(type_label_key, lang=lang)
        period = t(alert.period_label, lang=lang)
        if alert.direction == "up":
            advice.append(
                t(
                    "rebalance.fx_alert_up",
                    lang=lang,
                    pair=alert.pair,
                    type_label=type_label,
                    period=period,
                    change_pct=alert.change_pct,
                    rate=alert.current_rate,
                    cash_note=cash_note,
                )
            )
        else:
            advice.append(
                t(
                    "rebalance.fx_alert_down",
                    lang=lang,
                    pair=alert.pair,
                    type_label=type_label,
                    period=period,
                    change_pct=alert.change_pct,
                    rate=alert.current_rate,
                    cash_note=cash_note,
                )
            )

    return advice


# ===========================================================================
# FX Alerts
# ===========================================================================


def check_fx_alerts(session: Session, lang: str | None = None) -> list[str]:
    """
    檢查匯率曝險警報：偵測三層級匯率變動，產出 Telegram 通知文字。
    Alert text is localised to the user's preferred language.
    Pass `lang` explicitly to avoid a redundant DB read when the caller already holds it.
    """
    exposure = calculate_currency_exposure(session)
    alerts: list[str] = []
    if lang is None:
        lang = get_user_language(session)

    home_currency = exposure.get("home_currency", "TWD")
    cash_breakdown = exposure.get("cash_breakdown", [])
    cash_by_cur = {
        row.get("currency"): row.get("value", 0.0)
        for row in cash_breakdown
        if row.get("currency")
    }

    # 匯率變動警報（三層級偵測）
    for alert_data in exposure.get("fx_rate_alerts", []):
        pair = alert_data["pair"]
        base_currency = pair.split("/")[0]
        cash_amt = float(cash_by_cur.get(base_currency, 0.0) or 0.0)
        cash_note = (
            t(
                "rebalance.cash_impact",
                lang=lang,
                currency=base_currency,
                amount=cash_amt,
                home=home_currency,
            )
            if cash_amt > 0
            else ""
        )
        type_label_key = FX_ALERT_LABEL.get(
            alert_data["alert_type"], alert_data["alert_type"]
        )
        type_label = t(type_label_key, lang=lang)
        period = (
            t(alert_data["period_label"], lang=lang)
            if alert_data.get("period_label")
            else ""
        )
        key = (
            "rebalance.fx_alert_up"
            if alert_data["direction"] == "up"
            else "rebalance.fx_alert_down"
        )
        alerts.append(
            t(
                key,
                lang=lang,
                pair=pair,
                type_label=type_label,
                period=period,
                change_pct=alert_data["change_pct"],
                rate=alert_data["current_rate"],
                cash_note=cash_note,
            ).rstrip()
        )

    return alerts


def send_fx_alerts(session: Session) -> list[str]:
    """
    執行匯率曝險檢查，若有警報則發送 Telegram 通知。
    回傳已發送的警報列表。
    """
    lang = get_user_language(session)
    alerts = check_fx_alerts(session, lang=lang)

    if alerts:
        if not is_notification_enabled(session, "fx_alerts"):
            logger.info("匯率曝險通知已被使用者停用，跳過發送。")
        elif not is_within_rate_limit(session, "fx_alerts"):
            logger.info("匯率曝險通知已達頻率上限，跳過發送。")
        else:
            title = t("rebalance.fx_exposure_title", lang=lang)
            full_msg = title + "\n\n" + "\n\n".join(alerts)
            try:
                send_telegram_message_dual(full_msg, session)
            except Exception as e:
                logger.warning("匯率曝險 Telegram 警報發送失敗：%s", e)
            else:
                log_notification_sent(session, "fx_alerts")
                logger.info("已發送匯率曝險警報（%d 筆）", len(alerts))

    return alerts


# ===========================================================================
# Smart Withdrawal — 聰明提款機
# ===========================================================================


def calculate_withdrawal(
    session: Session,
    target_amount: float,
    display_currency: str = "USD",
    notify: bool = True,
) -> dict:
    """
    聰明提款：根據 Liquidity Waterfall 演算法產生賣出建議。
    1. 讀取投資組合目標配置與持倉
    2. 取得匯率與即時價格
    3. 計算再平衡偏移
    4. 委託 domain.withdrawal 純函式產生賣出計劃
    5. （可選）發送 Telegram 通知
    """
    from application.formatters import format_withdrawal_telegram
    from domain.withdrawal import HoldingData, plan_withdrawal

    logger.info("聰明提款計算：目標 %.2f %s", target_amount, display_currency)

    # 1) 取得目標配置
    profile = session.exec(
        select(UserInvestmentProfile)
        .where(UserInvestmentProfile.user_id == DEFAULT_USER_ID)
        .where(UserInvestmentProfile.is_active == True)  # noqa: E712
    ).first()

    if not profile:
        lang = get_user_language(session)
        raise StockNotFoundError(t("withdrawal.no_profile", lang=lang))

    target_config: dict[str, float] = _json.loads(profile.config)

    # 2) 取得持倉（僅啟用帳戶）
    holdings = find_holdings_for_active_accounts(
        session,
        include_unlinked=False,
        user_id=DEFAULT_USER_ID,
    )

    if not holdings:
        lang = get_user_language(session)
        return {
            "recommendations": [],
            "total_sell_value": 0.0,
            "target_amount": target_amount,
            "shortfall": target_amount,
            "post_sell_drifts": {},
            "message": t("withdrawal.no_holdings", lang=lang),
        }

    # 3) 取得匯率
    holding_currencies = list({h.currency for h in holdings})
    fx_rates = get_exchange_rates(display_currency, holding_currencies)

    # 4) 計算各持倉市值，建立 HoldingData 列表
    category_values: dict[str, float] = {}
    holdings_data: list[HoldingData] = []
    account_wrapper_map = {
        int(account.id): (account.tax_wrapper or "").strip().lower()
        for account in find_all_accounts(session, active_only=True)
        if account.id is not None
    }
    _nav_cache_wd = _build_nav_cache(session, holdings)

    for h in holdings:
        fx = fx_rates.get(h.currency, 1.0)
        price = _resolve_holding_price(h, _nav_cache_wd)

        if h.is_cash:
            market_value = h.quantity * fx
        elif price is not None:
            market_value = h.quantity * price * fx
        elif h.cost_basis is not None:
            market_value = h.quantity * h.cost_basis * fx
        else:
            market_value = 0.0

        cat = h.category.value if hasattr(h.category, "value") else str(h.category)
        category_values[cat] = category_values.get(cat, 0.0) + market_value

        holdings_data.append(
            HoldingData(
                ticker=h.ticker,
                category=cat,
                quantity=h.quantity,
                cost_basis=h.cost_basis,
                current_price=price,
                market_value=market_value,
                currency=h.currency,
                is_cash=h.is_cash,
                fx_rate=fx,
                tax_wrapper=account_wrapper_map.get(int(h.account_id))
                if h.account_id is not None
                else None,
            )
        )

    total_value = sum(category_values.values())

    # 5) 計算再平衡偏移
    rebalance_result = _pure_rebalance(category_values, target_config)
    category_drifts = {
        cat: info["drift_pct"]
        for cat, info in rebalance_result.get("categories", {}).items()
    }

    # 6) 執行 Liquidity Waterfall 演算法
    plan = plan_withdrawal(
        target_amount=target_amount,
        holdings_data=holdings_data,
        category_drifts=category_drifts,
        total_portfolio_value=total_value,
        target_config=target_config,
    )

    # 7) 建立回傳結果（翻譯 reason_key → 使用者語言的 reason 文字）
    lang = get_user_language(session)
    recs = [
        {
            "ticker": r.ticker,
            "category": r.category,
            "quantity_to_sell": r.quantity_to_sell,
            "sell_value": r.sell_value,
            "reason": t(r.reason_key, lang=lang, **r.reason_vars),
            "unrealized_pl": r.unrealized_pl,
            "priority": r.priority,
        }
        for r in plan.recommendations
    ]

    if plan.shortfall > 0:
        message = t(
            "withdrawal.shortfall",
            lang=lang,
            amount=f"{plan.shortfall:,.2f}",
            currency=display_currency,
        )
    elif not plan.recommendations:
        message = t("withdrawal.no_sellable", lang=lang)
    else:
        message = t("withdrawal.plan_generated", lang=lang, count=len(recs))

    result = {
        "recommendations": recs,
        "total_sell_value": plan.total_sell_value,
        "target_amount": plan.target_amount,
        "shortfall": plan.shortfall,
        "post_sell_drifts": plan.post_sell_drifts,
        "message": message,
    }

    # 8) 發送 Telegram 通知
    if notify and plan.recommendations:
        if is_notification_enabled(session, "withdrawal"):
            try:
                withdrawal_lang = get_user_language(session)
                tg_msg = format_withdrawal_telegram(
                    plan, display_currency, lang=withdrawal_lang
                )
                send_telegram_message_dual(tg_msg, session)
                logger.info("聰明提款建議已發送至 Telegram。")
            except Exception as e:
                logger.warning("聰明提款 Telegram 通知發送失敗：%s", e)
        else:
            logger.info("聰明提款通知已被使用者停用，跳過發送。")

    return result
