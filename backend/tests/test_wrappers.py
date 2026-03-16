"""Contract tests for wrapper quota APIs."""

from fastapi.testclient import TestClient


def _create_nisa_account(client: TestClient, wrapper: str) -> int:
    resp = client.post(
        "/accounts",
        json={
            "name": f"NISA {wrapper}",
            "broker": "SBI",
            "account_type": "brokerage",
            "tax_wrapper": wrapper,
            "currency": "JPY",
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _deposit(client: TestClient, account_id: int, amount: float) -> None:
    resp = client.post(
        "/transactions",
        json={
            "account_id": account_id,
            "ticker": "JPY",
            "transaction_type": "DEPOSIT",
            "quantity": 1,
            "price": amount,
            "total_amount": amount,
            "currency": "JPY",
            "transaction_date": "2026-01-01",
        },
    )
    assert resp.status_code == 201


def test_wrappers_quota_should_return_nisa_quota_map(client: TestClient):
    resp = client.get("/wrappers/quota")
    assert resp.status_code == 200
    payload = resp.json()
    assert "year" in payload
    assert "as_of" in payload
    assert payload["restoration_policy"] in {"next_year", "same_day"}
    assert "nisa_tsumitate" in payload["quotas"]
    assert "nisa_growth" in payload["quotas"]


def test_wrappers_restoration_forecast_should_include_pending_after_sell(
    client: TestClient,
):
    account_resp = client.post(
        "/accounts",
        json={
            "name": "NISA Growth",
            "broker": "SBI Securities",
            "account_type": "brokerage",
            "tax_wrapper": "nisa_growth",
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
            "price": 1.0,
            "total_amount": 500.0,
            "currency": "USD",
            "transaction_date": "2026-03-09",
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
            "price": 100.0,
            "total_amount": 100.0,
            "currency": "USD",
            "transaction_date": "2026-03-10",
        },
    )
    assert buy_resp.status_code == 201

    sell_resp = client.post(
        "/transactions",
        json={
            "account_id": account_id,
            "ticker": "AAPL",
            "transaction_type": "SELL",
            "quantity": 1,
            "price": 100.0,
            "total_amount": 100.0,
            "currency": "USD",
            "transaction_date": "2026-03-11",
        },
    )
    assert sell_resp.status_code == 201

    forecast_resp = client.get("/wrappers/restoration-forecast")
    assert forecast_resp.status_code == 200
    forecast = forecast_resp.json()
    assert forecast["total_pending"] >= 100.0
    assert any(item["tax_wrapper"] == "nisa_growth" for item in forecast["pending"])


def test_nisa_buy_should_return_422_with_quota_exceeded_payload(client: TestClient):
    """BUY exceeding the annual NISA limit must return 422 with machine-readable error."""
    account_id = _create_nisa_account(client, "nisa_growth")
    # Deposit far more than the annual growth limit (2_400_000 JPY) so cash is not
    # the constraint — only the NISA quota gate should fire.
    _deposit(client, account_id, 3_000_000.0)

    resp = client.post(
        "/transactions",
        json={
            "account_id": account_id,
            "ticker": "7203.T",
            "transaction_type": "BUY",
            "quantity": 1,
            "price": 2_800_000.0,
            "total_amount": 2_800_000.0,
            "currency": "JPY",
            "transaction_date": "2026-06-01",
        },
    )
    assert resp.status_code == 422
    # FastAPI wraps HTTPException detail under the "detail" key.
    detail = resp.json()["detail"]
    assert detail["error_code"] == "QUOTA_EXCEEDED"
    assert "violations" in detail
    assert isinstance(detail["violations"], list)
    assert len(detail["violations"]) > 0


def test_wrapper_check_eligibility_should_return_suggestion_for_ineligible_tsumitate(
    client: TestClient,
):
    resp = client.get(
        "/wrappers/nisa_tsumitate/check-eligibility",
        params={"ticker": "AAPL"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["wrapper"] == "nisa_tsumitate"
    assert payload["ticker"] == "AAPL"
    assert payload["eligible"] is False
    assert "eligibility.not_in_tsumitate_approved_list" in payload["reasons"]
    assert payload["suggested_wrapper"] == "nisa_growth"


def test_wrapper_eligible_assets_should_return_list_shape(client: TestClient):
    resp = client.get("/wrappers/nisa_tsumitate/eligible-assets")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["wrapper"] == "nisa_tsumitate"
    assert isinstance(payload["count"], int)
    assert isinstance(payload["items"], list)


def test_wrappers_suggest_routing_should_split_growth_and_tokutei(client: TestClient):
    # Create a wrapped account so routing has candidate wrappers.
    growth_account_id = _create_nisa_account(client, "nisa_growth")
    _deposit(client, growth_account_id, 500_000.0)
    assert growth_account_id > 0

    routing_resp = client.post(
        "/wrappers/suggest-routing",
        json={"ticker": "AAPL", "total_amount": 3_000_000.0},
    )
    assert routing_resp.status_code == 200
    payload = routing_resp.json()
    assert payload["ticker"] == "AAPL"
    assert payload["total_amount"] == 3_000_000.0
    assert [item["wrapper"] for item in payload["suggestions"]] == [
        "nisa_growth",
        "tokutei",
    ]
    assert payload["suggestions"][0]["amount"] == 2_400_000.0
    assert payload["suggestions"][1]["amount"] == 600_000.0


def test_wrappers_detax_should_return_computed_tax_saving(
    client: TestClient,
    monkeypatch,
):
    from application.portfolio import routing_service

    def _fake_price(ticker: str):
        return {"price": 50.0 if ticker == "BBB" else 200.0}

    monkeypatch.setattr(routing_service, "get_technical_signals", _fake_price)

    account_resp = client.post(
        "/accounts",
        json={
            "name": "Tokutei Test",
            "broker": "SBI",
            "account_type": "brokerage",
            "tax_wrapper": "tokutei",
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
            "price": 250_000.0,
            "total_amount": 250_000.0,
            "currency": "USD",
            "transaction_date": "2026-01-01",
        },
    )
    assert deposit_resp.status_code == 201
    buy_aaa = client.post(
        "/transactions",
        json={
            "account_id": account_id,
            "ticker": "AAA",
            "transaction_type": "BUY",
            "quantity": 500,
            "price": 100.0,
            "total_amount": 50_000.0,
            "currency": "USD",
            "transaction_date": "2026-01-02",
        },
    )
    assert buy_aaa.status_code == 201
    sell_aaa = client.post(
        "/transactions",
        json={
            "account_id": account_id,
            "ticker": "AAA",
            "transaction_type": "SELL",
            "quantity": 500,
            "price": 200.0,
            "total_amount": 100_000.0,
            "currency": "USD",
            "transaction_date": "2026-01-03",
        },
    )
    assert sell_aaa.status_code == 201
    buy_bbb = client.post(
        "/transactions",
        json={
            "account_id": account_id,
            "ticker": "BBB",
            "transaction_type": "BUY",
            "quantity": 500,
            "price": 100.0,
            "total_amount": 50_000.0,
            "currency": "USD",
            "transaction_date": "2026-01-04",
        },
    )
    assert buy_bbb.status_code == 201

    detax_resp = client.get("/wrappers/detax")
    assert detax_resp.status_code == 200
    payload = detax_resp.json()
    assert payload["total_estimated_savings"] == 5_078.75
    assert len(payload["opportunities"]) == 1
    assert payload["opportunities"][0]["ticker"] == "BBB"
    assert payload["opportunities"][0]["estimated_tax_saved"] == 5_078.75
