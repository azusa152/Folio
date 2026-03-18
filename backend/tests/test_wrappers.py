"""Contract tests for wrapper quota APIs."""

import httpx
from fastapi.testclient import TestClient

from domain.constants import DEFAULT_LANGUAGE
from i18n import t


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


def test_wrappers_contributions_should_return_filtered_history(client: TestClient):
    growth_account_id = _create_nisa_account(client, "nisa_growth")
    _deposit(client, growth_account_id, 1_000_000.0)
    buy_resp = client.post(
        "/transactions",
        json={
            "account_id": growth_account_id,
            "ticker": "1306.T",
            "transaction_type": "BUY",
            "quantity": 10,
            "price": 2_000.0,
            "total_amount": 20_000.0,
            "currency": "JPY",
            "transaction_date": "2026-02-01",
        },
    )
    assert buy_resp.status_code == 201

    resp = client.get(
        "/wrappers/contributions",
        params={"wrapper": "nisa_growth", "year": 2026, "limit": 50},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["count"] >= 1
    assert isinstance(payload["items"], list)
    for item in payload["items"]:
        assert item["tax_wrapper"] == "nisa_growth"
        assert item["fiscal_year"] == 2026
        assert item["entry_type"] in {"CONTRIBUTION", "RESTORATION", "ADJUSTMENT"}


def test_wrappers_contributions_should_reject_invalid_wrapper_with_structured_error(
    client: TestClient,
):
    resp = client.get("/wrappers/contributions", params={"wrapper": "tokutei"})
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["error_code"] == "INVALID_INPUT"
    assert detail["detail"] == t(
        "eligibility.contributions_unsupported_wrapper",
        lang=DEFAULT_LANGUAGE,
    )


def test_wrappers_contributions_should_apply_limit(client: TestClient):
    growth_account_id = _create_nisa_account(client, "nisa_growth")
    _deposit(client, growth_account_id, 1_000_000.0)
    first_buy = client.post(
        "/transactions",
        json={
            "account_id": growth_account_id,
            "ticker": "1306.T",
            "transaction_type": "BUY",
            "quantity": 10,
            "price": 2_000.0,
            "total_amount": 20_000.0,
            "currency": "JPY",
            "transaction_date": "2026-02-01",
        },
    )
    assert first_buy.status_code == 201
    second_buy = client.post(
        "/transactions",
        json={
            "account_id": growth_account_id,
            "ticker": "1475.T",
            "transaction_type": "BUY",
            "quantity": 10,
            "price": 2_000.0,
            "total_amount": 20_000.0,
            "currency": "JPY",
            "transaction_date": "2026-02-02",
        },
    )
    assert second_buy.status_code == 201

    resp = client.get(
        "/wrappers/contributions",
        params={"wrapper": "nisa_growth", "year": 2026, "limit": 1},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["count"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["tax_wrapper"] == "nisa_growth"
    assert payload["items"][0]["fiscal_year"] == 2026


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


def test_wrapper_check_eligibility_should_include_asset_type_for_growth_mutual_fund(
    client: TestClient,
):
    csv_content = (
        b"ticker,fund_name,asset_type,trust_fee_pct\n"
        b"01312179,eMAXIS Slim S&P500,mutual_fund,0.0814\n"
    )
    upload_resp = client.post(
        "/wrappers/nisa_growth/eligible-assets/upload",
        files={"file": ("eligible.csv", csv_content, "text/csv")},
    )
    assert upload_resp.status_code == 200

    resp = client.get(
        "/wrappers/nisa_growth/check-eligibility",
        params={"ticker": "01312179"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["wrapper"] == "nisa_growth"
    assert payload["ticker"] == "01312179"
    assert payload["eligible"] is True
    assert payload["asset_type"] == "mutual_fund"


def test_wrapper_eligible_assets_should_return_list_shape(client: TestClient):
    resp = client.get("/wrappers/nisa_tsumitate/eligible-assets")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["wrapper"] == "nisa_tsumitate"
    assert isinstance(payload["count"], int)
    assert isinstance(payload["total_count"], int)
    assert isinstance(payload["items"], list)


def test_wrapper_eligible_assets_search_should_match_fullwidth_query(
    client: TestClient,
):
    csv_content = (
        b"ticker,fund_name,asset_type,trust_fee_pct\n"
        b"03311187,eMAXIS Slim S&P500,mutual_fund,0.0814\n"
    )
    upload_resp = client.post(
        "/wrappers/nisa_tsumitate/eligible-assets/upload",
        files={"file": ("eligible.csv", csv_content, "text/csv")},
    )
    assert upload_resp.status_code == 200

    search_resp = client.get(
        "/wrappers/nisa_tsumitate/eligible-assets",
        params={"search": "\uff33\uff06\uff30\uff15\uff10\uff10"},
    )
    assert search_resp.status_code == 200
    payload = search_resp.json()
    assert payload["count"] == 1
    assert payload["total_count"] == 1
    assert payload["items"][0]["ticker"] == "03311187"


def test_wrapper_eligible_assets_search_should_match_halfwidth_query_against_fullwidth_name(
    client: TestClient,
):
    csv_text = (
        "ticker,fund_name,asset_type,trust_fee_pct\n"
        "09311187,eMAXIS Slim Ｓ＆Ｐ５００,mutual_fund,0.0814\n"
    )
    upload_resp = client.post(
        "/wrappers/nisa_tsumitate/eligible-assets/upload",
        files={"file": ("eligible.csv", csv_text.encode("utf-8"), "text/csv")},
    )
    assert upload_resp.status_code == 200

    search_resp = client.get(
        "/wrappers/nisa_tsumitate/eligible-assets",
        params={"search": "S&P500"},
    )
    assert search_resp.status_code == 200
    payload = search_resp.json()
    assert payload["count"] == 1
    assert payload["total_count"] == 1
    assert payload["items"][0]["ticker"] == "09311187"


def test_wrapper_eligible_assets_should_return_count_and_total_count_with_limit(
    client: TestClient,
):
    csv_text = (
        "ticker,fund_name,asset_type,trust_fee_pct\n"
        "01311187,Slim Limit Alpha,mutual_fund,0.0814\n"
        "01311188,Slim Limit Beta,mutual_fund,0.0815\n"
    )
    upload_resp = client.post(
        "/wrappers/nisa_tsumitate/eligible-assets/upload",
        files={"file": ("eligible.csv", csv_text.encode("utf-8"), "text/csv")},
    )
    assert upload_resp.status_code == 200

    resp = client.get(
        "/wrappers/nisa_tsumitate/eligible-assets",
        params={"search": "Slim Limit", "limit": 1},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["count"] == 1
    assert payload["total_count"] == 2
    assert len(payload["items"]) == payload["count"]


def test_wrapper_eligible_assets_upload_should_accept_csv(client: TestClient):
    csv_content = (
        b"ticker,fund_name,asset_type,trust_fee_pct\n"
        b"03311187,eMAXIS Slim S&P500,mutual_fund,0.0814\n"
    )
    upload_resp = client.post(
        "/wrappers/nisa_tsumitate/eligible-assets/upload",
        files={"file": ("eligible.csv", csv_content, "text/csv")},
    )
    assert upload_resp.status_code == 200
    payload = upload_resp.json()
    assert payload["wrapper"] == "nisa_tsumitate"
    assert payload["source"] == "manual_upload"
    assert payload["stats"]["added"] >= 1


def test_wrapper_eligible_assets_metadata_should_return_sync_info(client: TestClient):
    csv_content = (
        b"ticker,fund_name,asset_type,trust_fee_pct\n"
        b"03311187,eMAXIS Slim S&P500,mutual_fund,0.0814\n"
    )
    client.post(
        "/wrappers/nisa_tsumitate/eligible-assets/upload",
        files={"file": ("eligible.csv", csv_content, "text/csv")},
    )

    metadata_resp = client.get("/wrappers/nisa_tsumitate/eligible-assets/metadata")
    assert metadata_resp.status_code == 200
    payload = metadata_resp.json()
    assert payload["wrapper"] == "nisa_tsumitate"
    assert payload["count"] >= 1
    assert payload["source"] in {
        "manual_upload",
        "csv_seed",
        "official_sync",
        "unknown",
    }


def test_wrapper_eligible_assets_refresh_should_return_stats(
    client: TestClient, monkeypatch
):
    from api.routes import wrapper_routes

    def _fake_sync(session, wrapper: str):
        return {"added": 1, "updated": 0, "deactivated": 0}

    monkeypatch.setattr(wrapper_routes, "sync_wrapper_from_official_source", _fake_sync)
    refresh_resp = client.post("/wrappers/nisa_growth/eligible-assets/refresh")
    assert refresh_resp.status_code == 200
    payload = refresh_resp.json()
    assert payload["wrapper"] == "nisa_growth"
    assert payload["source"] == "official_sync"
    assert payload["stats"]["added"] == 1


def test_wrapper_eligible_assets_upload_should_return_structured_error_on_invalid_extension(
    client: TestClient,
):
    upload_resp = client.post(
        "/wrappers/nisa_tsumitate/eligible-assets/upload",
        files={"file": ("eligible.txt", b"bad", "text/plain")},
    )
    assert upload_resp.status_code == 422
    detail = upload_resp.json()["detail"]
    assert detail["error_code"] == "INVALID_INPUT"


def test_wrapper_eligible_assets_upload_should_reject_unsupported_wrapper(
    client: TestClient,
):
    upload_resp = client.post(
        "/wrappers/tokutei/eligible-assets/upload",
        files={"file": ("eligible.csv", b"ticker,fund_name\n", "text/csv")},
    )
    assert upload_resp.status_code == 422
    detail = upload_resp.json()["detail"]
    assert detail["error_code"] == "INVALID_INPUT"


def test_wrapper_eligible_assets_upload_should_return_structured_error_on_empty_source(
    client: TestClient,
):
    upload_resp = client.post(
        "/wrappers/nisa_tsumitate/eligible-assets/upload",
        files={"file": ("eligible.csv", b"ticker,fund_name\n", "text/csv")},
    )
    assert upload_resp.status_code == 422
    detail = upload_resp.json()["detail"]
    assert detail["error_code"] == "ELIGIBILITY_UPLOAD_FAILED"


def test_wrapper_eligible_assets_refresh_should_return_structured_error_on_parse_failure(
    client: TestClient,
    monkeypatch,
):
    from api.routes import wrapper_routes

    def _fake_sync(_session, _wrapper: str):
        raise ValueError("empty parse")

    monkeypatch.setattr(wrapper_routes, "sync_wrapper_from_official_source", _fake_sync)
    refresh_resp = client.post("/wrappers/nisa_growth/eligible-assets/refresh")
    assert refresh_resp.status_code == 422
    detail = refresh_resp.json()["detail"]
    assert detail["error_code"] == "ELIGIBILITY_REFRESH_FAILED"


def test_wrapper_eligible_assets_refresh_should_map_http_errors_to_structured_error(
    client: TestClient,
    monkeypatch,
):
    from api.routes import wrapper_routes

    def _fake_sync(_session, _wrapper: str):
        request = httpx.Request("GET", "https://example.com/source.xlsx")
        raise httpx.RequestError("network failed", request=request)

    monkeypatch.setattr(wrapper_routes, "sync_wrapper_from_official_source", _fake_sync)
    refresh_resp = client.post("/wrappers/nisa_growth/eligible-assets/refresh")
    assert refresh_resp.status_code == 422
    detail = refresh_resp.json()["detail"]
    assert detail["error_code"] == "ELIGIBILITY_REFRESH_FAILED"


def test_wrapper_eligible_assets_refresh_should_map_runtime_errors_to_structured_error(
    client: TestClient,
    monkeypatch,
):
    from api.routes import wrapper_routes

    def _fake_sync(_session, _wrapper: str):
        raise RuntimeError("unexpected parser crash")

    monkeypatch.setattr(wrapper_routes, "sync_wrapper_from_official_source", _fake_sync)
    refresh_resp = client.post("/wrappers/nisa_growth/eligible-assets/refresh")
    assert refresh_resp.status_code == 422
    detail = refresh_resp.json()["detail"]
    assert detail["error_code"] == "ELIGIBILITY_REFRESH_FAILED"


def test_wrapper_eligible_assets_upload_should_map_runtime_errors_to_structured_error(
    client: TestClient,
    monkeypatch,
):
    from api.routes import wrapper_routes

    def _fake_refresh(*_args, **_kwargs):
        raise RuntimeError("unexpected parser crash")

    monkeypatch.setattr(wrapper_routes, "refresh_eligible_assets", _fake_refresh)
    upload_resp = client.post(
        "/wrappers/nisa_tsumitate/eligible-assets/upload",
        files={"file": ("eligible.csv", b"ticker,fund_name\n", "text/csv")},
    )
    assert upload_resp.status_code == 422
    detail = upload_resp.json()["detail"]
    assert detail["error_code"] == "ELIGIBILITY_UPLOAD_FAILED"


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
    assert payload["suggestions"][0]["account_id"] == growth_account_id


def test_wrappers_suggest_routing_should_exclude_non_jpy_accounts(client: TestClient):
    usd_account_resp = client.post(
        "/accounts",
        json={
            "name": "NISA Growth USD",
            "broker": "SBI",
            "account_type": "brokerage",
            "tax_wrapper": "nisa_growth",
            "currency": "USD",
        },
    )
    assert usd_account_resp.status_code == 201

    routing_resp = client.post(
        "/wrappers/suggest-routing",
        json={"ticker": "AAPL", "total_amount": 300_000.0},
    )
    assert routing_resp.status_code == 200
    payload = routing_resp.json()
    assert payload["suggestions"] == []


def test_wrappers_suggest_routing_should_exclude_non_routing_wrappers(
    client: TestClient,
):
    ippan_resp = client.post(
        "/accounts",
        json={
            "name": "Ippan JPY",
            "broker": "SBI",
            "account_type": "brokerage",
            "tax_wrapper": "ippan",
            "currency": "JPY",
        },
    )
    assert ippan_resp.status_code == 201

    routing_resp = client.post(
        "/wrappers/suggest-routing",
        json={"ticker": "AAPL", "total_amount": 300_000.0},
    )
    assert routing_resp.status_code == 200
    payload = routing_resp.json()
    assert payload["suggestions"] == []


def test_wrappers_suggest_routing_should_exclude_non_jp_market_accounts(
    client: TestClient,
):
    non_jp_market_resp = client.post(
        "/accounts",
        json={
            "name": "NISA Growth JPY US Market",
            "broker": "SBI",
            "account_type": "brokerage",
            "tax_wrapper": "nisa_growth",
            "currency": "JPY",
            "market": "US",
        },
    )
    assert non_jp_market_resp.status_code == 201

    routing_resp = client.post(
        "/wrappers/suggest-routing",
        json={"ticker": "AAPL", "total_amount": 300_000.0},
    )
    assert routing_resp.status_code == 200
    payload = routing_resp.json()
    assert payload["suggestions"] == []


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
