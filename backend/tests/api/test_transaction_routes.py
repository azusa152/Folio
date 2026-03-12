"""Contract tests for transaction CRUD endpoints."""

import csv
import io

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


def _deposit_cash(client: TestClient, account_id: int, amount: float = 10000.0) -> None:
    resp = client.post(
        "/transactions",
        json={
            "account_id": account_id,
            "ticker": "USD",
            "transaction_type": "DEPOSIT",
            "quantity": 1,
            "total_amount": amount,
            "currency": "USD",
            "transaction_date": "2025-05-31",
        },
    )
    assert resp.status_code == 201


def test_create_and_list_transaction(client: TestClient):
    account_id = _create_account(client)
    _deposit_cash(client, account_id)
    payload = {
        "account_id": account_id,
        "ticker": "AAPL",
        "transaction_type": "BUY",
        "quantity": 10,
        "price": 150.0,
        "total_amount": 1500.0,
        "currency": "USD",
        "transaction_date": "2025-06-01",
    }
    resp = client.post("/transactions", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["ticker"] == "AAPL"
    assert data["transaction_type"] == "BUY"
    assert data["quantity"] == 10
    assert data["total_amount"] == 1500.0
    txn_id = data["id"]

    resp = client.get(f"/transactions/{txn_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == txn_id

    resp = client.get("/transactions", params={"ticker": "AAPL"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    resp = client.delete(f"/transactions/{txn_id}")
    assert resp.status_code == 200


def test_get_nonexistent_transaction(client: TestClient):
    resp = client.get("/transactions/999999")
    assert resp.status_code == 404


def test_delete_nonexistent_transaction(client: TestClient):
    resp = client.delete("/transactions/999999")
    assert resp.status_code == 404


def test_list_transactions_empty(client: TestClient):
    resp = client.get("/transactions")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_transaction_with_optional_fields(client: TestClient):
    account_id = _create_account(client)
    payload = {
        "account_id": account_id,
        "ticker": "USD",
        "transaction_type": "DEPOSIT",
        "quantity": 1,
        "total_amount": 25.0,
        "currency": "USD",
        "fee": 0.5,
        "note": "cash top-up",
        "transaction_date": "2025-07-15",
    }
    resp = client.post("/transactions", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["fee"] == 0.5
    assert data["note"] == "cash top-up"
    assert data["price"] is None
    assert data["holding_id"] is None


def test_create_transaction_validation_error(client: TestClient):
    payload = {
        "account_id": _create_account(client),
        "ticker": "",
        "transaction_type": "BUY",
        "quantity": 10,
        "total_amount": 1500.0,
        "transaction_date": "2025-06-01",
    }
    resp = client.post("/transactions", json=payload)
    assert resp.status_code == 422


def test_create_transaction_invalid_type_should_return_422(client: TestClient):
    payload = {
        "account_id": _create_account(client),
        "ticker": "AAPL",
        "transaction_type": "INVALID",
        "quantity": 10,
        "total_amount": 1500.0,
        "transaction_date": "2025-06-01",
    }
    resp = client.post("/transactions", json=payload)
    assert resp.status_code == 422


def test_create_transaction_lowercase_type_should_normalize(client: TestClient):
    account_id = _create_account(client)
    _deposit_cash(client, account_id)
    payload = {
        "account_id": account_id,
        "ticker": "aapl",
        "transaction_type": "buy",
        "quantity": 5,
        "total_amount": 750.0,
        "currency": "usd",
        "transaction_date": "2025-06-01",
    }
    resp = client.post("/transactions", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["ticker"] == "AAPL"
    assert data["transaction_type"] == "BUY"
    assert data["currency"] == "USD"


def test_list_transactions_negative_limit_should_return_422(client: TestClient):
    resp = client.get("/transactions", params={"limit": -1})
    assert resp.status_code == 422


def test_list_transactions_zero_limit_should_return_422(client: TestClient):
    resp = client.get("/transactions", params={"limit": 0})
    assert resp.status_code == 422


def test_delete_transaction_response_body(client: TestClient):
    account_id = _create_account(client)
    payload = {
        "account_id": account_id,
        "ticker": "USD",
        "transaction_type": "DEPOSIT",
        "quantity": 1,
        "total_amount": 300.0,
        "transaction_date": "2025-08-01",
    }
    resp = client.post("/transactions", json=payload)
    assert resp.status_code == 201
    txn_id = resp.json()["id"]

    resp = client.delete(f"/transactions/{txn_id}")
    assert resp.status_code == 200
    assert "message" in resp.json()
    assert len(resp.json()["message"]) > 0


def test_create_transaction_with_account_should_return_account_id(client: TestClient):
    account_resp = client.post(
        "/accounts",
        json={
            "name": "IB US",
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
            "transaction_date": "2026-03-10",
        },
    )
    assert deposit_resp.status_code == 201

    buy_resp = client.post(
        "/transactions",
        json={
            "account_id": account_id,
            "ticker": "AAPL",
            "transaction_type": "BUY",
            "quantity": 1,
            "price": 500.0,
            "total_amount": 500.0,
            "currency": "USD",
            "transaction_date": "2026-03-10",
        },
    )
    assert buy_resp.status_code == 201
    assert buy_resp.json()["account_id"] == account_id


def test_create_transaction_should_auto_add_new_stock_with_custom_thesis(
    client: TestClient,
):
    account_id = _create_account(client)
    resp = client.post(
        "/transactions",
        json={
            "account_id": account_id,
            "ticker": "QQQ",
            "transaction_type": "OPENING_BALANCE",
            "quantity": 2,
            "price": 100.0,
            "total_amount": 200.0,
            "currency": "USD",
            "transaction_date": "2026-03-10",
            "thesis": "Core ETF thesis",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["ticker"] == "QQQ"
    assert body["auto_radar"] is True

    stocks_resp = client.get("/stocks")
    assert stocks_resp.status_code == 200
    qqq = next(stock for stock in stocks_resp.json() if stock["ticker"] == "QQQ")
    assert qqq["current_thesis"] == "Core ETF thesis"


def test_create_transaction_should_not_recreate_existing_radar_stock(
    client: TestClient,
):
    account_id = _create_account(client)
    create_stock_resp = client.post(
        "/ticker",
        json={
            "ticker": "QQQ",
            "category": "Trend_Setter",
            "thesis": "Original thesis",
            "is_etf": True,
        },
    )
    assert create_stock_resp.status_code == 200

    resp = client.post(
        "/transactions",
        json={
            "account_id": account_id,
            "ticker": "QQQ",
            "transaction_type": "OPENING_BALANCE",
            "quantity": 1,
            "price": 100.0,
            "total_amount": 100.0,
            "currency": "USD",
            "transaction_date": "2026-03-11",
            "thesis": "Should not override",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["auto_radar"] is False

    stocks_resp = client.get("/stocks")
    assert stocks_resp.status_code == 200
    qqq = next(stock for stock in stocks_resp.json() if stock["ticker"] == "QQQ")
    assert qqq["current_thesis"] == "Original thesis"


def test_create_cash_transaction_should_not_trigger_auto_radar(client: TestClient):
    account_id = _create_account(client)
    resp = client.post(
        "/transactions",
        json={
            "account_id": account_id,
            "ticker": "USD",
            "transaction_type": "DEPOSIT",
            "quantity": 1,
            "total_amount": 250.0,
            "currency": "USD",
            "transaction_date": "2026-03-10",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["auto_radar"] is False
    stocks_resp = client.get("/stocks")
    assert stocks_resp.status_code == 200
    assert all(stock["ticker"] != "USD" for stock in stocks_resp.json())


def test_create_transaction_should_reactivate_inactive_stock_on_radar(
    client: TestClient,
):
    account_id = _create_account(client)
    create_stock_resp = client.post(
        "/ticker",
        json={
            "ticker": "QQQ",
            "category": "Trend_Setter",
            "thesis": "Old thesis",
            "is_etf": True,
        },
    )
    assert create_stock_resp.status_code == 200
    deactivate_resp = client.post("/ticker/QQQ/deactivate", json={"reason": "cleanup"})
    assert deactivate_resp.status_code == 200

    resp = client.post(
        "/transactions",
        json={
            "account_id": account_id,
            "ticker": "QQQ",
            "transaction_type": "OPENING_BALANCE",
            "quantity": 1,
            "price": 100.0,
            "total_amount": 100.0,
            "currency": "USD",
            "transaction_date": "2026-03-11",
            "thesis": "Reactivated via transaction",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["auto_radar"] is True

    stocks_resp = client.get("/stocks")
    assert stocks_resp.status_code == 200
    qqq = next(stock for stock in stocks_resp.json() if stock["ticker"] == "QQQ")
    assert qqq["is_active"] is True
    assert qqq["current_thesis"] == "Reactivated via transaction"


def test_reactivate_inactive_stock_should_apply_explicit_category_from_transaction(
    client: TestClient,
):
    account_id = _create_account(client)
    _deposit_cash(client, account_id, amount=1000.0)
    create_stock_resp = client.post(
        "/ticker",
        json={
            "ticker": "CSCO",
            "category": "Growth",
            "thesis": "Old thesis",
            "is_etf": False,
        },
    )
    assert create_stock_resp.status_code == 200
    deactivate_resp = client.post("/ticker/CSCO/deactivate", json={"reason": "cleanup"})
    assert deactivate_resp.status_code == 200

    resp = client.post(
        "/transactions",
        json={
            "account_id": account_id,
            "ticker": "CSCO",
            "transaction_type": "BUY",
            "quantity": 1,
            "price": 100.0,
            "total_amount": 100.0,
            "currency": "USD",
            "transaction_date": "2026-03-12",
            "thesis": "Reactivated via transaction",
            "category": "Moat",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["auto_radar"] is True

    stocks_resp = client.get("/stocks")
    assert stocks_resp.status_code == 200
    csco = next(stock for stock in stocks_resp.json() if stock["ticker"] == "CSCO")
    assert csco["is_active"] is True
    assert csco["category"] == "Moat"


def test_create_transaction_with_new_ticker_should_use_explicit_category(
    client: TestClient,
):
    account_id = _create_account(client)
    _deposit_cash(client, account_id, amount=1000.0)

    resp = client.post(
        "/transactions",
        json={
            "account_id": account_id,
            "ticker": "CSCO",
            "transaction_type": "BUY",
            "quantity": 1,
            "price": 100.0,
            "total_amount": 100.0,
            "currency": "USD",
            "transaction_date": "2026-03-12",
            "thesis": "Networking thesis",
            "category": "Moat",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["auto_radar"] is True

    stocks_resp = client.get("/stocks")
    assert stocks_resp.status_code == 200
    csco = next(stock for stock in stocks_resp.json() if stock["ticker"] == "CSCO")
    assert csco["category"] == "Moat"

    holdings_resp = client.get("/holdings")
    assert holdings_resp.status_code == 200
    csco_holding = next(
        holding for holding in holdings_resp.json() if holding["ticker"] == "CSCO"
    )
    assert csco_holding["category"] == "Moat"


def test_import_transactions_should_not_leak_auto_radar_from_failed_item(
    client: TestClient,
):
    account_id = _create_account(client)
    resp = client.post(
        "/transactions/import",
        json={
            "account_id": account_id,
            "items": [
                {
                    "ticker": "AAPL",
                    "transaction_type": "BUY",
                    "quantity": 1,
                    "price": 100.0,
                    "total_amount": 100.0,
                    "currency": "USD",
                    "transaction_date": "2026-03-10",
                    "thesis": "Should not persist",
                },
                {
                    "ticker": "USD",
                    "transaction_type": "DEPOSIT",
                    "quantity": 1,
                    "total_amount": 1000.0,
                    "currency": "USD",
                    "transaction_date": "2026-03-10",
                },
            ],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["imported"] == 1
    assert len(body["errors"]) == 1

    stocks_resp = client.get("/stocks")
    assert stocks_resp.status_code == 200
    assert all(stock["ticker"] != "AAPL" for stock in stocks_resp.json())


def test_import_transactions_should_return_import_summary(client: TestClient):
    account_id = _create_account(client)
    resp = client.post(
        "/transactions/import",
        json={
            "account_id": account_id,
            "items": [
                {
                    "ticker": "USD",
                    "transaction_type": "DEPOSIT",
                    "quantity": 1,
                    "total_amount": 180.0,
                    "currency": "USD",
                    "transaction_date": "2026-03-10",
                },
                {
                    "ticker": "USD",
                    "transaction_type": "WITHDRAWAL",
                    "quantity": 1,
                    "total_amount": 3.5,
                    "currency": "USD",
                    "transaction_date": "2026-03-11",
                },
            ],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["imported"] == 2
    assert body["errors"] == []


def test_import_transactions_with_account_id_should_apply_to_all_items(
    client: TestClient,
):
    account_resp = client.post(
        "/accounts",
        json={
            "name": "IB US",
            "broker": "Interactive Brokers",
            "account_type": "brokerage",
            "currency": "USD",
        },
    )
    assert account_resp.status_code == 201
    account_id = account_resp.json()["id"]

    resp = client.post(
        "/transactions/import",
        json={
            "account_id": account_id,
            "items": [
                {
                    "ticker": "USD",
                    "transaction_type": "DEPOSIT",
                    "quantity": 1,
                    "total_amount": 1000.0,
                    "currency": "USD",
                    "transaction_date": "2026-03-10",
                },
                {
                    "ticker": "AAPL",
                    "transaction_type": "BUY",
                    "quantity": 1,
                    "price": 500.0,
                    "total_amount": 500.0,
                    "currency": "USD",
                    "transaction_date": "2026-03-10",
                },
            ],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["imported"] == 2
    assert body["errors"] == []

    txns = client.get("/transactions", params={"account_id": account_id}).json()
    assert len(txns) >= 2
    assert all(txn["account_id"] == account_id for txn in txns[:2])


def test_export_transactions_csv_should_return_csv_with_headers(client: TestClient):
    account_id = _create_account(client)
    _deposit_cash(client, account_id, amount=1000.0)
    buy_resp = client.post(
        "/transactions",
        json={
            "account_id": account_id,
            "ticker": "AAPL",
            "transaction_type": "BUY",
            "quantity": 1,
            "price": 100.0,
            "total_amount": 100.0,
            "currency": "USD",
            "transaction_date": "2026-03-12",
        },
    )
    assert buy_resp.status_code == 201

    resp = client.get("/transactions/export-csv", params={"account_id": account_id})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=" in resp.headers.get("content-disposition", "")

    rows = list(csv.DictReader(io.StringIO(resp.text)))
    assert len(rows) >= 2
    assert {
        "transaction_date",
        "ticker",
        "transaction_type",
        "quantity",
        "price",
        "total_amount",
        "currency",
        "fx_rate",
        "fee",
        "note",
        "account_name",
    }.issubset(set(rows[0].keys()))


def test_export_transactions_csv_should_respect_account_filter(client: TestClient):
    account_a = _create_account(client)
    account_b_resp = client.post(
        "/accounts",
        json={
            "name": "Second",
            "broker": "Second",
            "account_type": "brokerage",
            "currency": "USD",
        },
    )
    assert account_b_resp.status_code == 201
    account_b = account_b_resp.json()["id"]

    _deposit_cash(client, account_a, amount=1000.0)
    _deposit_cash(client, account_b, amount=2000.0)
    a_buy = client.post(
        "/transactions",
        json={
            "account_id": account_a,
            "ticker": "AAPL",
            "transaction_type": "BUY",
            "quantity": 1,
            "price": 100.0,
            "total_amount": 100.0,
            "currency": "USD",
            "transaction_date": "2026-03-12",
        },
    )
    assert a_buy.status_code == 201
    b_buy = client.post(
        "/transactions",
        json={
            "account_id": account_b,
            "ticker": "MSFT",
            "transaction_type": "BUY",
            "quantity": 1,
            "price": 200.0,
            "total_amount": 200.0,
            "currency": "USD",
            "transaction_date": "2026-03-12",
        },
    )
    assert b_buy.status_code == 201

    resp = client.get("/transactions/export-csv", params={"account_id": account_a})
    assert resp.status_code == 200
    rows = list(csv.DictReader(io.StringIO(resp.text)))
    tickers = {row["ticker"] for row in rows}
    assert "AAPL" in tickers
    assert "MSFT" not in tickers
