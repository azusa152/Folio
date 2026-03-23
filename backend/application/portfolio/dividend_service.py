"""Application — Dividend detection and settlement workflows."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from fastapi import HTTPException

if TYPE_CHECKING:
    from sqlmodel import Session

from application.portfolio.settlement_service import settle_transaction
from domain.constants import (
    DIVIDEND_LOOKBACK_DAYS,
    ERROR_INVALID_INPUT,
    HOLDING_QUANTITY_EPSILON,
)
from domain.entities import DividendEvent
from domain.enums import TransactionType
from i18n import get_user_language, t
from infrastructure import repositories as repo
from infrastructure.market_data import get_dividend_events
from infrastructure.notification import (
    is_notification_enabled,
    send_telegram_message_dual,
)
from logging_config import get_logger

logger = get_logger(__name__)

_PREF_AUTO_APPLY_DIVIDENDS = "auto_apply_dividends"
_STATUS_PENDING = "pending"
_STATUS_APPLIED = "applied"
_STATUS_DISMISSED = "dismissed"


def list_dividend_events(
    session: Session,
    *,
    status: str | None = None,
    limit: int | None = 200,
) -> list[DividendEvent]:
    """List dividend events with optional status filter."""
    return repo.find_dividend_events(session, status=status, limit=limit)


def check_dividends(
    session: Session,
    *,
    lookback_days: int = DIVIDEND_LOOKBACK_DAYS,
    send_notifications: bool = True,
) -> dict:
    """Detect dividends for currently-held tickers."""
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

    new_events: list[DividendEvent] = []
    for ticker in held_tickers:
        for row in get_dividend_events(ticker, lookback_days=lookback_days):
            ex_date = _parse_date(row.get("ex_dividend_date"))
            amount = _parse_amount(row.get("amount_per_share"))
            if ex_date is None or amount is None:
                continue
            existing = repo.find_dividend_event_by_unique_key(
                session,
                ticker=ticker,
                ex_dividend_date=ex_date,
                amount_per_share=amount,
            )
            if existing is not None:
                continue
            event = DividendEvent(
                ticker=ticker,
                ex_dividend_date=ex_date,
                amount_per_share=amount,
                status=_STATUS_PENDING,
                detected_at=datetime.now(UTC),
            )
            created = repo.create_dividend_event(session, event)
            new_events.append(created)

    auto_applied = 0
    if _is_auto_apply_enabled(session) and new_events:
        lang = get_user_language(session)
        for event in new_events:
            result = apply_dividend(session, event.id or 0, lang=lang)
            if result.get("status") == _STATUS_APPLIED:
                auto_applied += 1

    if send_notifications and new_events:
        send_dividend_alerts(session, events=new_events)

    return {
        "checked_tickers": len(held_tickers),
        "detected": len(new_events),
        "auto_applied": auto_applied,
        "events": [serialize_dividend_event(event) for event in new_events],
    }


def apply_dividend(session: Session, event_id: int, *, lang: str) -> dict:
    """Apply one pending dividend event to all matching holdings."""
    event = repo.find_dividend_event_by_id(session, event_id)
    if event is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": ERROR_INVALID_INPUT,
                "detail": t("dividend.not_found", lang=lang),
            },
        )
    if event.status != _STATUS_PENDING:
        return {
            "event": serialize_dividend_event(event),
            "status": event.status,
            "applied_accounts": 0,
            "transactions": 0,
        }

    claimed = repo.try_claim_dividend_event(
        session,
        event_id,
        from_status=_STATUS_PENDING,
        to_status=_STATUS_APPLIED,
    )
    if not claimed:
        session.refresh(event)
        return {
            "event": serialize_dividend_event(event),
            "status": event.status,
            "applied_accounts": 0,
            "transactions": 0,
        }

    session.refresh(event)
    preview = build_dividend_preview(session, event)
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
        total_amount = float(holding.quantity) * float(event.amount_per_share)
        if total_amount <= HOLDING_QUANTITY_EPSILON:
            continue
        txn_data = {
            "account_id": int(holding.account_id),
            "holding_id": holding.id,
            "ticker": holding.ticker.upper().strip(),
            "transaction_type": TransactionType.DIVIDEND.value,
            "quantity": float(holding.quantity),
            "price": float(event.amount_per_share),
            "total_amount": round(total_amount, 8),
            "currency": holding.currency,
            "fx_rate": None,
            "fee": 0.0,
            "note": _build_dividend_note(event),
            "transaction_date": event.ex_dividend_date,
        }
        settle_transaction(session, txn_data, lang, autocommit=False)
        applied_accounts.add(int(holding.account_id))
        transactions += 1

    event.applied_at = datetime.now(UTC)
    session.add(event)
    session.commit()
    session.refresh(event)
    return {
        "event": serialize_dividend_event(event, preview=preview),
        "status": event.status,
        "applied_accounts": len(applied_accounts),
        "transactions": transactions,
    }


def apply_all_pending_dividends(session: Session, *, lang: str) -> dict:
    """Apply all pending dividend events."""
    pending = repo.find_dividend_events(session, status=_STATUS_PENDING, limit=None)
    results = [apply_dividend(session, event.id or 0, lang=lang) for event in pending]
    applied = sum(1 for row in results if row.get("status") == _STATUS_APPLIED)
    return {"total": len(pending), "applied": applied, "results": results}


def dismiss_dividend(session: Session, event_id: int, *, lang: str) -> dict:
    """Dismiss one pending dividend event."""
    event = repo.find_dividend_event_by_id(session, event_id)
    if event is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": ERROR_INVALID_INPUT,
                "detail": t("dividend.not_found", lang=lang),
            },
        )
    if event.status != _STATUS_PENDING:
        return {"event": serialize_dividend_event(event), "status": event.status}
    repo.try_claim_dividend_event(
        session,
        event_id,
        from_status=_STATUS_PENDING,
        to_status=_STATUS_DISMISSED,
    )
    session.refresh(event)
    return {"event": serialize_dividend_event(event), "status": event.status}


def send_dividend_alerts(
    session: Session, *, events: list[DividendEvent] | None = None
) -> dict:
    """Send Telegram alerts for newly detected dividend events."""
    if not is_notification_enabled(session, "dividend_alerts"):
        return {"sent": False, "count": 0}
    lang = get_user_language(session)
    target_events = events
    if target_events is None:
        target_events = repo.find_dividend_events(
            session, status=_STATUS_PENDING, limit=20
        )
    if not target_events:
        return {"sent": False, "count": 0}

    from application.formatters import format_stock_display, resolve_display_names

    event_tickers = [event.ticker for event in target_events]
    names = resolve_display_names(event_tickers, session)

    lines = [t("dividend.notification_header", lang=lang), ""]
    lines.extend(
        t(
            "dividend.notification_line",
            lang=lang,
            ticker=format_stock_display(
                names.get(event.ticker.strip().upper()), event.ticker
            ),
            amount=round(event.amount_per_share, 6),
            ex_date=event.ex_dividend_date.isoformat(),
        )
        for event in target_events
    )
    lines.append("")
    lines.append(t("dividend.notification_footer", lang=lang))
    send_telegram_message_dual("\n".join(lines), session)
    return {"sent": True, "count": len(target_events)}


def serialize_dividend_event(
    event: DividendEvent,
    *,
    preview: list[dict] | None = None,
) -> dict:
    """Serialize dividend event for API response payloads."""
    return {
        "id": event.id,
        "ticker": event.ticker,
        "ex_dividend_date": event.ex_dividend_date.isoformat(),
        "amount_per_share": event.amount_per_share,
        "status": event.status,
        "detected_at": event.detected_at.isoformat(),
        "applied_at": event.applied_at.isoformat() if event.applied_at else None,
        "preview": preview or [],
    }


def build_dividend_preview(session: Session, event: DividendEvent) -> list[dict]:
    """Compute per-holding estimated cash credit for a pending dividend event."""
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
    all_accounts = repo.find_all_accounts(session, active_only=False)
    account_names: dict[int, str] = {
        a.id: a.name for a in all_accounts if a.id is not None
    }
    preview: list[dict] = []
    for h in matching:
        estimated_cash = round(float(h.quantity) * float(event.amount_per_share), 8)
        account_name = (
            account_names.get(int(h.account_id)) if h.account_id is not None else None
        )
        preview.append(
            {
                "account_id": h.account_id,
                "account_name": account_name,
                "shares": float(h.quantity),
                "amount_per_share": float(event.amount_per_share),
                "estimated_cash": estimated_cash,
                "currency": h.currency,
            }
        )
    return preview


def _is_auto_apply_enabled(session: Session) -> bool:
    prefs = repo.find_user_preferences(session)
    if prefs is None:
        return False
    return bool(prefs.get_notification_prefs().get(_PREF_AUTO_APPLY_DIVIDENDS, False))


def _parse_date(raw_value: object) -> date | None:
    if isinstance(raw_value, date):
        return raw_value
    if raw_value is None:
        return None
    try:
        return date.fromisoformat(str(raw_value)[:10])
    except ValueError:
        return None


def _parse_amount(raw_value: object) -> float | None:
    try:
        amount = float(raw_value)
    except (TypeError, ValueError):
        return None
    if amount <= 0:
        return None
    return round(amount, 8)


def _build_dividend_note(event: DividendEvent) -> str:
    return (
        f"dividend amount_per_share={round(event.amount_per_share, 8)} "
        f"ex_date={event.ex_dividend_date.isoformat()} event_id={event.id}"
    )
