"""Application service for drift/X-Ray acknowledgment suppression."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from domain.constants import DRIFT_ACK_EXPIRE_DAYS
from infrastructure import repositories as repo

ACK_TYPE_DRIFT = "drift"
ACK_TYPE_XRAY = "xray"


def acknowledge_alert(
    session,
    *,
    alert_type: str,
    alert_key: str,
    acknowledged_value: float,
    expire_days: int = DRIFT_ACK_EXPIRE_DAYS,
) -> dict:
    """Persist acknowledgment for one alert key."""
    expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(
        days=max(1, int(expire_days))
    )
    ack = repo.upsert_drift_acknowledgment(
        session,
        alert_type=alert_type,
        alert_key=alert_key,
        acknowledged_value=float(acknowledged_value),
        expires_at=expires_at,
    )
    return {
        "type": ack.alert_type,
        "key": ack.alert_key,
        "acknowledged_value": float(ack.acknowledged_value),
        "acknowledged_at": ack.acknowledged_at.isoformat(),
        "expires_at": ack.expires_at.isoformat(),
    }


def should_suppress_alert(
    session,
    *,
    alert_type: str,
    alert_key: str,
    current_value: float,
    step_threshold: float,
    clear_if_below: float | None = None,
) -> bool:
    """Return True when an alert should be suppressed by existing acknowledgment."""
    ack = repo.find_drift_acknowledgment(
        session, alert_type=alert_type, alert_key=alert_key
    )
    if ack is None:
        return False

    current_abs = abs(float(current_value))
    if clear_if_below is not None and current_abs < float(clear_if_below):
        repo.delete_drift_acknowledgment(
            session, alert_type=alert_type, alert_key=alert_key
        )
        return False

    ack_value = float(ack.acknowledged_value)
    # For drift acknowledgments we re-alert if direction reverses past target.
    if alert_type == ACK_TYPE_DRIFT and (float(current_value) * ack_value < 0):
        repo.delete_drift_acknowledgment(
            session, alert_type=alert_type, alert_key=alert_key
        )
        return False

    should_realert = current_abs >= (abs(ack_value) + float(step_threshold))
    return not should_realert
