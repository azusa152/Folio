"""Contract tests for stock split routes."""

from unittest.mock import patch

from fastapi.testclient import TestClient


def _create_account(client: TestClient) -> int:
    resp = client.post(
        "/accounts",
        json={
            "name": "Default",
            "broker": "Default",
            "account_type": "brokerage",
            "currency": "USD",
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _create_opening_stock_position(
    client: TestClient,
    *,
    account_id: int,
    ticker: str,
    quantity: float,
    cost_basis: float,
) -> None:
    resp = client.post(
        "/transactions",
        json={
            "account_id": account_id,
            "ticker": ticker,
            "transaction_type": "OPENING_BALANCE",
            "quantity": quantity,
            "price": cost_basis,
            "total_amount": quantity * cost_basis,
            "currency": "USD",
            "transaction_date": "2026-03-10",
        },
    )
    assert resp.status_code == 201


def test_check_stock_splits_should_detect_events(client: TestClient):
    account_id = _create_account(client)
    _create_opening_stock_position(
        client, account_id=account_id, ticker="AAPL", quantity=10, cost_basis=100.0
    )

    with patch(
        "application.portfolio.stock_split_service.get_stock_splits",
        return_value=[{"split_date": "2026-03-15", "ratio": 2.0}],
    ):
        resp = client.post("/stock-splits/check")

    assert resp.status_code == 200
    body = resp.json()
    assert body["checked_tickers"] == 1
    assert body["detected"] == 1
    assert body["auto_applied"] == 0
    assert len(body["events"]) == 1
    assert body["events"][0]["ticker"] == "AAPL"
    assert body["events"][0]["status"] == "pending"


def test_list_pending_stock_splits_should_return_empty_list(client: TestClient):
    resp = client.get("/stock-splits/pending")
    assert resp.status_code == 200
    assert resp.json() == []


def test_apply_stock_split_should_return_404_for_missing_event(client: TestClient):
    resp = client.post("/stock-splits/999999/apply")
    assert resp.status_code == 404


def test_dismiss_stock_split_should_return_404_for_missing_event(client: TestClient):
    resp = client.post("/stock-splits/999999/dismiss")
    assert resp.status_code == 404


def test_apply_all_stock_splits_should_apply_pending_events(client: TestClient):
    account_id = _create_account(client)
    _create_opening_stock_position(
        client, account_id=account_id, ticker="AAPL", quantity=10, cost_basis=100.0
    )
    with patch(
        "application.portfolio.stock_split_service.get_stock_splits",
        return_value=[{"split_date": "2026-03-15", "ratio": 2.0}],
    ):
        check_resp = client.post("/stock-splits/check")
    assert check_resp.status_code == 200
    assert check_resp.json()["detected"] == 1

    resp = client.post("/stock-splits/apply-all")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["applied"] == 1
    assert len(body["results"]) == 1
    assert body["results"][0]["status"] == "applied"

    holdings_resp = client.get("/holdings")
    assert holdings_resp.status_code == 200
    aapl = next(h for h in holdings_resp.json() if h["ticker"] == "AAPL")
    assert aapl["quantity"] == 20.0
