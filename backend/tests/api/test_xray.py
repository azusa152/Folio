"""Tests for X-Ray analysis in the rebalance endpoint.

Covers coverage-percentage calculation, skipped-ETF reporting, and the
response-shape contract.
"""

from unittest.mock import patch

from fastapi.testclient import TestClient

_PROFILE_PAYLOAD = {"config": {"Growth": 100}, "home_currency": "USD"}

_ETF_HOLDING = {
    "ticker": "VTI",
    "category": "Growth",
    "quantity": 100,
    "cost_basis": 200.0,
    "broker": "Firstrade",
    "currency": "USD",
    "account_type": "US",
    "is_cash": False,
}

_STOCK_HOLDING = {
    "ticker": "AAPL",
    "category": "Growth",
    "quantity": 50,
    "cost_basis": 150.0,
    "broker": "Firstrade",
    "currency": "USD",
    "account_type": "US",
    "is_cash": False,
}


def _setup_portfolio(client: TestClient, holdings: list[dict] | None = None):
    """Create holdings and an investment profile."""
    account_resp = client.post(
        "/accounts",
        json={
            "name": "Default",
            "broker": "Default",
            "account_type": "brokerage",
            "currency": "USD",
        },
    )
    assert account_resp.status_code == 201
    account_id = account_resp.json()["id"]

    for h in holdings or [_STOCK_HOLDING]:
        resp = client.post("/holdings", json={**h, "account_id": account_id})
        assert resp.status_code == 200
    resp = client.post("/profiles", json=_PROFILE_PAYLOAD)
    assert resp.status_code in (200, 201)


def _mark_etf(client: TestClient, ticker: str):
    """Add a stock to the watchlist flagged as ETF so rebalance recognises it."""
    resp = client.post(
        "/ticker",
        json={"ticker": ticker, "category": "Growth", "thesis": "ETF", "is_etf": True},
    )
    assert resp.status_code in (200, 201, 409)


class TestXRayCoverageMath:
    """Verify xray_coverage_pct reflects available ETF decomposition data."""

    def test_sector_weights_should_enable_full_coverage_even_if_top_holdings_partial(
        self, client
    ):
        """If ETF sector weights are available, coverage counts full ETF value."""
        _setup_portfolio(client, [_ETF_HOLDING])
        _mark_etf(client, "VTI")

        partial_constituents = [
            {"symbol": "AAPL", "name": "Apple Inc.", "weight": 0.30},
            {"symbol": "MSFT", "name": "Microsoft Corp.", "weight": 0.20},
            {"symbol": "GOOGL", "name": "Alphabet Inc.", "weight": 0.10},
        ]

        with (
            patch(
                "application.portfolio.rebalance_service.get_etf_top_holdings",
                return_value=partial_constituents,
            ),
            patch(
                "application.portfolio.rebalance_service.get_etf_sector_weights",
                return_value={"technology": 0.4, "financial_services": 0.6},
            ),
        ):
            resp = client.get("/rebalance")

        assert resp.status_code == 200
        data = resp.json()
        assert data["xray_coverage_pct"] >= 99.0

    def test_partial_constituents_without_sector_weights_should_remain_partial(
        self, client
    ):
        """Without sector weights, coverage falls back to constituent weight sum."""
        _setup_portfolio(client, [_ETF_HOLDING])
        _mark_etf(client, "VTI")

        partial_constituents = [
            {"symbol": "AAPL", "name": "Apple Inc.", "weight": 0.30},
            {"symbol": "MSFT", "name": "Microsoft Corp.", "weight": 0.20},
            {"symbol": "GOOGL", "name": "Alphabet Inc.", "weight": 0.10},
        ]

        with (
            patch(
                "application.portfolio.rebalance_service.get_etf_top_holdings",
                return_value=partial_constituents,
            ),
            patch(
                "application.portfolio.rebalance_service.get_etf_sector_weights",
                return_value=None,
            ),
        ):
            resp = client.get("/rebalance")

        assert resp.status_code == 200
        data = resp.json()
        coverage = data["xray_coverage_pct"]
        assert 55 <= coverage <= 65, (
            f"Expected ~60% coverage for 60% constituent weight sum, got {coverage}%"
        )

    def test_full_constituents_should_produce_100_coverage(self, client):
        """ETF whose constituents sum to >=1.0 → coverage is 100%."""
        _setup_portfolio(client, [_ETF_HOLDING])
        _mark_etf(client, "VTI")

        full_constituents = [
            {"symbol": "AAPL", "name": "Apple Inc.", "weight": 0.50},
            {"symbol": "MSFT", "name": "Microsoft Corp.", "weight": 0.30},
            {"symbol": "GOOGL", "name": "Alphabet Inc.", "weight": 0.25},
        ]

        with patch(
            "application.portfolio.rebalance_service.get_etf_top_holdings",
            return_value=full_constituents,
        ):
            resp = client.get("/rebalance")

        assert resp.status_code == 200
        data = resp.json()
        assert data["xray_coverage_pct"] >= 99.0

    def test_direct_stock_should_count_as_fully_covered(self, client):
        """Non-ETF stock → full market value counts toward coverage."""
        _setup_portfolio(client, [_STOCK_HOLDING])

        resp = client.get("/rebalance")

        assert resp.status_code == 200
        data = resp.json()
        assert data["xray_coverage_pct"] >= 99.0


class TestXRaySkippedEtfs:
    """Verify skipped ETFs are reported when constituents are unavailable."""

    def test_known_etf_without_constituents_should_appear_in_skipped(self, client):
        _setup_portfolio(client, [_ETF_HOLDING, _STOCK_HOLDING])
        _mark_etf(client, "VTI")

        resp = client.get("/rebalance")

        assert resp.status_code == 200
        data = resp.json()
        skipped = data["xray_skipped_etfs"]
        skipped_tickers = [e["ticker"] for e in skipped]
        assert "VTI" in skipped_tickers
        vti_entry = next(e for e in skipped if e["ticker"] == "VTI")
        assert vti_entry["weight_pct"] > 0

    def test_known_etf_without_constituents_but_with_sector_weights_not_skipped(
        self, client
    ):
        _setup_portfolio(client, [_ETF_HOLDING, _STOCK_HOLDING])
        _mark_etf(client, "VTI")

        with (
            patch(
                "application.portfolio.rebalance_service.get_etf_top_holdings",
                return_value=None,
            ),
            patch(
                "application.portfolio.rebalance_service.get_etf_sector_weights",
                return_value={"technology": 1.0},
            ),
        ):
            resp = client.get("/rebalance")

        assert resp.status_code == 200
        data = resp.json()
        skipped_tickers = [e["ticker"] for e in data["xray_skipped_etfs"]]
        assert "VTI" not in skipped_tickers

    def test_non_etf_stock_should_not_appear_in_skipped(self, client):
        _setup_portfolio(client, [_STOCK_HOLDING])

        resp = client.get("/rebalance")

        assert resp.status_code == 200
        data = resp.json()
        assert data["xray_skipped_etfs"] == []


class TestXRayResponseContract:
    """Verify the rebalance response always includes X-Ray fields."""

    def test_response_should_include_xray_fields(self, client):
        _setup_portfolio(client, [_STOCK_HOLDING])

        resp = client.get("/rebalance")

        assert resp.status_code == 200
        data = resp.json()
        assert "xray" in data
        assert "xray_coverage_pct" in data
        assert "xray_skipped_etfs" in data
        assert isinstance(data["xray"], list)
        assert isinstance(data["xray_coverage_pct"], (int, float))
        assert isinstance(data["xray_skipped_etfs"], list)

    def test_rebalance_should_return_404_when_no_holdings(self, client):
        """Rebalance requires holdings; empty portfolio returns 404."""
        client.post("/profiles", json=_PROFILE_PAYLOAD)

        resp = client.get("/rebalance")

        assert resp.status_code == 404
