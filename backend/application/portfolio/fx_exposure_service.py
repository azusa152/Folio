"""Application — Currency Exposure Monitor + FX Alerts.

Analyses foreign-currency exposure across the portfolio, computes risk level,
generates advice, and optionally sends Telegram alerts.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

from sqlmodel import Session, select

from application.portfolio.pricing_service import (
    build_nav_cache as _build_nav_cache,
)
from domain.constants import (
    DEFAULT_USER_ID,
    FX_HISTORY_PERIOD,
    SKIP_PRICE_FETCH_CATEGORIES,
)
from domain.entities import Holding, UserInvestmentProfile
from domain.enums import FX_ALERT_LABEL, StockCategory
from domain.fx_analysis import (
    FXRateAlert,
    analyze_fx_rate_changes,
    determine_fx_risk_level,
)
from i18n import get_user_language, t
from infrastructure.market_data import (
    get_exchange_rates,
    get_forex_history,
    get_forex_history_long,
    prewarm_crypto_prices,
    prewarm_signals_batch,
)
from infrastructure.notification import (
    is_notification_enabled,
    is_within_rate_limit,
    send_telegram_message_dual,
)
from infrastructure.repositories import (
    find_holdings_for_active_accounts,
    log_notification_sent,
)
from logging_config import get_logger

logger = get_logger(__name__)


def _resolve_home_currency(session: Session, home_currency: str | None) -> str:
    """Return home_currency from arg, or load the active profile, defaulting to TWD."""
    if home_currency:
        return home_currency
    profile = session.exec(
        select(UserInvestmentProfile)
        .where(UserInvestmentProfile.user_id == DEFAULT_USER_ID)
        .where(UserInvestmentProfile.is_active == True)  # noqa: E712
    ).first()
    return profile.home_currency if profile else "TWD"


def _load_and_value_holdings_for_fx(
    session: Session, home_currency: str
) -> tuple[
    list[Holding], dict[str, float], dict[str, float], dict[str, float], float, float
]:
    """Load active holdings, fetch FX rates, warm caches, compute home-currency values.

    Returns (holdings, fx_rates, currency_values, cash_currency_values,
             total_value_home, total_cash_home).
    Returns an empty holdings list if no holdings exist.
    """
    from application.portfolio.rebalance_service import _compute_holding_market_values

    holdings = find_holdings_for_active_accounts(
        session, include_unlinked=False, user_id=DEFAULT_USER_ID
    )
    if not holdings:
        return holdings, {}, {}, {}, 0.0, 0.0

    holding_currencies = list({h.currency for h in holdings})
    fx_rates = get_exchange_rates(home_currency, holding_currencies)
    logger.info(
        "匯率曝險分析 → %s：%s",
        home_currency,
        {k: round(v, 4) for k, v in fx_rates.items()},
    )

    stock_tickers = list(
        {
            h.ticker
            for h in holdings
            if not h.is_cash
            and h.category != StockCategory.CRYPTO
            and h.category.value not in SKIP_PRICE_FETCH_CATEGORIES
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

    nav_cache = _build_nav_cache(session, holdings)
    currency_values, cash_currency_values, _ticker_agg, _account_ticker_agg = (
        _compute_holding_market_values(holdings, fx_rates, nav_cache=nav_cache)
    )
    return (
        holdings,
        fx_rates,
        currency_values,
        cash_currency_values,
        sum(currency_values.values()),
        sum(cash_currency_values.values()),
    )


def _build_currency_breakdown(
    currency_values: dict[str, float],
    cash_currency_values: dict[str, float],
    home_currency: str,
    total_value_home: float,
    total_cash_home: float,
) -> tuple[list[dict], float, list[dict], float]:
    """Compute per-currency percentage breakdowns for total and cash positions.

    Returns (breakdown, non_home_pct, cash_breakdown, cash_non_home_pct).
    """
    breakdown = [
        {
            "currency": cur,
            "value": round(val, 2),
            "percentage": round((val / total_value_home) * 100, 2)
            if total_value_home > 0
            else 0.0,
            "is_home": cur == home_currency,
        }
        for cur, val in sorted(
            currency_values.items(), key=lambda x: x[1], reverse=True
        )
    ]
    non_home_pct = round(sum(b["percentage"] for b in breakdown if not b["is_home"]), 2)

    cash_breakdown = [
        {
            "currency": cur,
            "value": round(val, 2),
            "percentage": round((val / total_cash_home) * 100, 2)
            if total_cash_home > 0
            else 0.0,
            "is_home": cur == home_currency,
        }
        for cur, val in sorted(
            cash_currency_values.items(), key=lambda x: x[1], reverse=True
        )
    ]
    cash_non_home_pct = round(
        sum(b["percentage"] for b in cash_breakdown if not b["is_home"]), 2
    )
    return breakdown, non_home_pct, cash_breakdown, cash_non_home_pct


def _analyze_fx_movements(
    currency_values: dict[str, float],
    cash_currency_values: dict[str, float],
    home_currency: str,
) -> tuple[list[dict], list[FXRateAlert], list[dict], Literal["low", "medium", "high"]]:
    """Detect recent FX movements, run multi-period alert analysis, determine risk level.

    Returns (fx_movements, all_fx_alerts, fx_rate_alerts_serialized, risk_level).
    """
    non_home_currencies = [cur for cur in currency_values if cur != home_currency]
    fx_movements: list[dict] = []
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
                fx_movements.append(
                    {
                        "pair": f"{cur}/{home_currency}",
                        "current_rate": last_close,
                        "change_pct": change_pct,
                        "direction": direction,
                        "impact_home_value": round(
                            currency_value_home * (change_pct / 100.0), 2
                        ),
                        "impact_cash_home_value": round(
                            cash_value_home * (change_pct / 100.0), 2
                        ),
                        "impact_investment_home_value": round(
                            investment_value_home * (change_pct / 100.0), 2
                        ),
                    }
                )

    all_fx_alerts: list[FXRateAlert] = []
    for cur in non_home_currencies:
        short_hist = currency_histories.get(cur, [])
        long_hist = get_forex_history_long(cur, home_currency)
        current_rate = short_hist[-1]["close"] if short_hist else 0.0
        all_fx_alerts.extend(
            analyze_fx_rate_changes(
                pair=f"{cur}/{home_currency}",
                current_rate=current_rate,
                short_history=short_hist,
                long_history=long_hist,
            )
        )

    risk_level = determine_fx_risk_level(all_fx_alerts)
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
    return fx_movements, all_fx_alerts, fx_rate_alerts_serialized, risk_level


@dataclass
class FXAdviceContext:
    """Parameters for the FX advice generator — replaces a 10-argument call signature."""

    home_currency: str
    non_home_pct: float
    risk_level: str
    fx_rate_alerts: list[FXRateAlert] = field(default_factory=list)
    cash_breakdown: list[dict] = field(default_factory=list)
    cash_non_home_pct: float = 0.0
    lang: str = "zh-TW"


def _generate_fx_advice(ctx: FXAdviceContext) -> list[str]:
    """根據匯率變動警報產出建議文字。"""
    advice: list[str] = []

    if ctx.risk_level == "high":
        advice.append(t("rebalance.fx_risk_high", lang=ctx.lang))
    elif ctx.risk_level == "medium":
        advice.append(t("rebalance.fx_risk_medium", lang=ctx.lang))
    else:
        advice.append(t("rebalance.fx_risk_low", lang=ctx.lang))

    if ctx.non_home_pct > 0:
        advice.append(
            t(
                "rebalance.non_home_pct",
                lang=ctx.lang,
                home=ctx.home_currency,
                pct=ctx.non_home_pct,
            )
        )

    if ctx.cash_breakdown:
        foreign_cash = [b for b in ctx.cash_breakdown if not b["is_home"]]
        if foreign_cash and ctx.cash_non_home_pct > 0:
            top_cash_cur = foreign_cash[0]["currency"]
            top_cash_val = foreign_cash[0]["value"]
            advice.append(
                t(
                    "rebalance.foreign_cash_warning",
                    lang=ctx.lang,
                    pct=ctx.cash_non_home_pct,
                    currency=top_cash_cur,
                    value=top_cash_val,
                    home=ctx.home_currency,
                )
            )

    cash_by_cur = {b["currency"]: b["value"] for b in ctx.cash_breakdown}
    for alert in ctx.fx_rate_alerts:
        base_cur = alert.pair.split("/")[0]
        cash_amt = cash_by_cur.get(base_cur, 0.0)
        cash_note = (
            t(
                "rebalance.cash_impact",
                lang=ctx.lang,
                currency=base_cur,
                amount=cash_amt,
                home=ctx.home_currency,
            )
            if cash_amt > 0
            else ""
        )
        type_label_key = FX_ALERT_LABEL.get(
            alert.alert_type.value, alert.alert_type.value
        )
        type_label = t(type_label_key, lang=ctx.lang)
        period = t(alert.period_label, lang=ctx.lang)
        alert_key = (
            "rebalance.fx_alert_up"
            if alert.direction == "up"
            else "rebalance.fx_alert_down"
        )
        advice.append(
            t(
                alert_key,
                lang=ctx.lang,
                pair=alert.pair,
                type_label=type_label,
                period=period,
                change_pct=alert.change_pct,
                rate=alert.current_rate,
                cash_note=cash_note,
            )
        )

    return advice


def calculate_currency_exposure(
    session: Session, home_currency: str | None = None
) -> dict:
    """計算匯率曝險分析 (orchestrator).

    1. 決定本幣（profile 或預設 TWD）
    2. 載入持倉並計算以本幣計價的市值
    3. 建立幣別分佈與百分比
    4. 偵測近期匯率變動並評估風險等級
    5. 產出建議文字
    """
    home_currency = _resolve_home_currency(session, home_currency)
    (
        holdings,
        _fx_rates,
        currency_values,
        cash_currency_values,
        total_value_home,
        total_cash_home,
    ) = _load_and_value_holdings_for_fx(session, home_currency)

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

    breakdown, non_home_pct, cash_breakdown, cash_non_home_pct = (
        _build_currency_breakdown(
            currency_values,
            cash_currency_values,
            home_currency,
            total_value_home,
            total_cash_home,
        )
    )
    fx_movements, all_fx_alerts, fx_rate_alerts_serialized, risk_level = (
        _analyze_fx_movements(currency_values, cash_currency_values, home_currency)
    )
    lang = get_user_language(session)
    advice = _generate_fx_advice(
        FXAdviceContext(
            home_currency=home_currency,
            non_home_pct=non_home_pct,
            risk_level=risk_level,
            fx_rate_alerts=all_fx_alerts,
            cash_breakdown=cash_breakdown,
            cash_non_home_pct=cash_non_home_pct,
            lang=lang,
        )
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
            sum(m.get("impact_cash_home_value", 0.0) for m in fx_movements), 2
        ),
        "net_investment_impact": round(
            sum(m.get("impact_investment_home_value", 0.0) for m in fx_movements), 2
        ),
        "fx_movement_period": FX_HISTORY_PERIOD,
        "fx_movements": fx_movements,
        "fx_rate_alerts": fx_rate_alerts_serialized,
        "risk_level": risk_level,
        "advice": advice,
        "calculated_at": datetime.now(UTC).isoformat(),
    }


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
