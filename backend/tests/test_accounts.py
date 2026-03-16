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
    assert data["tax_wrapper"] is None
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
        json={
            "name": "SBI Japan",
            "broker": "SBI Securities",
            "tax_wrapper": "nisa_tsumitate",
        },
    )
    assert acct_resp.status_code == 201

    resp = client.get("/accounts/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["account"]["name"] == "SBI Japan"
    assert data[0]["account"]["tax_wrapper"] == "nisa_tsumitate"
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


def test_account_should_persist_tax_wrapper(client: TestClient):
    create_resp = client.post(
        "/accounts",
        json={
            "name": "NISA Account",
            "broker": "SBI Securities",
            "account_type": "brokerage",
            "tax_wrapper": "nisa_growth",
            "currency": "JPY",
        },
    )
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["tax_wrapper"] == "nisa_growth"

    account_id = created["id"]
    update_resp = client.put(
        f"/accounts/{account_id}",
        json={
            "tax_wrapper": "tokutei",
        },
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["tax_wrapper"] == "tokutei"

    list_resp = client.get("/accounts")
    assert list_resp.status_code == 200
    listed = next(item for item in list_resp.json() if item["id"] == account_id)
    assert listed["tax_wrapper"] == "tokutei"


def test_account_should_reject_invalid_tax_wrapper(client: TestClient):
    resp = client.post(
        "/accounts",
        json={
            "name": "Invalid Wrapper",
            "broker": "Demo Broker",
            "tax_wrapper": "invalid_wrapper",
            "currency": "USD",
        },
    )
    assert resp.status_code == 422


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


def test_account_positions_should_return_holdings_for_selected_account(
    client: TestClient,
):
    account_a = client.post(
        "/accounts",
        json={
            "name": "Primary",
            "broker": "IBKR",
            "account_type": "brokerage",
            "currency": "USD",
        },
    )
    account_b = client.post(
        "/accounts",
        json={
            "name": "Secondary",
            "broker": "SBI",
            "account_type": "brokerage",
            "currency": "USD",
        },
    )
    assert account_a.status_code == 201
    assert account_b.status_code == 201
    account_a_id = account_a.json()["id"]
    account_b_id = account_b.json()["id"]

    for account_id, ticker, quantity, price in (
        (account_a_id, "AAPL", 2, 190.0),
        (account_b_id, "TSLA", 1, 230.0),
    ):
        deposit_resp = client.post(
            "/transactions",
            json={
                "account_id": account_id,
                "ticker": "USD",
                "transaction_type": "DEPOSIT",
                "quantity": 1,
                "total_amount": 5000.0,
                "currency": "USD",
                "transaction_date": "2026-03-11",
            },
        )
        buy_resp = client.post(
            "/transactions",
            json={
                "account_id": account_id,
                "ticker": ticker,
                "transaction_type": "BUY",
                "quantity": quantity,
                "price": price,
                "total_amount": quantity * price,
                "currency": "USD",
                "transaction_date": "2026-03-11",
            },
        )
        assert deposit_resp.status_code == 201
        assert buy_resp.status_code == 201

    resp = client.get(f"/accounts/{account_a_id}/positions")
    assert resp.status_code == 200
    payload = resp.json()
    assert any(item["ticker"] == "AAPL" for item in payload)
    assert all(item["account_id"] == account_a_id for item in payload)


def test_account_transactions_should_return_paginated_transactions(client: TestClient):
    account_resp = client.post(
        "/accounts",
        json={
            "name": "Txn Account",
            "broker": "IBKR",
            "account_type": "brokerage",
            "currency": "USD",
        },
    )
    assert account_resp.status_code == 201
    account_id = account_resp.json()["id"]

    for amount, txn_date in ((1000.0, "2026-03-10"), (2000.0, "2026-03-11")):
        txn_resp = client.post(
            "/transactions",
            json={
                "account_id": account_id,
                "ticker": "USD",
                "transaction_type": "DEPOSIT",
                "quantity": 1,
                "total_amount": amount,
                "currency": "USD",
                "transaction_date": txn_date,
            },
        )
        assert txn_resp.status_code == 201

    first_page_resp = client.get(
        f"/accounts/{account_id}/transactions?limit=1&offset=0"
    )
    assert first_page_resp.status_code == 200
    first_page = first_page_resp.json()
    assert len(first_page) == 1
    assert first_page[0]["account_id"] == account_id

    second_page_resp = client.get(
        f"/accounts/{account_id}/transactions?limit=1&offset=1"
    )
    assert second_page_resp.status_code == 200
    second_page = second_page_resp.json()
    assert len(second_page) == 1
    assert second_page[0]["account_id"] == account_id
    assert first_page[0]["id"] != second_page[0]["id"]


def test_account_positions_and_transactions_should_return_404_for_unknown_account(
    client: TestClient,
):
    positions_resp = client.get("/accounts/99999/positions")
    assert positions_resp.status_code == 404

    transactions_resp = client.get("/accounts/99999/transactions")
    assert transactions_resp.status_code == 404


def test_deactivate_all_accounts_should_hide_positions_from_holdings_and_rebalance(
    client: TestClient,
):
    account_resp = client.post(
        "/accounts",
        json={
            "name": "IB Main",
            "broker": "Interactive Brokers",
            "account_type": "brokerage",
            "currency": "USD",
        },
    )
    assert account_resp.status_code == 201
    account_id = account_resp.json()["id"]

    deposit_resp = client.post(
        "/transactions",
        json={
            "account_id": account_id,
            "ticker": "USD",
            "transaction_type": "DEPOSIT",
            "quantity": 1,
            "total_amount": 1000.0,
            "currency": "USD",
            "transaction_date": "2026-03-11",
        },
    )
    assert deposit_resp.status_code == 201

    buy_resp = client.post(
        "/transactions",
        json={
            "account_id": account_id,
            "ticker": "AAPL",
            "transaction_type": "BUY",
            "quantity": 2,
            "price": 100.0,
            "total_amount": 200.0,
            "currency": "USD",
            "transaction_date": "2026-03-11",
        },
    )
    assert buy_resp.status_code == 201
    profile_resp = client.post(
        "/profiles",
        json={"config": {"Growth": 100}, "home_currency": "USD"},
    )
    assert profile_resp.status_code in (200, 201)

    rebalance_before = client.get("/rebalance")
    assert rebalance_before.status_code == 200
    assert len(rebalance_before.json()["holdings_detail"]) >= 1

    deactivate_resp = client.delete(f"/accounts/{account_id}")
    assert deactivate_resp.status_code == 200

    holdings_resp = client.get("/holdings")
    assert holdings_resp.status_code == 200
    assert holdings_resp.json() == []

    rebalance_after = client.get("/rebalance")
    assert rebalance_after.status_code == 404
