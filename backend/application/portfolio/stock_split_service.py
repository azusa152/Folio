"""Application — Stock split detection and settlement workflows."""

from __future__ import annotations

from datetime import UTC, date, datetime
from fractions import Fraction
from typing import TYPE_CHECKING

from fastapi import HTTPException

if TYPE_CHECKING:
    from sqlmodel import Session

from application.portfolio.settlement_service import settle_transaction
from domain.constants import (
    ERROR_INVALID_INPUT,
    HOLDING_QUANTITY_EPSILON,
    STOCK_SPLIT_LOOKBACK_DAYS,
)
from domain.entities import StockSplitEvent
from domain.enums import TransactionType
from i18n import get_user_language, t
from infrastructure import repositories as repo
from infrastructure.market_data import get_stock_splits
from infrastructure.notification import (
    is_notification_enabled,
    send_telegram_message_dual,
)
from logging_config import get_logger

logger = get_logger(__name__)

_PREF_AUTO_APPLY_SPLITS = "auto_apply_splits"
_SPLIT_STATUS_PENDING = "pending"
_SPLIT_STATUS_APPLIED = "applied"
_SPLIT_STATUS_DISMISSED = "dismissed"


def list_split_events(
    session: Session,
    *,
    status: str | None = None,
    limit: int | None = 200,
) -> list[StockSplitEvent]:
    """List stock split events with optional status filter."""
    return repo.find_stock_split_events(session, status=status, limit=limit)


def check_splits(
    session: Session,
    *,
    lookback_days: int = STOCK_SPLIT_LOOKBACK_DAYS,
    send_notifications: bool = True,
) -> dict:
    """Detect stock splits for currently-held tickers."""
    holdings = repo.find_all_holdings(session, include_zero_quantity=False)
    held_tickers = sorted(
        {
            h.ticker.upper().strip()
            for h in holdings
            if (not h.is_cash) and h.quantity > HOLDING_QUANTITY_EPSILON
        }
    )
    if not held_tickers:
        return {"checked_tickers": 0, "detected": 0, "auto_applied": 0, "events": []}

    new_events: list[StockSplitEvent] = []
    for ticker in held_tickers:
        for row in get_stock_splits(ticker, lookback_days=lookback_days):
            split_date = _parse_split_date(row.get("split_date"))
            ratio = _parse_ratio(row.get("ratio"))
            if split_date is None or ratio is None:
                continue
            existing = repo.find_stock_split_event_by_unique_key(
                session,
                ticker=ticker,
                split_date=split_date,
                ratio=ratio,
            )
            if existing is not None:
                continue
            event = StockSplitEvent(
                ticker=ticker,
                split_date=split_date,
                ratio=ratio,
                status=_SPLIT_STATUS_PENDING,
                detected_at=datetime.now(UTC),
            )
            created = repo.create_stock_split_event(session, event)
            new_events.append(created)

    auto_applied = 0
    if _is_auto_apply_enabled(session) and new_events:
        lang = get_user_language(session)
        for event in new_events:
            result = apply_split(session, event.id or 0, lang=lang)
            if result.get("status") == _SPLIT_STATUS_APPLIED:
                auto_applied += 1

    if send_notifications and new_events:
        send_split_alerts(session, events=new_events)

    return {
        "checked_tickers": len(held_tickers),
        "detected": len(new_events),
        "auto_applied": auto_applied,
        "events": [serialize_split_event(event) for event in new_events],
    }


def apply_split(session: Session, event_id: int, *, lang: str) -> dict:
    """Apply one pending split event to all matching holdings.

    Uses an atomic CAS transition (pending -> applied) so that concurrent
    callers are safe: only one writer proceeds with settlement; any racing
    caller that loses the CAS receives the already-applied event.
    """
    event = repo.find_stock_split_event_by_id(session, event_id)
    if event is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": ERROR_INVALID_INPUT,
                "detail": t("stock_split.not_found", lang=lang),
            },
        )
    if event.status != _SPLIT_STATUS_PENDING:
        return {
            "event": serialize_split_event(event),
            "status": event.status,
            "applied_accounts": 0,
            "transactions": 0,
        }

    # Atomically claim the event — only the winner proceeds with settlement.
    claimed = repo.try_claim_stock_split_event(
        session,
        event_id,
        from_status=_SPLIT_STATUS_PENDING,
        to_status=_SPLIT_STATUS_APPLIED,
    )
    if not claimed:
        # Another concurrent caller already moved this event; return current state.
        session.refresh(event)
        return {
            "event": serialize_split_event(event),
            "status": event.status,
            "applied_accounts": 0,
            "transactions": 0,
        }

    # Re-fetch with fresh state after the CAS commit.
    session.refresh(event)

    # Capture the before/after preview while holdings still reflect pre-split quantities.
    preview = build_split_preview(session, event)

    holdings = repo.find_all_holdings(session, include_zero_quantity=False)
    matching = [
        h
        for h in holdings
        if (not h.is_cash)
        and h.ticker.upper().strip() == event.ticker.upper().strip()
        and h.quantity > HOLDING_QUANTITY_EPSILON
        and h.account_id is not None
    ]

    transactions = 0
    applied_accounts: set[int] = set()
    for holding in matching:
        delta_shares = float(holding.quantity) * (float(event.ratio) - 1.0)
        if abs(delta_shares) <= HOLDING_QUANTITY_EPSILON:
            continue
        txn_data = {
            "account_id": int(holding.account_id),
            "holding_id": holding.id,
            "ticker": holding.ticker.upper().strip(),
            "transaction_type": TransactionType.STOCK_SPLIT.value,
            "quantity": delta_shares,
            "price": float(event.ratio),
            "total_amount": 0.0,
            "currency": holding.currency,
            "fx_rate": None,
            "fee": 0.0,
            "note": _build_split_note(event),
            "transaction_date": event.split_date,
        }
        settle_transaction(session, txn_data, lang, autocommit=False)
        applied_accounts.add(int(holding.account_id))
        transactions += 1

    event.applied_at = datetime.now(UTC)
    session.add(event)
    session.commit()
    session.refresh(event)

    return {
        "event": serialize_split_event(event, preview=preview),
        "status": event.status,
        "applied_accounts": len(applied_accounts),
        "transactions": transactions,
    }


def apply_all_pending_splits(session: Session, *, lang: str) -> dict:
    """Apply all pending split events."""
    pending = repo.find_stock_split_events(
        session, status=_SPLIT_STATUS_PENDING, limit=None
    )
    results = [apply_split(session, event.id or 0, lang=lang) for event in pending]
    applied = sum(1 for row in results if row.get("status") == _SPLIT_STATUS_APPLIED)
    return {"total": len(pending), "applied": applied, "results": results}


def dismiss_split(session: Session, event_id: int, *, lang: str) -> dict:
    """Dismiss one pending split event.

    Uses an atomic CAS transition (pending -> dismissed) so that concurrent
    callers are safe: only one writer lands the status change; any racing
    caller that loses the CAS receives the already-transitioned event.
    """
    event = repo.find_stock_split_event_by_id(session, event_id)
    if event is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": ERROR_INVALID_INPUT,
                "detail": t("stock_split.not_found", lang=lang),
            },
        )
    if event.status != _SPLIT_STATUS_PENDING:
        return {"event": serialize_split_event(event), "status": event.status}

    # Atomically claim the event — only the winner proceeds with the status change.
    repo.try_claim_stock_split_event(
        session,
        event_id,
        from_status=_SPLIT_STATUS_PENDING,
        to_status=_SPLIT_STATUS_DISMISSED,
    )
    session.expire(event)  # reload from DB to pick up the committed status
    session.refresh(event)
    return {"event": serialize_split_event(event), "status": event.status}


def send_split_alerts(
    session: Session, *, events: list[StockSplitEvent] | None = None
) -> dict:
    """Send Telegram alert for newly detected stock split events."""
    if not is_notification_enabled(session, "stock_split_alerts"):
        return {"sent": False, "count": 0}

    lang = get_user_language(session)
    target_events = events
    if target_events is None:
        target_events = repo.find_stock_split_events(
            session, status=_SPLIT_STATUS_PENDING, limit=20
        )
    if not target_events:
        return {"sent": False, "count": 0}

    lines = [t("stock_split.notification_header", lang=lang), ""]
    for event in target_events:
        ratio_label = _format_ratio_label(event.ratio)
        lines.append(
            t(
                "stock_split.notification_line",
                lang=lang,
                ticker=event.ticker,
                ratio=ratio_label,
                split_date=event.split_date.isoformat(),
            )
        )
    lines.append("")
    lines.append(t("stock_split.notification_footer", lang=lang))
    send_telegram_message_dual("\n".join(lines), session)
    return {"sent": True, "count": len(target_events)}


def serialize_split_event(
    event: StockSplitEvent,
    *,
    preview: list[dict] | None = None,
) -> dict:
    """Serialize split event for API response payloads."""
    return {
        "id": event.id,
        "ticker": event.ticker,
        "split_date": event.split_date.isoformat(),
        "ratio": event.ratio,
        "ratio_label": _format_ratio_label(event.ratio),
        "status": event.status,
        "detected_at": event.detected_at.isoformat(),
        "applied_at": event.applied_at.isoformat() if event.applied_at else None,
        "preview": preview or [],
    }


def build_split_preview(session: Session, event: StockSplitEvent) -> list[dict]:
    """Compute per-holding before/after preview for a pending split event.

    Fetches all accounts in a single query to avoid N+1 round-trips.
    """
    holdings = repo.find_all_holdings(session, include_zero_quantity=False)
    ticker_upper = event.ticker.upper().strip()
    matching = [
        h
        for h in holdings
        if not h.is_cash
        and h.ticker.upper().strip() == ticker_upper
        and h.quantity > HOLDING_QUANTITY_EPSILON
    ]
    if not matching:
        return []

    # Batch-load all accounts (one query) and build a lookup map.
    all_accounts = repo.find_all_accounts(session, active_only=False)
    account_names: dict[int, str] = {
        a.id: a.name for a in all_accounts if a.id is not None
    }

    ratio = float(event.ratio)
    preview: list[dict] = []
    for h in matching:
        before_qty = float(h.quantity)
        after_qty = round(before_qty * ratio, 8)
        before_cb = float(h.cost_basis) if h.cost_basis is not None else None
        after_cb = (
            round(before_cb / ratio, 8) if before_cb is not None and ratio > 0 else None
        )
        account_name = (
            account_names.get(int(h.account_id)) if h.account_id is not None else None
        )
        preview.append(
            {
                "account_id": h.account_id,
                "account_name": account_name,
                "before_qty": before_qty,
                "after_qty": after_qty,
                "before_cost_basis": before_cb,
                "after_cost_basis": after_cb,
            }
        )
    return preview


def _is_auto_apply_enabled(session: Session) -> bool:
    prefs = repo.find_user_preferences(session)
    if prefs is None:
        return False
    return bool(prefs.get_notification_prefs().get(_PREF_AUTO_APPLY_SPLITS, False))


def _parse_split_date(raw_value: object) -> date | None:
    if isinstance(raw_value, date):
        return raw_value
    if raw_value is None:
        return None
    try:
        return date.fromisoformat(str(raw_value)[:10])
    except ValueError:
        return None


def _parse_ratio(raw_value: object) -> float | None:
    try:
        ratio = float(raw_value)
    except (TypeError, ValueError):
        return None
    if ratio <= 0:
        return None
    return round(ratio, 8)


def _format_ratio_label(ratio: float) -> str:
    """Return a human-readable split ratio label.

    Examples:
        4.0  -> "4:1"   (4-for-1 forward split)
        0.5  -> "1:2"   (1-for-2 reverse split)
        2.0  -> "2:1"
        1.0  -> "1:1"
    """
    if ratio <= 0:
        return "N/A"
    frac = Fraction(ratio).limit_denominator(1000)
    return f"{frac.numerator}:{frac.denominator}"


def _build_split_note(event: StockSplitEvent) -> str:
    return (
        f"stock_split ratio={_format_ratio_label(event.ratio)} "
        f"date={event.split_date.isoformat()} event_id={event.id}"
    )
