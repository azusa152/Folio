"""Contract tests for transaction CRUD endpoints."""

from fastapi.testclient import TestClient


def test_create_and_list_transaction(client: TestClient):
    payload = {
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
    payload = {
        "ticker": "MSFT",
        "transaction_type": "DIVIDEND",
        "quantity": 5,
        "total_amount": 25.0,
        "currency": "USD",
        "fee": 0.5,
        "note": "Q2 dividend",
        "transaction_date": "2025-07-15",
    }
    resp = client.post("/transactions", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["fee"] == 0.5
    assert data["note"] == "Q2 dividend"
    assert data["price"] is None
    assert data["holding_id"] is None


def test_create_transaction_validation_error(client: TestClient):
    payload = {
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
        "ticker": "AAPL",
        "transaction_type": "INVALID",
        "quantity": 10,
        "total_amount": 1500.0,
        "transaction_date": "2025-06-01",
    }
    resp = client.post("/transactions", json=payload)
    assert resp.status_code == 422


def test_create_transaction_lowercase_type_should_normalize(client: TestClient):
    payload = {
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
    payload = {
        "ticker": "GOOG",
        "transaction_type": "SELL",
        "quantity": 2,
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
