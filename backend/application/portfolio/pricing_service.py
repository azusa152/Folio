"""
Application — Pricing Service。
共用的市場價格解析工具，供 rebalance_service、holding_service 等多處呼叫。
抽出以避免跨服務直接依賴私有實作細節。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlmodel import Session

from domain.constants import SKIP_PRICE_FETCH_CATEGORIES
from domain.enums import StockCategory
from infrastructure.market_data import get_crypto_price, get_technical_signals
from infrastructure.repositories import get_latest_nav


def build_nav_cache(session: Session, holdings: list) -> dict[str, dict]:
    """Pre-fetch latest NAV for all Mutual_Fund holdings.

    Returns a mapping of ticker → {nav, nav_previous}.
    """
    cache: dict[str, dict] = {}
    for holding in holdings:
        cat = (
            holding.category.value
            if hasattr(holding.category, "value")
            else str(holding.category)
        )
        if cat != StockCategory.MUTUAL_FUND.value or holding.ticker in cache:
            continue
        nav_row = get_latest_nav(session, holding.ticker)
        if nav_row:
            cache[holding.ticker] = {
                "nav": nav_row.nav,
                "nav_previous": nav_row.nav_previous,
            }
    return cache


def resolve_holding_price(
    holding: object,
    nav_cache: dict[str, dict],
) -> float | None:
    """Resolve current market price for a holding based on its category.

    Returns the raw price (not FX-adjusted).  Returns None if the price is
    unavailable (caller should fall back to cost_basis).
    """
    price, _, _ = resolve_holding_price_with_prev(holding, nav_cache)
    return price


def resolve_holding_price_with_prev(
    holding: object,
    nav_cache: dict[str, dict],
) -> tuple[float | None, float | None, bool]:
    """Resolve current and previous-close price for a holding.

    Returns (price, previous_close, has_prev_close):
    - price:           raw current price (not FX-adjusted); None → use cost_basis
    - previous_close:  prior-day price; None when unavailable
    - has_prev_close:  True when a reliable prev baseline exists (including cost-basis cases)
    """
    cat = (
        holding.category.value
        if hasattr(holding.category, "value")
        else str(holding.category)
    )  # type: ignore[attr-defined]

    if holding.is_cash:  # type: ignore[attr-defined]
        return 1.0, None, True

    if holding.category == StockCategory.CRYPTO:  # type: ignore[attr-defined]
        crypto_data = get_crypto_price(
            getattr(holding, "coingecko_id", None),
            holding.ticker,  # type: ignore[attr-defined]
        )
        price = crypto_data.get("price_usd") if crypto_data else None
        change_24h_pct = crypto_data.get("change_24h_pct") if crypto_data else None
        price_f: float | None = (
            float(price) if isinstance(price, (int, float)) else None
        )
        previous_close: float | None = None
        if (
            price_f is not None
            and isinstance(change_24h_pct, (int, float))
            and (1 + change_24h_pct / 100) != 0
        ):
            previous_close = price_f / (1 + change_24h_pct / 100)
        return price_f, previous_close, previous_close is not None

    if cat == StockCategory.MUTUAL_FUND.value:
        nav_data = nav_cache.get(holding.ticker)  # type: ignore[attr-defined]
        nav = nav_data.get("nav") if nav_data else None
        nav_prev = nav_data.get("nav_previous") if nav_data else None
        nav_f: float | None = float(nav) if isinstance(nav, (int, float)) else None
        nav_prev_f: float | None = (
            float(nav_prev) if isinstance(nav_prev, (int, float)) else None
        )
        return nav_f, nav_prev_f, nav_prev_f is not None

    if cat in SKIP_PRICE_FETCH_CATEGORIES:
        # No live price; caller uses cost_basis for both current and previous MV.
        return None, None, True

    signals = get_technical_signals(holding.ticker)  # type: ignore[attr-defined]
    price_s = signals.get("price") if signals else None
    prev_s = signals.get("previous_close") if signals else None
    price_sf: float | None = (
        float(price_s) if isinstance(price_s, (int, float)) else None
    )
    prev_sf: float | None = float(prev_s) if isinstance(prev_s, (int, float)) else None
    return price_sf, prev_sf, prev_sf is not None
