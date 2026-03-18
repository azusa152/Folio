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


def resolve_holding_price(
    h: object,
    nav_cache: dict[str, dict],
) -> float | None:
    """Resolve current market price for a holding based on its category.

    Returns the raw price (not FX-adjusted).  Returns None if the price is
    unavailable (caller should fall back to cost_basis).
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
