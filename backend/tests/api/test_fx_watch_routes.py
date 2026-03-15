"""Tests for FX Watch API routes."""

from unittest.mock import patch

from fastapi.testclient import TestClient


class TestFXWatchCRUD:
    """Tests for FX Watch CRUD operations."""

    def test_create_fx_watch_config(self, client: TestClient):
        # Arrange
        payload = {
            "base_currency": "USD",
            "quote_currency": "TWD",
            "recent_high_days": 30,
            "consecutive_increase_days": 3,
            "alert_on_recent_high": True,
            "alert_on_consecutive_increase": True,
            "reminder_interval_hours": 24,
        }

        # Act
        response = client.post("/fx-watch", json=payload)

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["base_currency"] == "USD"
        assert data["quote_currency"] == "TWD"
        assert data["recent_high_days"] == 30
        assert data["consecutive_increase_days"] == 3
        assert data["alert_on_recent_high"] is True
        assert data["alert_on_consecutive_increase"] is True
        assert data["reminder_interval_hours"] == 24
        assert data["is_active"] is True
        assert "id" in data

    def test_create_fx_watch_config_with_target_fields(self, client: TestClient):
        payload = {
            "base_currency": "USD",
            "quote_currency": "JPY",
            "target_rate": 150.0,
            "target_direction": "below",
        }

        response = client.post("/fx-watch", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["target_rate"] == 150.0
        assert data["target_direction"] == "below"

    def test_get_all_fx_watch_configs(self, client: TestClient):
        # Arrange: create two configs
        client.post(
            "/fx-watch",
            json={
                "base_currency": "USD",
                "quote_currency": "TWD",
            },
        )
        client.post(
            "/fx-watch",
            json={
                "base_currency": "EUR",
                "quote_currency": "TWD",
            },
        )

        # Act
        response = client.get("/fx-watch")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["base_currency"] in ["USD", "EUR"]
        assert data[1]["base_currency"] in ["USD", "EUR"]

    def test_get_active_fx_watch_configs_only(self, client: TestClient):
        # Arrange: create two configs, deactivate one
        create_response = client.post(
            "/fx-watch",
            json={
                "base_currency": "USD",
                "quote_currency": "TWD",
            },
        )
        watch_id = create_response.json()["id"]

        client.post(
            "/fx-watch",
            json={
                "base_currency": "EUR",
                "quote_currency": "TWD",
            },
        )

        # Deactivate first watch
        client.patch(f"/fx-watch/{watch_id}", json={"is_active": False})

        # Act
        response = client.get("/fx-watch?active_only=true")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["base_currency"] == "EUR"
        assert data[0]["is_active"] is True

    def test_update_fx_watch_config(self, client: TestClient):
        # Arrange
        create_response = client.post(
            "/fx-watch",
            json={
                "base_currency": "USD",
                "quote_currency": "TWD",
            },
        )
        watch_id = create_response.json()["id"]

        # Act
        update_response = client.patch(
            f"/fx-watch/{watch_id}",
            json={
                "recent_high_days": 60,
                "consecutive_increase_days": 5,
                "is_active": False,
            },
        )

        # Assert
        assert update_response.status_code == 200
        data = update_response.json()
        assert data["id"] == watch_id
        assert data["recent_high_days"] == 60
        assert data["consecutive_increase_days"] == 5
        assert data["is_active"] is False

    def test_update_should_allow_clearing_target_fields(self, client: TestClient):
        create_response = client.post(
            "/fx-watch",
            json={
                "base_currency": "USD",
                "quote_currency": "JPY",
                "target_rate": 150.0,
                "target_direction": "below",
            },
        )
        watch_id = create_response.json()["id"]

        clear_response = client.patch(
            f"/fx-watch/{watch_id}",
            json={"target_rate": None, "target_direction": None},
        )
        assert clear_response.status_code == 200
        cleared = clear_response.json()
        assert cleared["target_rate"] is None
        assert cleared["target_direction"] is None

    def test_update_without_target_fields_should_preserve_existing_target(
        self, client: TestClient
    ):
        create_response = client.post(
            "/fx-watch",
            json={
                "base_currency": "USD",
                "quote_currency": "JPY",
                "target_rate": 150.0,
                "target_direction": "below",
            },
        )
        watch_id = create_response.json()["id"]

        update_response = client.patch(
            f"/fx-watch/{watch_id}",
            json={"recent_high_days": 45},
        )
        assert update_response.status_code == 200
        updated = update_response.json()
        assert updated["recent_high_days"] == 45
        assert updated["target_rate"] == 150.0
        assert updated["target_direction"] == "below"

    def test_update_nonexistent_watch_returns_404(self, client: TestClient):
        # Act
        response = client.patch(
            "/fx-watch/9999",
            json={"is_active": False},
        )

        # Assert
        assert response.status_code == 404
        detail = response.json()["detail"]
        assert detail["error_code"] == "FX_WATCH_NOT_FOUND"
        assert "not found" in detail["detail"].lower()

    def test_delete_fx_watch_config(self, client: TestClient):
        # Arrange
        create_response = client.post(
            "/fx-watch",
            json={
                "base_currency": "USD",
                "quote_currency": "TWD",
            },
        )
        watch_id = create_response.json()["id"]

        # Act
        delete_response = client.delete(f"/fx-watch/{watch_id}")

        # Assert
        assert delete_response.status_code == 200
        assert "deleted successfully" in delete_response.json()["message"]

        # Verify deleted
        get_response = client.get("/fx-watch")
        assert len(get_response.json()) == 0

    def test_delete_nonexistent_watch_returns_404(self, client: TestClient):
        # Act
        response = client.delete("/fx-watch/9999")

        # Assert
        assert response.status_code == 404
        detail = response.json()["detail"]
        assert detail["error_code"] == "FX_WATCH_NOT_FOUND"
        assert "not found" in detail["detail"].lower()

    def test_create_with_only_recent_high_enabled(self, client: TestClient):
        """Create config with only recent high toggle enabled."""
        # Arrange
        payload = {
            "base_currency": "USD",
            "quote_currency": "TWD",
            "alert_on_recent_high": True,
            "alert_on_consecutive_increase": False,
        }

        # Act
        response = client.post("/fx-watch", json=payload)

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["alert_on_recent_high"] is True
        assert data["alert_on_consecutive_increase"] is False

    def test_create_with_only_consecutive_enabled(self, client: TestClient):
        """Create config with only consecutive increase toggle enabled."""
        # Arrange
        payload = {
            "base_currency": "EUR",
            "quote_currency": "JPY",
            "alert_on_recent_high": False,
            "alert_on_consecutive_increase": True,
        }

        # Act
        response = client.post("/fx-watch", json=payload)

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["alert_on_recent_high"] is False
        assert data["alert_on_consecutive_increase"] is True

    def test_create_with_both_toggles_disabled(self, client: TestClient):
        """Create config with both toggles disabled."""
        # Arrange
        payload = {
            "base_currency": "GBP",
            "quote_currency": "USD",
            "alert_on_recent_high": False,
            "alert_on_consecutive_increase": False,
        }

        # Act
        response = client.post("/fx-watch", json=payload)

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["alert_on_recent_high"] is False
        assert data["alert_on_consecutive_increase"] is False

    def test_update_toggle_flags(self, client: TestClient):
        """Update toggle flags via PATCH."""
        # Arrange: Create config with defaults
        create_resp = client.post(
            "/fx-watch",
            json={
                "base_currency": "USD",
                "quote_currency": "TWD",
            },
        )
        watch_id = create_resp.json()["id"]

        # Act: Update toggles
        update_resp = client.patch(
            f"/fx-watch/{watch_id}",
            json={
                "alert_on_recent_high": False,
                "alert_on_consecutive_increase": True,
            },
        )

        # Assert
        assert update_resp.status_code == 200
        data = update_resp.json()
        assert data["alert_on_recent_high"] is False
        assert data["alert_on_consecutive_increase"] is True

    def test_defaults_when_toggles_not_specified(self, client: TestClient):
        """Verify default toggle values when not explicitly provided."""
        # Arrange: Create config without specifying toggles
        payload = {
            "base_currency": "USD",
            "quote_currency": "CNY",
        }

        # Act
        response = client.post("/fx-watch", json=payload)

        # Assert: Both should default to True
        assert response.status_code == 201
        data = response.json()
        assert data["alert_on_recent_high"] is True
        assert data["alert_on_consecutive_increase"] is True


class TestFXWatchActions:
    """Tests for FX Watch action endpoints (check & alert)."""

    def test_openapi_should_expose_fx_timing_enums(self, client: TestClient):
        """Contract guard: keep FX timing enum fields constrained in OpenAPI."""
        response = client.get("/openapi.json")
        assert response.status_code == 200

        schemas = response.json()["components"]["schemas"]
        properties = schemas["FXTimingResultResponse"]["properties"]

        assert properties["trend_direction"]["enum"] == [
            "rising",
            "falling",
            "sideways",
        ]
        assert properties["signal_strength"]["enum"] == [
            "strong",
            "moderate",
            "weak",
            "none",
        ]
        target_direction_prop = properties["target_direction"]
        enum_values = target_direction_prop.get("enum")
        if enum_values is None:
            enum_values = next(
                (
                    item.get("enum")
                    for item in target_direction_prop.get("anyOf", [])
                    if isinstance(item, dict) and item.get("enum")
                ),
                None,
            )
        assert enum_values == ["above", "below"]

    def test_check_fx_watches_with_no_configs(self, client: TestClient):
        # Act
        response = client.post("/fx-watch/check")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total_watches"] == 0
        assert data["results"] == []

    @patch.dict("api.routes.fx_watch_routes._force_refresh_tracker", {}, clear=True)
    @patch("api.routes.fx_watch_routes.refresh_fx_data")
    def test_force_refresh_should_return_429_during_cooldown(
        self, mock_refresh_fx_data, client: TestClient
    ):
        # Act: first force refresh should pass
        first = client.post("/fx-watch/check?force_refresh=true")
        second = client.post("/fx-watch/check?force_refresh=true")

        # Assert
        assert first.status_code == 200
        assert second.status_code == 429
        detail = second.json()["detail"]
        assert detail["error_code"] == "FX_WATCH_REFRESH_COOLDOWN"
        assert detail["retry_after_seconds"] >= 1
        assert second.headers["Retry-After"] == str(detail["retry_after_seconds"])
        assert mock_refresh_fx_data.call_count == 1

    @patch.dict("api.routes.fx_watch_routes._force_refresh_tracker", {}, clear=True)
    @patch("api.routes.fx_watch_routes.refresh_fx_data")
    def test_non_force_refresh_should_not_be_blocked_by_force_refresh_cooldown(
        self, mock_refresh_fx_data, client: TestClient
    ):
        # Act: trigger force refresh once, then normal check
        force_refresh_response = client.post("/fx-watch/check?force_refresh=true")
        normal_check_response = client.post("/fx-watch/check")

        # Assert: normal check remains available
        assert force_refresh_response.status_code == 200
        assert normal_check_response.status_code == 200
        assert mock_refresh_fx_data.call_count == 1

    @patch("application.portfolio.fx_watch_service.get_forex_history_long")
    def test_check_fx_watches_with_active_config(
        self, mock_get_history, client: TestClient
    ):
        # Arrange: create a config
        client.post(
            "/fx-watch",
            json={
                "base_currency": "USD",
                "quote_currency": "TWD",
                "recent_high_days": 5,
                "consecutive_increase_days": 2,
            },
        )

        # Mock forex history with upward trend
        mock_get_history.return_value = [
            {"date": "2026-02-07", "close": 30.0},
            {"date": "2026-02-08", "close": 30.5},
            {"date": "2026-02-09", "close": 31.0},
            {"date": "2026-02-10", "close": 31.5},
        ]

        # Act
        response = client.post("/fx-watch/check")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total_watches"] == 1
        assert len(data["results"]) == 1
        result = data["results"][0]
        assert result["pair"] == "USD/TWD"
        assert "result" in result
        assert result["result"]["current_rate"] == 31.5
        assert result["result"]["is_recent_high"] is True
        assert result["result"]["consecutive_increases"] == 3
        assert result["result"]["alert_on_recent_high"] is True
        assert result["result"]["alert_on_consecutive_increase"] is True
        assert result["result"]["high_days_ago"] >= 0
        assert result["result"]["distance_from_high_pct"] >= 0
        assert result["result"]["trend_direction"] in {"rising", "falling", "sideways"}
        assert isinstance(result["result"]["trend_strength_pct"], float)
        assert result["result"]["signal_strength"] in {
            "strong",
            "moderate",
            "weak",
            "none",
        }

    @patch("application.portfolio.fx_watch_service.get_forex_history_long")
    def test_check_fx_watch_response_should_include_trend_fields(
        self, mock_get_history, client: TestClient
    ):
        client.post(
            "/fx-watch",
            json={
                "base_currency": "USD",
                "quote_currency": "JPY",
                "recent_high_days": 5,
                "consecutive_increase_days": 2,
            },
        )
        mock_get_history.return_value = [
            {"date": "2026-02-07", "close": 150.0},
            {"date": "2026-02-08", "close": 150.2},
            {"date": "2026-02-09", "close": 150.4},
            {"date": "2026-02-10", "close": 150.8},
            {"date": "2026-02-11", "close": 151.0},
            {"date": "2026-02-12", "close": 151.1},
            {"date": "2026-02-13", "close": 151.2},
            {"date": "2026-02-14", "close": 151.4},
            {"date": "2026-02-15", "close": 151.5},
            {"date": "2026-02-16", "close": 151.6},
        ]

        response = client.post("/fx-watch/check")
        assert response.status_code == 200
        item = response.json()["results"][0]["result"]
        assert "high_days_ago" in item
        assert "distance_from_high_pct" in item
        assert "trend_direction" in item
        assert "trend_strength_pct" in item
        assert "signal_strength" in item

    @patch("application.portfolio.fx_watch_service.log_notification_sent")
    @patch("application.portfolio.fx_watch_service.is_within_rate_limit")
    @patch("application.portfolio.fx_watch_service.send_telegram_message_dual")
    @patch("application.portfolio.fx_watch_service.get_forex_history_long")
    @patch("application.portfolio.fx_watch_service.is_notification_enabled")
    def test_send_fx_watch_alerts_triggers_notification(
        self,
        mock_notification_enabled,
        mock_get_history,
        mock_send_telegram,
        mock_rate_limit,
        _mock_log,
        client: TestClient,
    ):
        # Arrange: create a config that should trigger alert
        client.post(
            "/fx-watch",
            json={
                "base_currency": "USD",
                "quote_currency": "TWD",
                "recent_high_days": 5,
                "consecutive_increase_days": 2,
            },
        )

        mock_notification_enabled.return_value = True
        mock_rate_limit.return_value = True
        mock_get_history.return_value = [
            {"date": "2026-02-07", "close": 30.0},
            {"date": "2026-02-08", "close": 30.5},
            {"date": "2026-02-09", "close": 31.0},
            {"date": "2026-02-10", "close": 31.5},
        ]

        # Act
        response = client.post("/fx-watch/alert")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total_watches"] == 1
        assert data["triggered_alerts"] == 1
        assert data["sent_alerts"] == 1
        assert len(data["alerts"]) == 1

        # Verify Telegram was called
        assert mock_send_telegram.call_count == 1
        telegram_msg = mock_send_telegram.call_args[0][0]
        assert "外匯換匯時機警報" in telegram_msg
        assert "USD/TWD" in telegram_msg


class TestFXWatchValidation:
    """Tests for FX Watch request validation (422 errors)."""

    def test_create_should_return_422_when_missing_required_fields(
        self, client: TestClient
    ):
        # Act — empty body
        response = client.post("/fx-watch", json={})

        # Assert
        assert response.status_code == 422

    def test_create_should_return_422_when_base_currency_missing(
        self, client: TestClient
    ):
        # Act — only quote_currency provided
        response = client.post("/fx-watch", json={"quote_currency": "TWD"})

        # Assert
        assert response.status_code == 422

    def test_create_should_return_422_when_target_direction_without_target_rate(
        self, client: TestClient
    ):
        response = client.post(
            "/fx-watch",
            json={
                "base_currency": "USD",
                "quote_currency": "JPY",
                "target_direction": "above",
            },
        )
        assert response.status_code == 422

    def test_update_should_return_422_when_target_direction_without_target_rate(
        self, client: TestClient
    ):
        create_response = client.post(
            "/fx-watch",
            json={
                "base_currency": "USD",
                "quote_currency": "JPY",
                "target_rate": 150.0,
                "target_direction": "below",
            },
        )
        watch_id = create_response.json()["id"]

        response = client.patch(
            f"/fx-watch/{watch_id}",
            json={"target_direction": "above"},
        )
        assert response.status_code == 422


class TestFXWatchAlertCooldown:
    """Tests for alert cooldown integration flow."""

    @patch("application.portfolio.fx_watch_service.log_notification_sent")
    @patch("application.portfolio.fx_watch_service.is_within_rate_limit")
    @patch("application.portfolio.fx_watch_service.send_telegram_message_dual")
    @patch("application.portfolio.fx_watch_service.get_forex_history_long")
    @patch("application.portfolio.fx_watch_service.is_notification_enabled")
    def test_cooldown_should_prevent_duplicate_alerts(
        self,
        mock_notification_enabled,
        mock_get_history,
        mock_send_telegram,
        mock_rate_limit,
        _mock_log,
        client: TestClient,
    ):
        # Arrange: create a config with short cooldown
        client.post(
            "/fx-watch",
            json={
                "base_currency": "USD",
                "quote_currency": "TWD",
                "recent_high_days": 5,
                "consecutive_increase_days": 2,
                "reminder_interval_hours": 24,
            },
        )

        mock_notification_enabled.return_value = True
        mock_rate_limit.return_value = True
        mock_get_history.return_value = [
            {"date": "2026-02-07", "close": 30.0},
            {"date": "2026-02-08", "close": 30.5},
            {"date": "2026-02-09", "close": 31.0},
            {"date": "2026-02-10", "close": 31.5},
        ]

        # Act: first alert should trigger
        first = client.post("/fx-watch/alert")
        assert first.status_code == 200
        assert first.json()["triggered_alerts"] == 1
        assert first.json()["sent_alerts"] == 1

        # Act: second alert immediately — should be within cooldown
        second = client.post("/fx-watch/alert")

        # Assert: second has zero triggered (cooldown prevents re-analysis)
        assert second.status_code == 200
        assert second.json()["triggered_alerts"] == 0
        assert second.json()["sent_alerts"] == 0

    @patch("application.portfolio.fx_watch_service.get_forex_history_long")
    def test_check_should_handle_forex_api_failure_gracefully(
        self, mock_get_history, client: TestClient
    ):
        # Arrange: create a config
        client.post(
            "/fx-watch",
            json={
                "base_currency": "USD",
                "quote_currency": "TWD",
            },
        )

        # Mock forex history to raise exception
        mock_get_history.side_effect = RuntimeError("yfinance error")

        # Act
        response = client.post("/fx-watch/check")

        # Assert: returns 200, not 500
        assert response.status_code == 200
        data = response.json()
        assert data["total_watches"] == 0
        assert data["results"] == []


class TestFXWatchNotificationToggle:
    """Tests for notification toggle integration."""

    @patch("application.portfolio.fx_watch_service.send_telegram_message_dual")
    @patch("application.portfolio.fx_watch_service.get_forex_history_long")
    @patch("application.portfolio.fx_watch_service.is_notification_enabled")
    def test_alert_should_not_send_when_notification_disabled(
        self,
        mock_notification_enabled,
        mock_get_history,
        mock_send_telegram,
        client: TestClient,
    ):
        # Arrange: create config
        client.post(
            "/fx-watch",
            json={
                "base_currency": "USD",
                "quote_currency": "TWD",
                "recent_high_days": 5,
                "consecutive_increase_days": 2,
            },
        )

        mock_notification_enabled.return_value = False
        mock_get_history.return_value = [
            {"date": "2026-02-07", "close": 30.0},
            {"date": "2026-02-08", "close": 30.5},
            {"date": "2026-02-09", "close": 31.0},
            {"date": "2026-02-10", "close": 31.5},
        ]

        # Act
        response = client.post("/fx-watch/alert")

        # Assert: triggered but not sent
        assert response.status_code == 200
        data = response.json()
        assert data["triggered_alerts"] == 1
        assert data["sent_alerts"] == 0
        mock_send_telegram.assert_not_called()


class TestFXWatchUserIsolation:
    """Tests for user_id query parameter isolation."""

    def test_get_watches_should_isolate_by_user_id(self, client: TestClient):
        # Arrange: create configs for two different users
        client.post(
            "/fx-watch?user_id=user_a",
            json={
                "base_currency": "USD",
                "quote_currency": "TWD",
            },
        )
        client.post(
            "/fx-watch?user_id=user_b",
            json={
                "base_currency": "EUR",
                "quote_currency": "TWD",
            },
        )

        # Act: query for user_a only
        response = client.get("/fx-watch?user_id=user_a")

        # Assert: only user_a's config returned
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["base_currency"] == "USD"
        assert data[0]["user_id"] == "user_a"
