"""Geographic and asset-class allocation helpers (pure functions).

These are domain-layer computations with no external dependencies.
Used by the rebalance service and snapshot service to derive allocation
breakdowns from holding data.
"""

from domain.core.constants import (
    CURRENCY_REGION_MAP,
    DEFAULT_MARKET,
    TICKER_MARKET_MAP,
)
from domain.core.enums import StockCategory


def classify_market(ticker: str) -> str:
    """Derive geographic market from ticker suffix."""
    upper = ticker.upper()
    for suffix, market in TICKER_MARKET_MAP.items():
        if upper.endswith(suffix.upper()):
            return market
    return DEFAULT_MARKET


def classify_cash_region(currency: str) -> str:
    """Map a cash currency to its geographic region."""
    return CURRENCY_REGION_MAP.get(currency.upper(), DEFAULT_MARKET)


def compute_geographic_allocation(
    holdings: list[dict],
) -> dict[str, float]:
    """Compute market value by geographic region.

    Args:
        holdings: list of dicts with ``ticker`` or ``region``, and ``market_value`` keys.

    Returns:
        e.g. ``{"US": 50000.0, "TW": 20000.0, "JP": 10000.0}``
    """
    geo: dict[str, float] = {}
    for h in holdings:
        market = h.get("region") or classify_market(h.get("ticker", ""))
        value = h.get("market_value") or 0.0
        geo[market] = geo.get(market, 0.0) + value
    return geo


CATEGORY_ASSET_CLASS: dict[str, str] = {
    StockCategory.TREND_SETTER: "Equity",
    StockCategory.MOAT: "Equity",
    StockCategory.GROWTH: "Equity",
    StockCategory.MUTUAL_FUND: "Equity",
    StockCategory.ETF: "Equity",
    StockCategory.BOND: "Fixed Income",
    StockCategory.CASH: "Cash",
    StockCategory.CRYPTO: "Alternatives",
}


def compute_asset_class_allocation(
    category_values: dict[str, float],
) -> dict[str, float]:
    """Map Folio categories to standard asset classes.

    Returns:
        e.g. ``{"Equity": 70000, "Fixed Income": 15000, "Cash": 10000, "Alternatives": 5000}``
    """
    result: dict[str, float] = {}
    for cat, value in category_values.items():
        asset_class = CATEGORY_ASSET_CLASS.get(cat, "Other")
        result[asset_class] = result.get(asset_class, 0.0) + value
    return result
