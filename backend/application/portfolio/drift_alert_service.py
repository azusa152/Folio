"""Application — Portfolio drift monitoring and notification service."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlmodel import Session

from application.portfolio.alert_ack_service import (
    ACK_TYPE_DRIFT,
    acknowledge_alert,
    should_suppress_alert,
)
from application.portfolio.rebalance_service import calculate_rebalance
from domain.constants import DRIFT_THRESHOLD_PCT, ERROR_INVALID_INPUT
from i18n import get_user_language, t
from infrastructure.notification import (
    is_notification_enabled,
    is_within_rate_limit,
    send_telegram_message_dual,
)
from infrastructure.repositories import (
    delete_drift_acknowledgment,
    find_all_drift_acknowledgments,
    log_notification_sent,
)
from logging_config import get_logger

logger = get_logger(__name__)


def send_drift_alerts(
    session: Session,
    *,
    display_currency: str = "USD",
    threshold_pct: float = DRIFT_THRESHOLD_PCT,
) -> dict:
    """Check allocation drift and optionally send an alert summary."""
    rebalance = calculate_rebalance(session, display_currency=display_currency)
    categories = rebalance.get("categories", {})

    # Cleanup pass: clear stale acks whose drift has since recovered below threshold.
    # This runs *before* the breach loop so that recovered categories can alert again.
    # Build case-insensitive map because ack keys are stored uppercased.
    categories_upper = {str(k).upper(): v for k, v in categories.items()}
    for ack in find_all_drift_acknowledgments(session, alert_type=ACK_TYPE_DRIFT):
        info = categories_upper.get(ack.alert_key.upper())
        if info is None:
            continue
        raw = info.get("drift_pct", info.get("drift", 0))
        try:
            current_drift = float(raw or 0)
        except (TypeError, ValueError):
            continue
        if abs(current_drift) < float(threshold_pct):
            delete_drift_acknowledgment(
                session, alert_type=ACK_TYPE_DRIFT, alert_key=ack.alert_key
            )

    breaches: list[dict] = []
    suppressed: list[dict] = []
    for category_name, info in categories.items():
        raw_drift = info.get("drift_pct")
        if raw_drift is None:
            raw_drift = info.get("drift")
        try:
            drift = float(raw_drift or 0)
        except (TypeError, ValueError):
            continue
        drift_abs = abs(drift)
        if drift_abs <= float(threshold_pct):
            continue
        category = str(category_name)
        row = {
            "category": category,
            "drift_pct": round(drift, 2),
            "target_pct": round(float(info.get("target_pct", 0) or 0), 2),
            "actual_pct": round(float(info.get("actual_pct", 0) or 0), 2),
        }
        if should_suppress_alert(
            session,
            alert_type=ACK_TYPE_DRIFT,
            alert_key=category,
            current_value=drift,
            step_threshold=float(threshold_pct),
            clear_if_below=float(threshold_pct),
        ):
            suppressed.append(row)
            continue
        breaches.append(row)

    lang = get_user_language(session)
    if not breaches:
        return {"sent": False, "count": 0, "alerts": [], "suppressed": suppressed}

    if not is_notification_enabled(session, "drift_alerts"):
        return {
            "sent": False,
            "count": len(breaches),
            "alerts": breaches,
            "suppressed": suppressed,
        }
    if not is_within_rate_limit(session, "drift_alerts"):
        return {
            "sent": False,
            "count": len(breaches),
            "alerts": breaches,
            "suppressed": suppressed,
        }

    lines = [t("drift.notification_header", lang=lang), ""]
    lines.extend(
        t(
            "drift.notification_line",
            lang=lang,
            category=row["category"],
            actual=row["actual_pct"],
            target=row["target_pct"],
            drift=abs(row["drift_pct"]),
        )
        for row in breaches
    )
    lines.append("")
    lines.append(t("drift.notification_footer", lang=lang))
    try:
        send_telegram_message_dual("\n".join(lines), session)
    except Exception as exc:
        logger.warning("drift_alerts Telegram 發送失敗：%s", exc)
        return {
            "sent": False,
            "count": len(breaches),
            "alerts": breaches,
            "suppressed": suppressed,
        }

    log_notification_sent(session, "drift_alerts")
    return {
        "sent": True,
        "count": len(breaches),
        "alerts": breaches,
        "suppressed": suppressed,
    }


def acknowledge_drift_alert(
    session: Session,
    *,
    category: str,
    drift_pct: float | None = None,
    display_currency: str = "USD",
    threshold_pct: float = DRIFT_THRESHOLD_PCT,
) -> dict:
    """Acknowledge one drift category to suppress repeated alerts."""
    normalized_category = category.strip()
    if not normalized_category:
        raise ValueError(ERROR_INVALID_INPUT)

    current_drift = drift_pct
    if current_drift is None:
        rebalance = calculate_rebalance(session, display_currency=display_currency)
        categories = rebalance.get("categories", {})
        category_info = categories.get(normalized_category)
        if category_info is None:
            # fallback to case-insensitive lookup
            category_info = next(
                (
                    info
                    for key, info in categories.items()
                    if str(key).lower() == normalized_category.lower()
                ),
                None,
            )
        if category_info is None:
            raise ValueError(ERROR_INVALID_INPUT)
        raw_drift = category_info.get("drift_pct", category_info.get("drift", 0))
        current_drift = float(raw_drift or 0)

    if abs(float(current_drift)) <= float(threshold_pct):
        raise ValueError(ERROR_INVALID_INPUT)

    return acknowledge_alert(
        session,
        alert_type=ACK_TYPE_DRIFT,
        alert_key=normalized_category,
        acknowledged_value=float(current_drift),
    )
