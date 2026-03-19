"""Tests for holding analysis routes in ledger mode."""

HOLDING_PAYLOAD = {
    "ticker": "NVDA",
    "transaction_type": "BUY",
    "quantity": 10,
    "price": 100.0,
    "total_amount": 1000.0,
    "currency": "USD",
    "transaction_date": "2026-03-11",
}

_PROFILE_PAYLOAD = {"config": {"Growth": 100}, "home_currency": "USD"}


def _create_account(client) -> int:
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


def _seed_equity_holding(client, ticker: str = "NVDA", quantity: float = 10) -> int:
    account_id = _create_account(client)
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
    assert deposit_resp.status_code == 201
    buy_resp = client.post(
        "/transactions",
        json={
            **HOLDING_PAYLOAD,
            "account_id": account_id,
            "ticker": ticker,
            "quantity": quantity,
        },
    )
    assert buy_resp.status_code == 201
    return account_id


class TestListHoldings:
    """Tests for GET /holdings."""

    def test_list_should_return_empty_initially(self, client):
        resp = client.get("/holdings")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_should_return_holdings_from_transactions(self, client):
        _seed_equity_holding(client, ticker="NVDA")
        resp = client.get("/holdings")
        assert resp.status_code == 200
        tickers = {item["ticker"] for item in resp.json()}
        assert "NVDA" in tickers

    def test_list_should_exclude_zero_quantity_stock_positions(self, client):
        account_id = _seed_equity_holding(client, ticker="AAPL", quantity=2)
        sell_resp = client.post(
            "/transactions",
            json={
                "account_id": account_id,
                "ticker": "AAPL",
                "transaction_type": "SELL",
                "quantity": 2,
                "price": 110.0,
                "total_amount": 220.0,
                "currency": "USD",
                "transaction_date": "2026-03-12",
            },
        )
        assert sell_resp.status_code == 201

        resp = client.get("/holdings")
        assert resp.status_code == 200
        tickers = {item["ticker"] for item in resp.json()}
        assert "AAPL" not in tickers


class TestRebalanceResponse:
    """Contract tests for GET /rebalance."""

    def test_should_include_geographic_and_asset_class_allocation(self, client):
        _seed_equity_holding(client, ticker="NVDA")
        client.post("/profiles", json=_PROFILE_PAYLOAD)

        resp = client.get("/rebalance")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["geographic_allocation"], dict)
        assert isinstance(data["asset_class_allocation"], dict)
        assert "US" in data["geographic_allocation"]
        assert "Equity" in data["asset_class_allocation"]

    def test_should_include_non_usd_cash_currency_region_in_geographic_allocation(
        self, client
    ):
        account_id = _seed_equity_holding(client, ticker="NVDA")
        sgd_deposit = client.post(
            "/transactions",
            json={
                "account_id": account_id,
                "ticker": "SGD",
                "transaction_type": "DEPOSIT",
                "quantity": 1,
                "total_amount": 1000.0,
                "currency": "SGD",
                "transaction_date": "2026-03-12",
            },
        )
        assert sgd_deposit.status_code == 201
        profile_resp = client.post("/profiles", json=_PROFILE_PAYLOAD)
        assert profile_resp.status_code in (200, 201)

        resp = client.get("/rebalance")
        assert resp.status_code == 200
        geographic = resp.json()["geographic_allocation"]
        assert "US" in geographic
        assert "SG" in geographic
        assert geographic["US"] > 0
        assert geographic["SG"] > 0

    def test_holdings_detail_should_split_same_ticker_by_account(self, client):
        account_a = _seed_equity_holding(client, ticker="AAPL", quantity=2)
        account_b = _seed_equity_holding(client, ticker="AAPL", quantity=3)
        profile_resp = client.post("/profiles", json=_PROFILE_PAYLOAD)
        assert profile_resp.status_code in (200, 201)

        rebalance_resp = client.get("/rebalance")
        assert rebalance_resp.status_code == 200
        details = [
            row
            for row in rebalance_resp.json()["holdings_detail"]
            if row["ticker"] == "AAPL"
        ]
        assert len(details) == 2
        assert {row["account_id"] for row in details} == {account_a, account_b}

    def test_should_hide_tiny_float_residue_positions_in_holdings_and_rebalance(
        self, client
    ):
        account_id = _seed_equity_holding(client, ticker="AAPL", quantity=0.1)
        buy_two_resp = client.post(
            "/transactions",
            json={
                "account_id": account_id,
                "ticker": "AAPL",
                "transaction_type": "BUY",
                "quantity": 0.2,
                "price": 100.0,
                "total_amount": 20.0,
                "currency": "USD",
                "transaction_date": "2026-03-12",
            },
        )
        sell_resp = client.post(
            "/transactions",
            json={
                "account_id": account_id,
                "ticker": "AAPL",
                "transaction_type": "SELL",
                "quantity": 0.3,
                "price": 105.0,
                "total_amount": 31.5,
                "currency": "USD",
                "transaction_date": "2026-03-13",
            },
        )
        profile_resp = client.post("/profiles", json=_PROFILE_PAYLOAD)
        assert buy_two_resp.status_code == 201
        assert sell_resp.status_code == 201
        assert profile_resp.status_code in (200, 201)

        holdings_resp = client.get("/holdings")
        rebalance_resp = client.get("/rebalance")
        assert holdings_resp.status_code == 200
        assert rebalance_resp.status_code == 200
        holdings_tickers = {item["ticker"] for item in holdings_resp.json()}
        rebalance_tickers = {
            row["ticker"] for row in rebalance_resp.json()["holdings_detail"]
        }
        assert "AAPL" not in holdings_tickers
        assert "AAPL" not in rebalance_tickers


class TestTriggerXrayAlert:
    """Tests for POST /rebalance/xray-alert."""

    def test_should_return_200_with_warnings_list(self, client):
        _seed_equity_holding(client)
        client.post("/profiles", json=_PROFILE_PAYLOAD)

        resp = client.post("/rebalance/xray-alert")
        assert resp.status_code == 200
        data = resp.json()
        assert "warnings" in data
        assert "message" in data
        assert isinstance(data["warnings"], list)

    def test_ack_should_return_200_when_weight_provided(self, client):
        _seed_equity_holding(client)
        client.post("/profiles", json=_PROFILE_PAYLOAD)
        resp = client.post("/rebalance/xray-alert/ack?symbol=NVDA&total_weight_pct=22")
        assert resp.status_code == 200
        assert "message" in resp.json()


class TestTriggerDriftAlert:
    """Tests for POST /rebalance/drift-alert."""

    def test_should_return_200_with_alerts_list(self, client):
        _seed_equity_holding(client)
        client.post("/profiles", json=_PROFILE_PAYLOAD)
        resp = client.post("/rebalance/drift-alert")
        assert resp.status_code == 200
        data = resp.json()
        assert "alerts" in data
        assert "message" in data
        assert isinstance(data["alerts"], list)

    def test_ack_should_return_200_when_drift_pct_provided(self, client):
        _seed_equity_holding(client)
        client.post("/profiles", json=_PROFILE_PAYLOAD)
        resp = client.post("/rebalance/drift-alert/ack?category=Growth&drift_pct=12")
        assert resp.status_code == 200
        assert "message" in resp.json()

    def test_ack_should_return_422_with_invalid_payload(self, client):
        resp = client.post("/rebalance/drift-alert/ack?category=")
        assert resp.status_code == 422


class TestCurrencyExposure:
    """Contract tests for GET /currency-exposure."""

    def test_should_allow_home_currency_override_via_query(self, client):
        resp = client.get("/currency-exposure?home_currency=JPY")
        assert resp.status_code == 200
        assert resp.json()["home_currency"] == "JPY"

    def test_should_normalize_home_currency_to_uppercase(self, client):
        resp = client.get("/currency-exposure?home_currency=usd")
        assert resp.status_code == 200
        assert resp.json()["home_currency"] == "USD"

    def test_should_return_422_for_unsupported_home_currency(self, client):
        resp = client.get("/currency-exposure?home_currency=ABC")
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert detail["error_code"] == "INVALID_INPUT"

    def test_should_include_fx_impact_breakdown_fields(self, client):
        resp = client.get("/currency-exposure?home_currency=USD")
        assert resp.status_code == 200
        data = resp.json()
        assert "net_cash_impact" in data
        assert "net_investment_impact" in data
        assert isinstance(data["net_cash_impact"], (int, float))
        assert isinstance(data["net_investment_impact"], (int, float))
        assert "fx_movements" in data
        assert isinstance(data["fx_movements"], list)
        for movement in data["fx_movements"]:
            assert "impact_cash_home_value" in movement
            assert "impact_investment_home_value" in movement
            assert isinstance(movement["impact_cash_home_value"], (int, float))
            assert isinstance(movement["impact_investment_home_value"], (int, float))


class TestTriggerFxAlert:
    """Tests for POST /currency-exposure/alert."""

    def test_should_return_200_with_alerts_list_when_no_holdings(self, client):
        resp = client.post("/currency-exposure/alert")
        assert resp.status_code == 200
        data = resp.json()
        assert "alerts" in data
        assert "message" in data
        assert isinstance(data["alerts"], list)

    def test_should_return_200_with_alerts_list_when_holdings_present(self, client):
        _seed_equity_holding(client)
        resp = client.post("/currency-exposure/alert")
        assert resp.status_code == 200
        assert "alerts" in resp.json()


class TestWithdraw:
    """Tests for POST /withdraw."""

    def test_should_return_withdraw_plan_with_holdings_and_profile(self, client):
        _seed_equity_holding(client)
        client.post("/profiles", json=_PROFILE_PAYLOAD)

        resp = client.post(
            "/withdraw",
            json={"target_amount": 1000, "display_currency": "USD"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "recommendations" in data

    def test_should_return_404_when_no_active_profile(self, client):
        _seed_equity_holding(client)
        resp = client.post(
            "/withdraw",
            json={"target_amount": 1000, "display_currency": "USD"},
        )
        assert resp.status_code == 404
