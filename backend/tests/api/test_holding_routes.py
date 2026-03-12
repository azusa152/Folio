"""Tests for holding management routes (CRUD + import/export + rebalance)."""

from typing import ClassVar

HOLDING_PAYLOAD = {
    "ticker": "NVDA",
    "category": "Growth",
    "quantity": 10,
    "cost_basis": 100.0,
    "broker": "Firstrade",
    "currency": "USD",
    "account_type": "US",
    "is_cash": False,
}

CASH_PAYLOAD = {
    "currency": "TWD",
    "amount": 50000,
    "broker": "玉山",
    "account_type": "TW",
}


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


def _create_holding(client, payload=None, account_id=None):
    """Helper: create a holding and return its JSON body."""
    resolved_account_id = account_id or _create_account(client)
    holding_payload = {
        **(payload or HOLDING_PAYLOAD),
        "account_id": (
            (payload or HOLDING_PAYLOAD).get("account_id", resolved_account_id)
        ),
    }
    resp = client.post("/holdings", json=holding_payload)
    assert resp.status_code == 200
    return resp.json()


# ---------------------------------------------------------------------------
# Holdings CRUD
# ---------------------------------------------------------------------------


class TestCreateHolding:
    """Tests for POST /holdings."""

    def test_create_holding_should_return_created_holding(self, client):
        # Act
        body = _create_holding(client)

        # Assert
        assert body["ticker"] == "NVDA"
        assert body["category"] == "Growth"
        assert body["quantity"] == 10
        assert body["is_cash"] is False

    def test_create_holding_should_return_422_when_missing_fields(self, client):
        # Act — missing required 'ticker'
        resp = client.post("/holdings", json={"category": "Growth", "quantity": 5})

        # Assert
        assert resp.status_code == 422


class TestCreateCashHolding:
    """Tests for POST /holdings/cash."""

    def test_create_cash_should_return_cash_holding(self, client):
        # Act
        account_id = _create_account(client)
        resp = client.post(
            "/holdings/cash", json={**CASH_PAYLOAD, "account_id": account_id}
        )

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["ticker"] == "TWD"
        assert body["is_cash"] is True
        assert body["quantity"] == 50000

    def test_create_cash_should_return_422_when_missing_account(self, client):
        # Act
        resp = client.post("/holdings/cash", json=CASH_PAYLOAD)

        # Assert
        assert resp.status_code == 422

    def test_create_cash_should_return_422_when_missing_currency(self, client):
        # Act
        account_id = _create_account(client)
        resp = client.post(
            "/holdings/cash", json={"amount": 1000, "account_id": account_id}
        )

        # Assert
        assert resp.status_code == 422


class TestListHoldings:
    """Tests for GET /holdings."""

    def test_list_should_return_empty_initially(self, client):
        # Act
        resp = client.get("/holdings")

        # Assert
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_should_return_added_holdings(self, client):
        # Arrange
        _create_holding(client)

        # Act
        resp = client.get("/holdings")

        # Assert
        assert resp.status_code == 200
        tickers = {item["ticker"] for item in resp.json()}
        assert tickers == {"USD", "NVDA"}


class TestUpdateHolding:
    """Tests for PUT /holdings/{holding_id}."""

    def test_update_should_modify_holding(self, client):
        # Arrange
        created = _create_holding(client)
        holding_id = created["id"]

        # Act
        updated_payload = {**HOLDING_PAYLOAD, "quantity": 20, "cost_basis": 150.0}
        resp = client.put(f"/holdings/{holding_id}", json=updated_payload)

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["quantity"] == 20
        assert body["cost_basis"] == 150.0

    def test_update_should_return_404_for_nonexistent_id(self, client):
        # Act
        account_id = _create_account(client)
        resp = client.put(
            "/holdings/99999", json={**HOLDING_PAYLOAD, "account_id": account_id}
        )

        # Assert
        assert resp.status_code == 404
        assert resp.json()["detail"]["error_code"] == "HOLDING_NOT_FOUND"

    def test_update_should_return_404_when_account_not_found(self, client):
        # Arrange
        created = _create_holding(client)
        holding_id = created["id"]

        # Act
        resp = client.put(f"/holdings/{holding_id}", json={"account_id": 99999})

        # Assert
        assert resp.status_code == 404
        assert resp.json()["detail"]["error_code"] == "ACCOUNT_NOT_FOUND"

    def test_update_should_return_422_when_account_is_null(self, client):
        # Arrange
        created = _create_holding(client)
        holding_id = created["id"]

        # Act
        resp = client.put(f"/holdings/{holding_id}", json={"account_id": None})

        # Assert
        assert resp.status_code == 422


class TestDeleteHolding:
    """Tests for DELETE /holdings/{holding_id}."""

    def test_delete_should_remove_holding(self, client):
        # Arrange
        created = _create_holding(client)
        holding_id = created["id"]

        # Act
        resp = client.delete(f"/holdings/{holding_id}")

        # Assert
        assert resp.status_code == 200
        assert "NVDA" in resp.json()["message"]

        # Verify deletion
        resp2 = client.get("/holdings")
        assert resp2.status_code == 200
        tickers = {item["ticker"] for item in resp2.json()}
        assert "NVDA" not in tickers

    def test_delete_should_return_404_for_nonexistent_id(self, client):
        # Act
        resp = client.delete("/holdings/99999")

        # Assert
        assert resp.status_code == 404
        assert resp.json()["detail"]["error_code"] == "HOLDING_NOT_FOUND"


# ---------------------------------------------------------------------------
# Holdings Import / Export
# ---------------------------------------------------------------------------


class TestExportHoldings:
    """Tests for GET /holdings/export."""

    def test_export_should_return_empty_list_when_no_holdings(self, client):
        # Act
        resp = client.get("/holdings/export")

        # Assert
        assert resp.status_code == 200
        assert resp.json() == []

    def test_export_should_return_all_holdings(self, client):
        # Arrange
        account_id = _create_account(client)
        _create_holding(client, account_id=account_id)
        client.post("/holdings/cash", json={**CASH_PAYLOAD, "account_id": account_id})

        # Act
        resp = client.get("/holdings/export")

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        tickers = {item["ticker"] for item in data}
        assert tickers == {"USD", "NVDA", "TWD"}


class TestImportHoldings:
    """Tests for POST /holdings/import."""

    def test_import_should_replace_all_holdings(self, client):
        # Arrange — create initial holding
        created = _create_holding(client)
        account_id = created["account_id"]

        import_data = {
            "mode": "replace_all",
            "account_id": account_id,
            "items": [
                {
                    "ticker": "AAPL",
                    "category": "Growth",
                    "quantity": 5,
                    "currency": "USD",
                },
                {
                    "ticker": "GOOGL",
                    "category": "Moat",
                    "quantity": 3,
                    "currency": "USD",
                },
            ],
        }

        # Act
        resp = client.post("/holdings/import", json=import_data)

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["imported"] == 2
        assert body["errors"] == []

        # Verify old holdings replaced
        holdings = client.get("/holdings").json()
        tickers = {h["ticker"] for h in holdings}
        assert "NVDA" not in tickers
        assert tickers == {"AAPL", "GOOGL"}

    def test_import_should_handle_empty_list(self, client):
        # Arrange — create initial holding
        _create_holding(client)

        # Act — import empty list (clears everything)
        resp = client.post(
            "/holdings/import", json={"mode": "replace_all", "items": []}
        )

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["imported"] == 0

        # Verify all cleared
        holdings = client.get("/holdings").json()
        assert len(holdings) == 0

    def test_import_replace_account_should_only_replace_selected_account(self, client):
        # Arrange
        account_a = client.post(
            "/accounts",
            json={
                "name": "IB US",
                "broker": "Interactive Brokers",
                "account_type": "brokerage",
                "currency": "USD",
            },
        )
        account_b = client.post(
            "/accounts",
            json={
                "name": "Futu HK",
                "broker": "Futu",
                "account_type": "brokerage",
                "currency": "USD",
            },
        )
        assert account_a.status_code == 201
        assert account_b.status_code == 201
        account_a_id = account_a.json()["id"]
        account_b_id = account_b.json()["id"]

        client.post(
            "/holdings",
            json={**HOLDING_PAYLOAD, "ticker": "AAPL", "account_id": account_a_id},
        )
        client.post(
            "/holdings",
            json={**HOLDING_PAYLOAD, "ticker": "MSFT", "account_id": account_b_id},
        )

        # Act
        resp = client.post(
            "/holdings/import",
            json={
                "mode": "replace_account",
                "account_id": account_b_id,
                "items": [
                    {
                        "ticker": "GOOGL",
                        "category": "Growth",
                        "quantity": 9,
                        "currency": "USD",
                    }
                ],
            },
        )

        # Assert
        assert resp.status_code == 200
        holdings = client.get("/holdings").json()
        ticker_to_account = {
            holding["ticker"]: holding["account_id"] for holding in holdings
        }
        assert ticker_to_account["AAPL"] == account_a_id
        assert "MSFT" not in ticker_to_account
        assert ticker_to_account["GOOGL"] == account_b_id

    def test_import_append_should_keep_existing_holdings(self, client):
        # Arrange
        created = _create_holding(client)
        account_id = created["account_id"]

        # Act
        resp = client.post(
            "/holdings/import",
            json={
                "mode": "append",
                "account_id": account_id,
                "items": [
                    {
                        "ticker": "QQQ",
                        "category": "Growth",
                        "quantity": 7,
                        "currency": "USD",
                    }
                ],
            },
        )

        # Assert
        assert resp.status_code == 200
        holdings = client.get("/holdings").json()
        tickers = {holding["ticker"] for holding in holdings}
        assert tickers == {"USD", "NVDA", "QQQ"}

    def test_import_should_return_422_when_missing_account_assignment(self, client):
        # Act
        resp = client.post(
            "/holdings/import",
            json={
                "mode": "append",
                "items": [
                    {
                        "ticker": "QQQ",
                        "category": "Growth",
                        "quantity": 7,
                        "currency": "USD",
                    }
                ],
            },
        )

        # Assert
        assert resp.status_code == 422

    def test_import_should_return_404_when_account_not_found(self, client):
        # Act
        resp = client.post(
            "/holdings/import",
            json={
                "mode": "append",
                "account_id": 99999,
                "items": [
                    {
                        "ticker": "QQQ",
                        "category": "Growth",
                        "quantity": 7,
                        "currency": "USD",
                    }
                ],
            },
        )

        # Assert
        assert resp.status_code == 404
        assert resp.json()["detail"]["error_code"] == "ACCOUNT_NOT_FOUND"


# ---------------------------------------------------------------------------
# X-Ray Alert
# ---------------------------------------------------------------------------

_PROFILE_PAYLOAD = {"config": {"Growth": 100}, "home_currency": "USD"}


class TestRebalanceResponse:
    """Contract tests for GET /rebalance — verify response shape includes allocation keys."""

    def test_should_include_geographic_and_asset_class_allocation(self, client):
        # Arrange — NVDA is a US stock in the Growth category
        _create_holding(client)
        client.post("/profiles", json=_PROFILE_PAYLOAD)

        # Act
        resp = client.get("/rebalance")

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["geographic_allocation"], dict)
        assert isinstance(data["asset_class_allocation"], dict)
        assert "US" in data["geographic_allocation"]
        assert data["geographic_allocation"]["US"] > 0
        assert "Equity" in data["asset_class_allocation"]
        assert data["asset_class_allocation"]["Equity"] > 0


class TestTriggerXrayAlert:
    """Tests for POST /rebalance/xray-alert."""

    def test_should_return_200_with_warnings_list(self, client):
        # Arrange — holding + active profile
        _create_holding(client)
        client.post("/profiles", json=_PROFILE_PAYLOAD)

        # Act
        resp = client.post("/rebalance/xray-alert")

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert "warnings" in data
        assert "message" in data
        assert isinstance(data["warnings"], list)


# ---------------------------------------------------------------------------
# FX Alert
# ---------------------------------------------------------------------------


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
        _create_holding(client)
        resp = client.post("/currency-exposure/alert")
        assert resp.status_code == 200
        assert "alerts" in resp.json()


# ---------------------------------------------------------------------------
# Smart Withdrawal
# ---------------------------------------------------------------------------


class TestWithdraw:
    """Tests for POST /withdraw."""

    def test_should_return_withdraw_plan_with_holdings_and_profile(self, client):
        # Arrange
        _create_holding(client)
        client.post("/profiles", json=_PROFILE_PAYLOAD)

        # Act
        resp = client.post(
            "/withdraw",
            json={"target_amount": 1000, "display_currency": "USD"},
        )

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert "recommendations" in data

    def test_should_return_404_when_no_active_profile(self, client):
        # No profile configured → StockNotFoundError → 404
        _create_holding(client)
        resp = client.post(
            "/withdraw",
            json={"target_amount": 1000, "display_currency": "USD"},
        )
        assert resp.status_code == 404


class TestHoldingImportSchemaContract:
    """Guard against schema drift that can break holdings import/export."""

    AUTO_FIELDS: ClassVar[set[str]] = {
        "id",
        "user_id",
        "updated_at",
        "purchase_fx_rate",
    }

    def test_import_schema_covers_all_required_holding_fields(self):
        from api.schemas.portfolio import HoldingImportItem
        from domain.entities import Holding

        missing: list[str] = []
        for name, field_info in Holding.model_fields.items():
            if name in self.AUTO_FIELDS:
                continue
            is_required = field_info.is_required()
            if is_required and name not in HoldingImportItem.model_fields:
                missing.append(name)

        assert missing == [], (
            f"Holding has required fields not covered by HoldingImportItem: {missing}. "
            "Either add them to HoldingImportItem or provide defaults in Holding."
        )

    def test_export_roundtrip_matches_import_schema(self):
        from api.schemas.portfolio import HoldingExportItem, HoldingImportItem

        export_fields = set(HoldingExportItem.model_fields.keys())
        import_required = {
            name
            for name, info in HoldingImportItem.model_fields.items()
            if info.is_required()
        }
        missing = import_required - export_fields
        assert missing == set(), (
            f"HoldingImportItem requires fields not in HoldingExportItem: {missing}. "
            "Export/import roundtrip would fail."
        )
