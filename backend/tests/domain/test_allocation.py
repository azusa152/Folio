"""Unit tests for geographic and asset class allocation helpers."""

from domain.portfolio.allocation import (
    classify_market,
    compute_asset_class_allocation,
    compute_geographic_allocation,
)

# ---------------------------------------------------------------------------
# classify_market
# ---------------------------------------------------------------------------


def test_classify_market_us_no_suffix():
    assert classify_market("AAPL") == "US"
    assert classify_market("MSFT") == "US"
    assert classify_market("BRK-B") == "US"


def test_classify_market_tw():
    assert classify_market("2330.TW") == "TW"
    assert classify_market("2330.tw") == "TW"


def test_classify_market_two():
    assert classify_market("6505.TWO") == "TW"


def test_classify_market_jp():
    assert classify_market("7203.T") == "JP"


def test_classify_market_hk():
    assert classify_market("0700.HK") == "HK"


def test_classify_market_empty_string():
    assert classify_market("") == "US"


# ---------------------------------------------------------------------------
# compute_geographic_allocation
# ---------------------------------------------------------------------------


def test_geographic_allocation_mixed_markets():
    holdings = [
        {"ticker": "AAPL", "market_value": 10000},
        {"ticker": "2330.TW", "market_value": 5000},
        {"ticker": "7203.T", "market_value": 3000},
        {"ticker": "0700.HK", "market_value": 2000},
    ]
    result = compute_geographic_allocation(holdings)
    assert result["US"] == 10000
    assert result["TW"] == 5000
    assert result["JP"] == 3000
    assert result["HK"] == 2000


def test_geographic_allocation_aggregates_same_market():
    holdings = [
        {"ticker": "AAPL", "market_value": 10000},
        {"ticker": "MSFT", "market_value": 8000},
    ]
    result = compute_geographic_allocation(holdings)
    assert result["US"] == 18000
    assert len(result) == 1


def test_geographic_allocation_empty_list():
    result = compute_geographic_allocation([])
    assert result == {}


def test_geographic_allocation_missing_keys():
    holdings = [{"other_key": "value"}]
    result = compute_geographic_allocation(holdings)
    assert result["US"] == 0.0


# ---------------------------------------------------------------------------
# compute_asset_class_allocation
# ---------------------------------------------------------------------------


def test_asset_class_allocation_all_categories():
    cat_values = {
        "Trend_Setter": 30000,
        "Moat": 10000,
        "Growth": 5000,
        "Bond": 10000,
        "Cash": 5000,
        "Crypto": 2000,
    }
    result = compute_asset_class_allocation(cat_values)
    assert result["Equity"] == 45000
    assert result["Fixed Income"] == 10000
    assert result["Cash"] == 5000
    assert result["Alternatives"] == 2000


def test_asset_class_allocation_unknown_category():
    cat_values = {"NewCategory": 1000}
    result = compute_asset_class_allocation(cat_values)
    assert result["Other"] == 1000


def test_asset_class_allocation_empty():
    result = compute_asset_class_allocation({})
    assert result == {}
