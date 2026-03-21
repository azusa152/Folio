"""Tests for X-Ray analysis in the rebalance endpoint.

Covers coverage-percentage calculation, skipped-ETF reporting, and the
response-shape contract.
"""

from unittest.mock import patch

import pytest
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

_CASH_HOLDING = {
    "ticker": "USD",
    "category": "Cash",
    "quantity": 1_000_000,
    "cost_basis": 1.0,
    "broker": "Firstrade",
    "currency": "USD",
    "account_type": "US",
    "is_cash": True,
}

_CASH_TW_HOLDING = {
    "ticker": "TWD",
    "category": "Cash",
    "quantity": 1_000_000,
    "cost_basis": 1.0,
    "broker": "Firstrade",
    "currency": "TWD",
    "account_type": "US",
    "is_cash": True,
}

_BOND_TW_HOLDING = {
    "ticker": "BND.TW",
    "category": "Bond",
    "quantity": 100,
    "cost_basis": 100.0,
    "broker": "Firstrade",
    "currency": "USD",
    "account_type": "US",
    "is_cash": False,
}


def _setup_portfolio(client: TestClient, holdings: list[dict] | None = None):
    """Create holdings via transactions and an investment profile."""
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

    seed_cash = client.post(
        "/transactions",
        json={
            "account_id": account_id,
            "ticker": "USD",
            "transaction_type": "DEPOSIT",
            "quantity": 1,
            "total_amount": 10_000_000.0,
            "currency": "USD",
            "transaction_date": "2026-03-11",
        },
    )
    assert seed_cash.status_code == 201

    for h in holdings or [_STOCK_HOLDING]:
        is_cash = bool(h.get("is_cash")) or str(h.get("category", "")).lower() == "cash"
        if is_cash:
            resp = client.post(
                "/transactions",
                json={
                    "account_id": account_id,
                    "ticker": h.get("currency", "USD"),
                    "transaction_type": "DEPOSIT",
                    "quantity": 1,
                    "total_amount": float(h["quantity"]),
                    "currency": h.get("currency", "USD"),
                    "transaction_date": "2026-03-11",
                },
            )
        else:
            price = float(h.get("cost_basis", 0.0))
            quantity = float(h["quantity"])
            resp = client.post(
                "/transactions",
                json={
                    "account_id": account_id,
                    "ticker": h["ticker"],
                    "transaction_type": "BUY",
                    "quantity": quantity,
                    "price": price,
                    "total_amount": price * quantity,
                    "currency": h.get("currency", "USD"),
                    "transaction_date": "2026-03-11",
                },
            )
        assert resp.status_code == 201
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

    @pytest.mark.slow
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

    def test_direct_stock_row_percentages_should_exclude_cash_denominator(self, client):
        """AAPL + large cash should still report 100% equity xray row weights."""
        _setup_portfolio(client, [_STOCK_HOLDING, _CASH_HOLDING])

        resp = client.get("/rebalance")

        assert resp.status_code == 200
        data = resp.json()
        assert data["xray_coverage_pct"] == 100
        xray_by_symbol = {entry["symbol"]: entry for entry in data["xray"]}
        assert "AAPL" in xray_by_symbol
        assert xray_by_symbol["AAPL"]["direct_weight_pct"] == 100
        assert xray_by_symbol["AAPL"]["total_weight_pct"] == 100


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

    def test_skipped_etf_weight_should_exclude_cash_denominator(self, client):
        """Skipped ETF with large cash still uses equity-only denominator."""
        _setup_portfolio(client, [_ETF_HOLDING, _CASH_HOLDING])
        _mark_etf(client, "VTI")

        with (
            patch(
                "application.portfolio.rebalance_service.get_etf_top_holdings",
                return_value=None,
            ),
            patch(
                "application.portfolio.rebalance_service.get_etf_sector_weights",
                return_value=None,
            ),
        ):
            resp = client.get("/rebalance")

        assert resp.status_code == 200
        data = resp.json()
        skipped = data["xray_skipped_etfs"]
        skipped_tickers = [e["ticker"] for e in skipped]
        assert "VTI" in skipped_tickers
        vti_entry = next(e for e in skipped if e["ticker"] == "VTI")
        assert vti_entry["weight_pct"] == 100


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

    def test_sector_equity_pct_should_exclude_cash_and_geo_should_include_cash_region(
        self, client
    ):
        """Sector stays equity-only; TW geo entry comes from TWD cash mapping."""
        _setup_portfolio(client, [_STOCK_HOLDING, _CASH_TW_HOLDING])

        resp = client.get("/rebalance")

        assert resp.status_code == 200
        data = resp.json()

        assert len(data["sector_exposure"]) >= 1
        total_equity_pct = sum(item["equity_pct"] for item in data["sector_exposure"])
        assert total_equity_pct == 100
        assert all(item["weight_pct"] < 100 for item in data["sector_exposure"])

        assert "US" in data["geographic_allocation"]
        assert "TW" in data["geographic_allocation"]
        assert data["geographic_allocation"]["US"] > 0
        assert data["geographic_allocation"]["TW"] > 0
