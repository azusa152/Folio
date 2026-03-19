"""Tests for POST /webhook — AI agent unified entry point."""

from unittest.mock import patch

from domain.constants import WEBHOOK_ACTION_REGISTRY
from i18n import t


class TestWebhookHelp:
    """Tests for the 'help' action (discoverability)."""

    def test_help_should_return_all_actions(self, client):
        # Act
        resp = client.post("/webhook", json={"action": "help"})

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        actions = body["data"]["actions"]
        assert "help" in actions
        assert "summary" in actions
        assert "signals" in actions
        assert "scan" in actions
        assert "moat" in actions
        assert "alerts" in actions
        assert "add_stock" in actions

    def test_help_should_include_structured_descriptions(self, client):
        # Act
        resp = client.post("/webhook", json={"action": "help"})

        # Assert
        actions = resp.json()["data"]["actions"]
        for action_info in actions.values():
            assert isinstance(action_info, dict)
            assert "description" in action_info
            assert "requires_ticker" in action_info

    def test_help_should_always_include_data_even_in_concise_mode(self, client):
        """Discoverability must never be gated behind format."""
        # Act
        resp = client.post("/webhook", json={"action": "help", "format": "concise"})

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "data" in body
        assert "actions" in body["data"]
        assert "workflows" in body["data"]
        assert "model_hint" in body["data"]


class TestWebhookSummary:
    """Tests for the 'summary' action."""

    def test_summary_should_return_success(self, client):
        # Act
        resp = client.post("/webhook", json={"action": "summary"})

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert isinstance(body["message"], str)


class TestWebhookDashboard:
    """Tests for the 'dashboard' composite action."""

    def test_dashboard_should_return_summary_and_fear_greed(self, client):
        # Act
        resp = client.post("/webhook", json={"action": "dashboard"})

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert isinstance(body["message"], str)
        assert body["interpretation"] == t(
            "webhook.interpretation.dashboard_ready", lang="zh-TW"
        )
        assert "fear_greed" in body["data"]


class TestWebhookAnalyze:
    """Tests for the 'analyze' composite action."""

    def test_analyze_should_return_combined_data_with_ticker(self, client):
        # Act
        resp = client.post("/webhook", json={"action": "analyze", "ticker": "NVDA"})

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "NVDA" in body["message"]
        assert "signals" in body["data"]
        assert "moat" in body["data"]
        assert "fundamentals" in body["data"]

    def test_analyze_should_fail_without_ticker(self, client):
        # Act
        resp = client.post("/webhook", json={"action": "analyze"})

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is False
        assert "ticker" in body["message"]


class TestWebhookSignals:
    """Tests for the 'signals' action."""

    def test_signals_should_return_data_with_ticker(self, client):
        # Arrange — add a stock first
        client.post(
            "/ticker",
            json={"ticker": "NVDA", "category": "Growth", "thesis": "AI leader"},
        )

        # Act
        resp = client.post("/webhook", json={"action": "signals", "ticker": "NVDA"})

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "RSI" in body["message"]

    def test_signals_should_fail_without_ticker(self, client):
        # Act
        resp = client.post("/webhook", json={"action": "signals"})

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is False
        assert "ticker" in body["message"]


class TestWebhookScan:
    """Tests for the 'scan' action."""

    def test_scan_should_accept_background_job(self, client):
        # Act — mock run_scan so it doesn't actually run the scan in the background
        with patch("application.messaging.webhook_service.run_scan"):
            resp = client.post("/webhook", json={"action": "scan"})

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        expected_msg = t("webhook.scan_started", lang="zh-TW")
        assert body["message"] == expected_msg


class TestWebhookMoat:
    """Tests for the 'moat' action."""

    def test_moat_should_return_analysis_with_ticker(self, client):
        # Act
        resp = client.post("/webhook", json={"action": "moat", "ticker": "NVDA"})

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "NVDA" in body["message"]
        assert "護城河" in body["message"]

    def test_moat_should_fail_without_ticker(self, client):
        # Act
        resp = client.post("/webhook", json={"action": "moat"})

        # Assert
        body = resp.json()
        assert body["success"] is False


class TestWebhookAlerts:
    """Tests for the 'alerts' action."""

    def test_alerts_should_return_empty_for_new_stock(self, client):
        # Arrange
        client.post(
            "/ticker",
            json={"ticker": "AAPL", "category": "Moat", "thesis": "Ecosystem"},
        )

        # Act
        resp = client.post("/webhook", json={"action": "alerts", "ticker": "AAPL"})

        # Assert
        body = resp.json()
        assert body["success"] is True
        expected_msg = t("webhook.no_alerts", lang="zh-TW", ticker="AAPL")
        assert body["message"] == expected_msg

    def test_alerts_should_fail_without_ticker(self, client):
        # Act
        resp = client.post("/webhook", json={"action": "alerts"})

        # Assert
        body = resp.json()
        assert body["success"] is False


class TestWebhookAddStock:
    """Tests for the 'add_stock' action."""

    def test_add_stock_should_create_new_stock(self, client):
        # Act
        resp = client.post(
            "/webhook",
            json={
                "action": "add_stock",
                "params": {
                    "ticker": "AMD",
                    "category": "Growth",
                    "thesis": "ASIC competitor",
                    "tags": ["AI", "Semiconductor"],
                },
            },
        )

        # Assert
        body = resp.json()
        assert body["success"] is True
        assert "AMD" in body["message"]

    def test_add_stock_should_fail_for_duplicate(self, client):
        # Arrange
        client.post(
            "/webhook",
            json={
                "action": "add_stock",
                "params": {"ticker": "AMD", "category": "Growth", "thesis": "Test"},
            },
        )

        # Act
        resp = client.post(
            "/webhook",
            json={
                "action": "add_stock",
                "params": {
                    "ticker": "AMD",
                    "category": "Growth",
                    "thesis": "Duplicate",
                },
            },
        )

        # Assert
        body = resp.json()
        assert body["success"] is False

    def test_add_stock_should_fail_without_ticker(self, client):
        # Act
        resp = client.post("/webhook", json={"action": "add_stock", "params": {}})

        # Assert
        body = resp.json()
        assert body["success"] is False


class TestWebhookFXWatch:
    """Tests for the 'fx_watch' webhook action — AI agent entry point for FX alerts."""

    @patch("application.portfolio.fx_watch_service.log_notification_sent")
    @patch("application.portfolio.fx_watch_service.is_within_rate_limit")
    @patch("application.portfolio.fx_watch_service.send_telegram_message_dual")
    @patch("application.portfolio.fx_watch_service.get_forex_history_long")
    @patch("application.portfolio.fx_watch_service.is_notification_enabled")
    def test_fx_watch_should_return_success_with_counts(
        self,
        mock_notif,
        mock_history,
        mock_telegram,
        mock_rate_limit,
        _mock_log,
        client,
    ):
        # Arrange: create an FX watch config
        client.post(
            "/fx-watch",
            json={
                "base_currency": "USD",
                "quote_currency": "TWD",
                "recent_high_days": 5,
                "consecutive_increase_days": 2,
            },
        )
        mock_notif.return_value = True
        mock_rate_limit.return_value = True
        mock_history.return_value = [
            {"date": "2026-02-07", "close": 30.0},
            {"date": "2026-02-08", "close": 30.5},
            {"date": "2026-02-09", "close": 31.0},
            {"date": "2026-02-10", "close": 31.5},
        ]

        # Act
        resp = client.post("/webhook", json={"action": "fx_watch"})

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        expected_complete = t(
            "webhook.fx_watch_complete", total=1, triggered=1, sent=1, lang="zh-TW"
        )
        assert body["message"] == expected_complete
        assert body["data"]["total_watches"] == 1
        assert body["data"]["triggered_alerts"] == 1
        assert body["data"]["sent_alerts"] == 1

    def test_fx_watch_should_return_success_when_no_watches(self, client):
        # Act — no FX watch configs exist
        resp = client.post("/webhook", json={"action": "fx_watch"})

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["total_watches"] == 0
        assert body["data"]["triggered_alerts"] == 0
        assert body["data"]["sent_alerts"] == 0

    @patch(
        "application.messaging.webhook_service.send_fx_watch_alerts",
        side_effect=RuntimeError("DB connection lost"),
    )
    def test_fx_watch_should_return_failure_on_service_exception(
        self, _mock_alert, client
    ):
        # Act
        resp = client.post("/webhook", json={"action": "fx_watch"})

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is False
        expected_msg = t(
            "webhook.fx_watch_failed", lang="zh-TW", error="DB connection lost"
        )
        assert body["message"] == expected_msg


class TestWebhookStockSplits:
    """Tests for the 'stock_splits' webhook action."""

    @patch("application.messaging.webhook_service.check_splits")
    def test_stock_splits_should_return_success_with_summary(
        self, mock_check_splits, client
    ):
        mock_check_splits.return_value = {
            "checked_tickers": 2,
            "detected": 1,
            "auto_applied": 1,
            "events": [],
        }

        resp = client.post("/webhook", json={"action": "stock_splits"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["checked_tickers"] == 2
        assert body["data"]["detected"] == 1
        assert body["data"]["auto_applied"] == 1
        expected_msg = t(
            "webhook.stock_splits_summary",
            lang="zh-TW",
            checked=2,
            detected=1,
            auto_applied=1,
        )
        assert body["message"] == expected_msg

    @patch(
        "application.messaging.webhook_service.check_splits",
        side_effect=RuntimeError("split source unavailable"),
    )
    def test_stock_splits_should_return_failure_on_service_exception(
        self, _mock_check_splits, client
    ):
        resp = client.post("/webhook", json={"action": "stock_splits"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is False
        expected_msg = t(
            "webhook.stock_splits_failed",
            lang="zh-TW",
            error="split source unavailable",
        )
        assert body["message"] == expected_msg


class TestWebhookAcknowledgments:
    """Tests for drift/X-Ray acknowledgment webhook actions."""

    @patch("application.messaging.webhook_service.acknowledge_drift_alert")
    def test_acknowledge_drift_should_return_success(self, mock_ack, client):
        mock_ack.return_value = {
            "type": "drift",
            "key": "Growth",
            "acknowledged_value": 12.0,
            "acknowledged_at": "2026-03-19T00:00:00",
            "expires_at": "2026-06-17T00:00:00",
        }
        resp = client.post(
            "/webhook",
            json={"action": "acknowledge_drift", "params": {"category": "Growth"}},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["key"] == "Growth"

    @patch("application.messaging.webhook_service.acknowledge_xray_alert")
    def test_acknowledge_xray_should_return_success(self, mock_ack, client):
        mock_ack.return_value = {
            "type": "xray",
            "key": "AAPL",
            "acknowledged_value": 20.0,
            "acknowledged_at": "2026-03-19T00:00:00",
            "expires_at": "2026-06-17T00:00:00",
        }
        resp = client.post(
            "/webhook",
            json={"action": "acknowledge_xray", "params": {"symbol": "AAPL"}},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["key"] == "AAPL"


class TestWebhookDiscoverability:
    """Tests ensuring AI agent discoverability stays in sync with WEBHOOK_ACTION_REGISTRY."""

    def test_help_should_include_all_registry_actions(self, client):
        """Dynamic guard: every action in WEBHOOK_ACTION_REGISTRY must appear in help response."""
        # Act
        resp = client.post("/webhook", json={"action": "help"})

        # Assert
        assert resp.status_code == 200
        actions = resp.json()["data"]["actions"]
        for action_name in WEBHOOK_ACTION_REGISTRY:
            assert action_name in actions, f"Missing action in help: {action_name}"
        assert set(actions.keys()) == set(WEBHOOK_ACTION_REGISTRY.keys())

    @patch("application.portfolio.fx_watch_service.log_notification_sent")
    @patch("application.portfolio.fx_watch_service.is_within_rate_limit")
    @patch("application.portfolio.fx_watch_service.send_telegram_message_dual")
    @patch("application.portfolio.fx_watch_service.get_forex_history_long")
    @patch("application.portfolio.fx_watch_service.is_notification_enabled")
    def test_fx_watch_response_data_should_have_required_keys(
        self,
        mock_notif,
        mock_history,
        mock_telegram,
        mock_rate_limit,
        _mock_log,
        client,
    ):
        """Response schema contract test — ensures AI agent gets expected keys."""
        # Arrange
        mock_notif.return_value = True
        mock_rate_limit.return_value = True
        mock_history.return_value = [
            {"date": "2026-02-10", "close": 31.0},
            {"date": "2026-02-11", "close": 31.5},
        ]

        # Act
        resp = client.post("/webhook", json={"action": "fx_watch"})

        # Assert
        assert resp.status_code == 200
        data = resp.json()["data"]
        required_keys = {"total_watches", "triggered_alerts", "sent_alerts", "alerts"}
        assert required_keys == set(data.keys()), (
            f"Response data keys mismatch: expected {required_keys}, got {set(data.keys())}"
        )


class TestWebhookQuota:
    """Tests for the 'quota' webhook action."""

    def test_quota_should_return_quota_payload(self, client):
        # Act
        resp = client.post("/webhook", json={"action": "quota"})

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "data" in body
        data = body["data"]
        assert "year" in data
        assert "as_of" in data
        assert "restoration_policy" in data
        assert "quotas" in data
        assert "nisa_tsumitate" in data["quotas"]
        assert "nisa_growth" in data["quotas"]
        assert "restoration_forecast" in data

    def test_quota_should_fail_for_invalid_year(self, client):
        # Act
        resp = client.post(
            "/webhook", json={"action": "quota", "params": {"year": "x"}}
        )

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is False
        assert body.get("error_code") == "INVALID_INPUT"


class TestWebhookUnknownAction:
    """Tests for unsupported actions."""

    def test_unknown_action_should_return_error(self, client):
        # Act
        resp = client.post("/webhook", json={"action": "nonexistent"})

        # Assert
        body = resp.json()
        assert body["success"] is False
        supported = ", ".join(sorted(WEBHOOK_ACTION_REGISTRY.keys()))
        expected_msg = t(
            "webhook.unsupported_action",
            action="nonexistent",
            supported=supported,
            lang="zh-TW",
        )
        assert body["message"] == expected_msg


class TestWebhookResponseContract:
    """Contract tests for webhook response structure and backward compatibility."""

    def test_default_response_includes_data(self, client):
        """Default format (detailed) must include data for backward compat."""
        # Act — no format specified
        resp = client.post("/webhook", json={"action": "help"})

        # Assert
        body = resp.json()
        assert "data" in body, (
            "Default response must include 'data' for backward compat"
        )

    def test_concise_omits_data_for_regular_actions(self, client):
        """Concise mode should omit data to save tokens."""
        # Act
        resp = client.post("/webhook", json={"action": "summary", "format": "concise"})

        # Assert
        body = resp.json()
        assert "data" not in body or body["data"] == {}

    def test_all_responses_include_interpretation(self, client):
        """Every webhook response should include the interpretation field."""
        # Act
        resp = client.post("/webhook", json={"action": "summary"})

        # Assert
        body = resp.json()
        assert "interpretation" in body
        assert isinstance(body["interpretation"], str)

    def test_help_structured_actions_have_required_keys(self, client):
        """Help action metadata must be machine-readable dicts."""
        # Act
        resp = client.post("/webhook", json={"action": "help"})

        # Assert
        actions = resp.json()["data"]["actions"]
        for name, meta in actions.items():
            assert isinstance(meta, dict), f"Action '{name}' should be a dict"
            assert "description" in meta, f"Action '{name}' missing 'description'"
            assert "requires_ticker" in meta, (
                f"Action '{name}' missing 'requires_ticker'"
            )
            assert isinstance(meta["requires_ticker"], bool)

    def test_help_workflows_present(self, client):
        """Help must include workflow suggestions."""
        # Act
        resp = client.post("/webhook", json={"action": "help"})

        # Assert
        data = resp.json()["data"]
        assert "workflows" in data
        assert len(data["workflows"]) > 0

    def test_help_model_hint_present(self, client):
        """Help must include a model hint for cost-aware routing."""
        # Act
        resp = client.post("/webhook", json={"action": "help"})

        # Assert
        data = resp.json()["data"]
        assert "model_hint" in data
        assert isinstance(data["model_hint"], str)
