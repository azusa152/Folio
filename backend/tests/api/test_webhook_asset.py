"""Contract tests for asset management webhook actions."""

from unittest.mock import patch


class TestWebhookTransactions:
    """Tests for the 'transactions' action."""

    @patch(
        "application.messaging.webhook_service.list_transactions",
        return_value=[
            {"id": 1, "ticker": "AAPL", "transaction_type": "BUY", "quantity": 10},
        ],
    )
    def test_transactions_should_return_list(self, _mock, client):
        resp = client.post("/webhook", json={"action": "transactions"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "transactions" in body["data"]
        assert body["data"]["count"] == 1

    @patch(
        "application.messaging.webhook_service.list_transactions",
        return_value=[],
    )
    def test_transactions_with_ticker_filter(self, mock_list, client):
        resp = client.post(
            "/webhook",
            json={"action": "transactions", "params": {"ticker": "AAPL", "limit": "5"}},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        mock_list.assert_called_once()
        call_kwargs = mock_list.call_args
        assert call_kwargs.kwargs.get("ticker") == "AAPL"
        assert call_kwargs.kwargs.get("limit") == 5


class TestWebhookAddTransaction:
    """Tests for the 'add_transaction' action."""

    @patch(
        "application.messaging.webhook_service.create_transaction",
        return_value={"id": 1, "ticker": "AAPL", "transaction_type": "BUY"},
    )
    def test_add_transaction_happy_path(self, _mock, client):
        resp = client.post(
            "/webhook",
            json={
                "action": "add_transaction",
                "ticker": "AAPL",
                "params": {
                    "type": "BUY",
                    "quantity": "10",
                    "total_amount": "1500",
                    "date": "2025-06-01",
                },
            },
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True

    def test_add_transaction_missing_ticker(self, client):
        resp = client.post(
            "/webhook",
            json={
                "action": "add_transaction",
                "params": {
                    "type": "BUY",
                    "quantity": "10",
                    "total_amount": "1500",
                    "date": "2025-06-01",
                },
            },
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is False
        assert "ticker" in body["message"].lower()

    def test_add_transaction_missing_required_params(self, client):
        resp = client.post(
            "/webhook",
            json={
                "action": "add_transaction",
                "ticker": "AAPL",
                "params": {"type": "BUY"},
            },
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is False


class TestWebhookAccounts:
    """Tests for the 'accounts' action."""

    @patch(
        "application.messaging.webhook_service.get_account_summary",
        return_value=[
            {"id": 1, "name": "IB", "holdings_count": 5},
        ],
    )
    def test_accounts_should_return_summary(self, _mock, client):
        resp = client.post("/webhook", json={"action": "accounts"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "accounts" in body["data"]
        assert body["data"]["count"] == 1


class TestWebhookAnalytics:
    """Tests for the 'analytics' action."""

    @patch(
        "application.messaging.webhook_service.get_risk_metrics_svc",
        return_value={
            "annualized_return": 0.12,
            "annualized_volatility": 0.18,
            "sharpe_ratio": 0.44,
            "sortino_ratio": 0.55,
            "max_drawdown_pct": -0.15,
            "calmar_ratio": 0.8,
        },
    )
    def test_analytics_should_return_metrics(self, _mock, client):
        resp = client.post("/webhook", json={"action": "analytics"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "sharpe_ratio" in body["data"]
        assert "max_drawdown_pct" in body["data"]


class TestWebhookInsights:
    """Tests for the 'insights' action."""

    @patch(
        "application.messaging.webhook_service.get_portfolio_insights",
        return_value=[
            {
                "key": "insight.test",
                "severity": "info",
                "vars": {},
                "category": "general",
            },
        ],
    )
    def test_insights_should_return_list(self, _mock, client):
        resp = client.post("/webhook", json={"action": "insights"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "insights" in body["data"]
        assert body["data"]["count"] == 1


class TestWebhookHelpIncludesAssetActions:
    """Verify help action lists all new asset management actions."""

    def test_help_includes_new_actions(self, client):
        resp = client.post("/webhook", json={"action": "help"})

        assert resp.status_code == 200
        actions = resp.json()["data"]["actions"]
        for expected in [
            "transactions",
            "add_transaction",
            "accounts",
            "analytics",
            "insights",
        ]:
            assert expected in actions, f"Missing action: {expected}"
