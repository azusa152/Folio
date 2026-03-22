"""Application — Smart Withdrawal (聰明提款機).

Liquidity Waterfall algorithm: given a target cash amount, produce an
ordered sell recommendation list that maximises tax efficiency and minimises
disruption to the target allocation.
"""

import json as _json

from sqlmodel import Session, select

from application.portfolio.pricing_service import (
    build_nav_cache as _build_nav_cache,
)
from application.portfolio.pricing_service import (
    resolve_holding_price as _resolve_holding_price,
)
from application.stock.stock_service import StockNotFoundError
from domain.constants import DEFAULT_USER_ID
from domain.entities import UserInvestmentProfile
from domain.rebalance import calculate_rebalance as _pure_rebalance
from i18n import get_user_language, t
from infrastructure.market_data import get_exchange_rates, get_ticker_name_cached
from infrastructure.notification import (
    is_notification_enabled,
    send_telegram_message_dual,
)
from infrastructure.repositories import (
    find_all_accounts,
    find_holdings_for_active_accounts,
)
from logging_config import get_logger

logger = get_logger(__name__)


def _build_withdrawal_input(
    session: Session,
    display_currency: str,
) -> tuple[dict[str, float], list, dict[str, float], float]:
    """Load holdings, price them in *display_currency*, and compute drifts.

    Returns (target_config, holdings_data, category_drifts, total_value).
    Raises StockNotFoundError when no active profile exists.
    Returns (target_config, [], {}, 0.0) when no holdings are found.
    """
    from domain.withdrawal import HoldingData

    profile = session.exec(
        select(UserInvestmentProfile)
        .where(UserInvestmentProfile.user_id == DEFAULT_USER_ID)
        .where(UserInvestmentProfile.is_active == True)  # noqa: E712
    ).first()
    if not profile:
        raise StockNotFoundError(
            t("withdrawal.no_profile", lang=get_user_language(session))
        )

    target_config: dict[str, float] = _json.loads(profile.config)

    holdings = find_holdings_for_active_accounts(
        session, include_unlinked=False, user_id=DEFAULT_USER_ID
    )
    if not holdings:
        return target_config, [], {}, 0.0

    holding_currencies = list({h.currency for h in holdings})
    fx_rates = get_exchange_rates(display_currency, holding_currencies)
    account_wrapper_map = {
        int(account.id): (account.tax_wrapper or "").strip().lower()
        for account in find_all_accounts(session, active_only=True)
        if account.id is not None
    }
    nav_cache = _build_nav_cache(session, holdings)

    category_values: dict[str, float] = {}
    holdings_data: list[HoldingData] = []
    for holding in holdings:
        fx = fx_rates.get(holding.currency, 1.0)
        price = _resolve_holding_price(holding, nav_cache)
        if holding.is_cash:
            market_value = holding.quantity * fx
        elif price is not None:
            market_value = holding.quantity * price * fx
        elif holding.cost_basis is not None:
            market_value = holding.quantity * holding.cost_basis * fx
        else:
            market_value = 0.0
        cat = (
            holding.category.value
            if hasattr(holding.category, "value")
            else str(holding.category)
        )
        category_values[cat] = category_values.get(cat, 0.0) + market_value
        holdings_data.append(
            HoldingData(
                ticker=holding.ticker,
                category=cat,
                quantity=holding.quantity,
                cost_basis=holding.cost_basis,
                current_price=price,
                market_value=market_value,
                currency=holding.currency,
                is_cash=holding.is_cash,
                fx_rate=fx,
                tax_wrapper=account_wrapper_map.get(int(holding.account_id))
                if holding.account_id is not None
                else None,
            )
        )

    total_value = sum(category_values.values())
    rebalance_result = _pure_rebalance(category_values, target_config)
    category_drifts = {
        cat: info["drift_pct"]
        for cat, info in rebalance_result.get("categories", {}).items()
    }
    return target_config, holdings_data, category_drifts, total_value


def calculate_withdrawal(
    session: Session,
    target_amount: float,
    display_currency: str = "USD",
    notify: bool = True,
) -> dict:
    """
    聰明提款：根據 Liquidity Waterfall 演算法產生賣出建議。
    1. 讀取投資組合目標配置與持倉，計算再平衡偏移
    2. 委託 domain.withdrawal 純函式產生賣出計劃
    3. （可選）發送 Telegram 通知
    """
    from application.formatters import format_withdrawal_telegram
    from domain.withdrawal import plan_withdrawal

    logger.info("聰明提款計算：目標 %.2f %s", target_amount, display_currency)

    target_config, holdings_data, category_drifts, total_value = (
        _build_withdrawal_input(session, display_currency)
    )

    if not holdings_data:
        lang = get_user_language(session)
        return {
            "recommendations": [],
            "total_sell_value": 0.0,
            "target_amount": target_amount,
            "shortfall": target_amount,
            "post_sell_drifts": {},
            "message": t("withdrawal.no_holdings", lang=lang),
        }

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
            "name": get_ticker_name_cached(r.ticker),
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
                rec_names = {r["ticker"]: r["name"] for r in recs if r.get("name")}
                tg_msg = format_withdrawal_telegram(
                    plan, display_currency, lang=withdrawal_lang, rec_names=rec_names
                )
                send_telegram_message_dual(tg_msg, session)
                logger.info("聰明提款建議已發送至 Telegram。")
            except Exception as e:
                logger.warning("聰明提款 Telegram 通知發送失敗：%s", e)
        else:
            logger.info("聰明提款通知已被使用者停用，跳過發送。")

    return result
