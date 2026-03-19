"""Tests for alert acknowledgment suppression logic and service-level lifecycle."""

from unittest.mock import patch

from application.portfolio.alert_ack_service import (
    ACK_TYPE_DRIFT,
    ACK_TYPE_XRAY,
    acknowledge_alert,
    should_suppress_alert,
)
from infrastructure import repositories as repo


def test_drift_ack_should_suppress_until_worsened_by_threshold(db_session):
    acknowledge_alert(
        db_session,
        alert_type=ACK_TYPE_DRIFT,
        alert_key="Growth",
        acknowledged_value=12.0,
    )
    assert (
        should_suppress_alert(
            db_session,
            alert_type=ACK_TYPE_DRIFT,
            alert_key="Growth",
            current_value=14.0,
            step_threshold=5.0,
            clear_if_below=5.0,
        )
        is True
    )
    assert (
        should_suppress_alert(
            db_session,
            alert_type=ACK_TYPE_DRIFT,
            alert_key="Growth",
            current_value=17.1,
            step_threshold=5.0,
            clear_if_below=5.0,
        )
        is False
    )


def test_drift_ack_should_clear_when_reversed_past_target(db_session):
    acknowledge_alert(
        db_session,
        alert_type=ACK_TYPE_DRIFT,
        alert_key="Cash",
        acknowledged_value=10.0,
    )
    assert (
        should_suppress_alert(
            db_session,
            alert_type=ACK_TYPE_DRIFT,
            alert_key="Cash",
            current_value=-8.0,
            step_threshold=5.0,
            clear_if_below=5.0,
        )
        is False
    )
    assert (
        repo.find_drift_acknowledgment(
            db_session, alert_type=ACK_TYPE_DRIFT, alert_key="Cash"
        )
        is None
    )


def test_xray_ack_should_clear_after_recovery_below_threshold(db_session):
    acknowledge_alert(
        db_session,
        alert_type=ACK_TYPE_XRAY,
        alert_key="AAPL",
        acknowledged_value=20.0,
    )
    assert (
        should_suppress_alert(
            db_session,
            alert_type=ACK_TYPE_XRAY,
            alert_key="AAPL",
            current_value=22.0,
            step_threshold=5.0,
            clear_if_below=15.0,
        )
        is True
    )
    assert (
        should_suppress_alert(
            db_session,
            alert_type=ACK_TYPE_XRAY,
            alert_key="AAPL",
            current_value=14.9,
            step_threshold=5.0,
            clear_if_below=15.0,
        )
        is False
    )
    assert (
        repo.find_drift_acknowledgment(
            db_session, alert_type=ACK_TYPE_XRAY, alert_key="AAPL"
        )
        is None
    )


# ---------------------------------------------------------------------------
# Service-level lifecycle tests — verify cleanup passes in service functions
# ---------------------------------------------------------------------------


class TestDriftAlertServiceLifecycle:
    """End-to-end lifecycle tests for the drift-alert cleanup pass."""

    def _rebalance_with_categories(self, categories: dict) -> dict:
        return {"categories": categories, "xray": []}

    @patch("application.portfolio.drift_alert_service.send_telegram_message_dual")
    @patch(
        "application.portfolio.drift_alert_service.is_within_rate_limit",
        return_value=True,
    )
    @patch(
        "application.portfolio.drift_alert_service.is_notification_enabled",
        return_value=True,
    )
    @patch("application.portfolio.drift_alert_service.calculate_rebalance")
    def test_ack_cleared_when_drift_recovers_below_threshold(
        self,
        mock_calc,
        _mock_enabled,
        _mock_limit,
        mock_tg,
        db_session,
    ):
        """Ack created at high drift should be deleted when drift recovers."""
        from application.portfolio.drift_alert_service import send_drift_alerts

        # Seed an acknowledgment at 15% drift for "Growth"
        acknowledge_alert(
            db_session,
            alert_type=ACK_TYPE_DRIFT,
            alert_key="GROWTH",
            acknowledged_value=15.0,
        )
        assert (
            repo.find_drift_acknowledgment(
                db_session, alert_type=ACK_TYPE_DRIFT, alert_key="GROWTH"
            )
            is not None
        )

        # Now drift for "Growth" has recovered to 2% (below 5% threshold)
        mock_calc.return_value = self._rebalance_with_categories(
            {
                "Growth": {
                    "drift_pct": 2.0,
                    "target_pct": 40.0,
                    "actual_pct": 42.0,
                }
            }
        )

        result = send_drift_alerts(db_session, threshold_pct=5.0)

        # No breach → no alert sent
        assert result["sent"] is False
        assert result["count"] == 0
        # Stale ack must be gone so a future breach will re-alert
        assert (
            repo.find_drift_acknowledgment(
                db_session, alert_type=ACK_TYPE_DRIFT, alert_key="GROWTH"
            )
            is None
        )

    @patch("application.portfolio.drift_alert_service.send_telegram_message_dual")
    @patch(
        "application.portfolio.drift_alert_service.is_within_rate_limit",
        return_value=True,
    )
    @patch(
        "application.portfolio.drift_alert_service.is_notification_enabled",
        return_value=True,
    )
    @patch("application.portfolio.drift_alert_service.calculate_rebalance")
    def test_breach_re_alerts_after_ack_cleared_by_recovery(
        self,
        mock_calc,
        _mock_enabled,
        _mock_limit,
        mock_tg,
        db_session,
    ):
        """After ack is cleared by recovery, a new breach should fire a fresh alert."""
        from application.portfolio.drift_alert_service import send_drift_alerts

        # 1. Acknowledge at 15%
        acknowledge_alert(
            db_session,
            alert_type=ACK_TYPE_DRIFT,
            alert_key="CASH",
            acknowledged_value=15.0,
        )

        # 2. Recovery pass: drift drops to 1%  → ack cleared
        mock_calc.return_value = self._rebalance_with_categories(
            {"Cash": {"drift_pct": 1.0, "target_pct": 10.0, "actual_pct": 11.0}}
        )
        send_drift_alerts(db_session, threshold_pct=5.0)
        assert (
            repo.find_drift_acknowledgment(
                db_session, alert_type=ACK_TYPE_DRIFT, alert_key="CASH"
            )
            is None
        )

        # 3. Drift rises again above threshold → fresh alert must fire
        mock_calc.return_value = self._rebalance_with_categories(
            {"Cash": {"drift_pct": 12.0, "target_pct": 10.0, "actual_pct": 22.0}}
        )
        result = send_drift_alerts(db_session, threshold_pct=5.0)
        assert result["sent"] is True
        assert result["count"] == 1
        mock_tg.assert_called_once()

    @patch("application.portfolio.drift_alert_service.send_telegram_message_dual")
    @patch(
        "application.portfolio.drift_alert_service.is_within_rate_limit",
        return_value=True,
    )
    @patch(
        "application.portfolio.drift_alert_service.is_notification_enabled",
        return_value=True,
    )
    @patch("application.portfolio.drift_alert_service.calculate_rebalance")
    def test_orphan_drift_ack_persists_when_category_missing(
        self,
        mock_calc,
        _mock_enabled,
        _mock_limit,
        _mock_tg,
        db_session,
    ):
        """If a category is absent, drift ack remains until expiry or future match."""
        from application.portfolio.drift_alert_service import send_drift_alerts

        acknowledge_alert(
            db_session,
            alert_type=ACK_TYPE_DRIFT,
            alert_key="COMMODITY",
            acknowledged_value=9.0,
        )

        # Category "COMMODITY" does not exist in current rebalance categories.
        mock_calc.return_value = self._rebalance_with_categories(
            {"Cash": {"drift_pct": 1.0, "target_pct": 10.0, "actual_pct": 11.0}}
        )
        send_drift_alerts(db_session, threshold_pct=5.0)

        # Orphan ack should remain.
        assert (
            repo.find_drift_acknowledgment(
                db_session, alert_type=ACK_TYPE_DRIFT, alert_key="COMMODITY"
            )
            is not None
        )


class TestXRayAlertServiceLifecycle:
    """End-to-end lifecycle tests for the X-Ray cleanup pass."""

    @patch("application.portfolio.rebalance_service.send_telegram_message_dual")
    @patch(
        "application.portfolio.rebalance_service.is_within_rate_limit",
        return_value=True,
    )
    @patch(
        "application.portfolio.rebalance_service.is_notification_enabled",
        return_value=True,
    )
    def test_ack_cleared_when_concentration_drops_below_threshold(
        self, _mock_enabled, _mock_limit, mock_tg, db_session
    ):
        """Ack created at high concentration should be deleted when weight drops below threshold."""
        from application.portfolio.rebalance_service import send_xray_warnings

        # Seed an acknowledgment at 25% for NVDA
        acknowledge_alert(
            db_session,
            alert_type=ACK_TYPE_XRAY,
            alert_key="NVDA",
            acknowledged_value=25.0,
        )
        assert (
            repo.find_drift_acknowledgment(
                db_session, alert_type=ACK_TYPE_XRAY, alert_key="NVDA"
            )
            is not None
        )

        # NVDA has since dropped to 12% (below the 15% threshold)
        entries = [
            {
                "symbol": "NVDA",
                "total_weight_pct": 12.0,
                "direct_weight_pct": 12.0,
                "indirect_value": 0.0,
                "indirect_sources": [],
            }
        ]
        send_xray_warnings(entries, "USD", db_session)

        # Stale ack must be gone
        assert (
            repo.find_drift_acknowledgment(
                db_session, alert_type=ACK_TYPE_XRAY, alert_key="NVDA"
            )
            is None
        )

    @patch("application.portfolio.rebalance_service.send_telegram_message_dual")
    @patch(
        "application.portfolio.rebalance_service.is_within_rate_limit",
        return_value=True,
    )
    @patch(
        "application.portfolio.rebalance_service.is_notification_enabled",
        return_value=True,
    )
    def test_xray_re_alerts_after_ack_cleared_by_recovery(
        self, _mock_enabled, _mock_limit, mock_tg, db_session
    ):
        """After ack is cleared by recovery, a new breach should fire a fresh alert."""
        from application.portfolio.rebalance_service import send_xray_warnings

        # 1. Acknowledge TSLA at 30%
        acknowledge_alert(
            db_session,
            alert_type=ACK_TYPE_XRAY,
            alert_key="TSLA",
            acknowledged_value=30.0,
        )

        # 2. Recovery: TSLA drops to 10% → ack cleared, no alert
        entries_low = [
            {
                "symbol": "TSLA",
                "total_weight_pct": 10.0,
                "direct_weight_pct": 10.0,
                "indirect_value": 0.0,
                "indirect_sources": [],
            }
        ]
        send_xray_warnings(entries_low, "USD", db_session)
        assert (
            repo.find_drift_acknowledgment(
                db_session, alert_type=ACK_TYPE_XRAY, alert_key="TSLA"
            )
            is None
        )
        mock_tg.assert_not_called()

        # 3. TSLA rises again above threshold → fresh alert
        entries_high = [
            {
                "symbol": "TSLA",
                "total_weight_pct": 22.0,
                "direct_weight_pct": 12.0,
                "indirect_value": 500.0,
                "indirect_sources": ["Fund A"],
            }
        ]
        result = send_xray_warnings(entries_high, "USD", db_session)
        assert len(result) == 1
        mock_tg.assert_called_once()

    @patch("application.portfolio.rebalance_service.send_telegram_message_dual")
    @patch(
        "application.portfolio.rebalance_service.is_within_rate_limit",
        return_value=True,
    )
    @patch(
        "application.portfolio.rebalance_service.is_notification_enabled",
        return_value=True,
    )
    def test_xray_ack_cleared_when_symbol_absent_from_entries(
        self, _mock_enabled, _mock_limit, _mock_tg, db_session
    ):
        """If a symbol disappears from X-Ray entries, treat as recovered and clear ack."""
        from application.portfolio.rebalance_service import send_xray_warnings

        acknowledge_alert(
            db_session,
            alert_type=ACK_TYPE_XRAY,
            alert_key="MSFT",
            acknowledged_value=20.0,
        )
        assert (
            repo.find_drift_acknowledgment(
                db_session, alert_type=ACK_TYPE_XRAY, alert_key="MSFT"
            )
            is not None
        )

        # Symbol absent from entries (e.g., sold out) should clear stale ack.
        send_xray_warnings([], "USD", db_session)
        assert (
            repo.find_drift_acknowledgment(
                db_session, alert_type=ACK_TYPE_XRAY, alert_key="MSFT"
            )
            is None
        )
