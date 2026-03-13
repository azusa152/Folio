"""
Import validation tests — stock import endpoint.
Tests Pydantic field validation and max payload size.
"""

from domain.constants import (
    DEFAULT_LANGUAGE,
    ERROR_INVALID_INPUT,
    GENERIC_VALIDATION_ERROR,
)
from i18n import t

# Valid categories: Trend_Setter, Moat, Growth, Bond, Cash
VALID_CATEGORY = "Growth"


def test_stock_import_empty_list(client):
    """Stock import with empty list succeeds (no-op)."""
    response = client.post("/stocks/import", json=[])
    assert response.status_code == 200


def test_stock_import_valid_payload(client):
    """Stock import with valid payload succeeds."""
    payload = [
        {
            "ticker": "AAPL",
            "category": VALID_CATEGORY,
            "thesis": "Strong ecosystem",
            "tags": ["tech", "growth"],
            "is_etf": False,
        }
    ]
    response = client.post("/stocks/import", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["imported"] == 1
    assert len(data["errors"]) == 0


def test_stock_import_ticker_uppercase_normalization(client):
    """Stock import normalizes ticker to uppercase."""
    payload = [
        {
            "ticker": "aapl",
            "category": VALID_CATEGORY,
            "thesis": "Test",
            "tags": [],
        }
    ]
    response = client.post("/stocks/import", json=payload)
    assert response.status_code == 200

    stocks_response = client.get("/stocks")
    stocks = stocks_response.json()
    assert any(s["ticker"] == "AAPL" for s in stocks)


def test_stock_import_missing_required_field(client):
    """Stock import rejects payload with missing required field."""
    payload = [{"category": VALID_CATEGORY, "thesis": "Test"}]
    response = client.post("/stocks/import", json=payload)
    assert response.status_code == 422


def test_stock_import_ticker_too_long(client):
    """Stock import rejects ticker exceeding 20 chars."""
    payload = [{"ticker": "A" * 21, "category": VALID_CATEGORY, "thesis": "Test"}]
    response = client.post("/stocks/import", json=payload)
    assert response.status_code == 422


def test_stock_import_thesis_too_long(client):
    """Stock import rejects thesis exceeding 5000 chars."""
    payload = [
        {
            "ticker": "AAPL",
            "category": VALID_CATEGORY,
            "thesis": "X" * 5001,
        }
    ]
    response = client.post("/stocks/import", json=payload)
    assert response.status_code == 422


def test_stock_import_oversized_list(client):
    """Stock import rejects payload with > 1000 items."""
    payload = [
        {"ticker": f"TICK{i}", "category": VALID_CATEGORY, "thesis": "Test"}
        for i in range(1001)
    ]
    response = client.post("/stocks/import", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["detail"]["error_code"] == ERROR_INVALID_INPUT
    assert data["detail"]["detail"] == t(
        GENERIC_VALIDATION_ERROR, lang=DEFAULT_LANGUAGE
    )


def test_stock_import_tags_validation(client):
    """Stock import validates tags list length."""
    payload = [
        {
            "ticker": "AAPL",
            "category": VALID_CATEGORY,
            "thesis": "Test",
            "tags": ["tag" + str(i) for i in range(21)],
        }
    ]
    response = client.post("/stocks/import", json=payload)
    assert response.status_code == 422
