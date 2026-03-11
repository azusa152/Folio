"""Contract tests for account CRUD and summary endpoints."""

from fastapi.testclient import TestClient


def test_account_crud(client: TestClient):
    payload = {
        "name": "IB US Stocks",
        "broker": "Interactive Brokers",
        "account_type": "brokerage",
        "currency": "USD",
    }
    resp = client.post("/accounts", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "IB US Stocks"
    assert data["broker"] == "Interactive Brokers"
    assert data["account_type"] == "brokerage"
    assert data["currency"] == "USD"
    assert data["is_active"] is True
    acct_id = data["id"]

    resp = client.put(f"/accounts/{acct_id}", json={"note": "Main trading"})
    assert resp.status_code == 200
    assert resp.json()["note"] == "Main trading"

    resp = client.get("/accounts")
    assert resp.status_code == 200
    assert any(a["id"] == acct_id for a in resp.json())

    resp = client.delete(f"/accounts/{acct_id}")
    assert resp.status_code == 200


def test_account_not_found(client: TestClient):
    resp = client.put("/accounts/99999", json={"note": "nope"})
    assert resp.status_code == 404

    resp = client.delete("/accounts/99999")
    assert resp.status_code == 404


def test_account_summary(client: TestClient):
    resp = client.get("/accounts/summary")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_account_summary_with_holdings(client: TestClient):
    acct_resp = client.post(
        "/accounts",
        json={"name": "SBI Japan", "broker": "SBI Securities"},
    )
    assert acct_resp.status_code == 201

    resp = client.get("/accounts/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["account"]["name"] == "SBI Japan"
    assert data[0]["holdings_count"] == 0
    assert data[0]["tickers"] == []
    assert data[0]["cash_balances"] == [{"currency": "USD", "balance": 0.0}]


def test_account_create_should_initialize_zero_cash_balance(client: TestClient):
    acct_resp = client.post(
        "/accounts",
        json={"name": "Zero Cash", "broker": "Demo Broker", "currency": "USD"},
    )
    assert acct_resp.status_code == 201
    account_id = acct_resp.json()["id"]

    balances_resp = client.get(f"/accounts/{account_id}/cash-balances")
    assert balances_resp.status_code == 200
    assert balances_resp.json() == [{"currency": "USD", "balance": 0.0}]

    summary_resp = client.get("/accounts/summary")
    assert summary_resp.status_code == 200
    account_row = next(
        (
            item
            for item in summary_resp.json()
            if item.get("account", {}).get("id") == account_id
        ),
        None,
    )
    assert account_row is not None
    assert account_row["holdings_count"] == 0
    assert account_row["tickers"] == []


def test_account_create_validation(client: TestClient):
    resp = client.post("/accounts", json={"broker": "IB"})
    assert resp.status_code == 422

    resp = client.post("/accounts", json={"name": "IB"})
    assert resp.status_code == 422


def test_account_cash_balances_endpoint(client: TestClient):
    acct_resp = client.post(
        "/accounts",
        json={
            "name": "IB Main",
            "broker": "Interactive Brokers",
            "account_type": "brokerage",
            "currency": "USD",
        },
    )
    assert acct_resp.status_code == 201
    account_id = acct_resp.json()["id"]

    deposit_resp = client.post(
        "/transactions",
        json={
            "account_id": account_id,
            "ticker": "USD",
            "transaction_type": "DEPOSIT",
            "quantity": 1,
            "total_amount": 750.0,
            "currency": "USD",
            "transaction_date": "2026-03-10",
        },
    )
    assert deposit_resp.status_code == 201

    balances_resp = client.get(f"/accounts/{account_id}/cash-balances")
    assert balances_resp.status_code == 200
    assert balances_resp.json() == [{"currency": "USD", "balance": 750.0}]


def test_accounts_include_inactive_query(client: TestClient):
    created = client.post(
        "/accounts",
        json={
            "name": "Legacy Broker",
            "broker": "Legacy",
            "account_type": "brokerage",
            "currency": "USD",
        },
    )
    assert created.status_code == 201
    account_id = created.json()["id"]

    deactivated = client.delete(f"/accounts/{account_id}")
    assert deactivated.status_code == 200

    active_only = client.get("/accounts")
    assert active_only.status_code == 200
    assert all(account["id"] != account_id for account in active_only.json())

    with_inactive = client.get("/accounts?include_inactive=true")
    assert with_inactive.status_code == 200
    assert any(account["id"] == account_id for account in with_inactive.json())
