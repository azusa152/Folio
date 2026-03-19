"""Unit tests for stock split application service."""

from datetime import date
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from sqlmodel import Session, select

from application.portfolio.stock_split_service import (
    apply_split,
    check_splits,
    dismiss_split,
)
from domain.constants import DEFAULT_USER_ID
from domain.entities import (
    Account,
    Holding,
    StockSplitEvent,
    Transaction,
    UserPreferences,
)
from domain.enums import StockCategory, TransactionType


def _create_account(session: Session) -> Account:
    account = Account(
        user_id=DEFAULT_USER_ID,
        name="IB Main",
        broker="Interactive Brokers",
        account_type="brokerage",
        currency="USD",
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


def _create_stock_holding(
    session: Session,
    *,
    account_id: int,
    ticker: str,
    quantity: float,
    cost_basis: float,
) -> Holding:
    holding = Holding(
        user_id=DEFAULT_USER_ID,
        ticker=ticker,
        category=StockCategory.GROWTH,
        quantity=quantity,
        cost_basis=cost_basis,
        broker="Interactive Brokers",
        account_id=account_id,
        currency="USD",
        account_type="brokerage",
        is_cash=False,
    )
    session.add(holding)
    session.commit()
    session.refresh(holding)
    return holding


def _enable_auto_apply(session: Session) -> None:
    prefs = UserPreferences(user_id=DEFAULT_USER_ID)
    prefs.set_notification_prefs({"auto_apply_splits": True})
    session.add(prefs)
    session.commit()


def test_check_splits_should_create_pending_event_and_skip_duplicate(
    db_session: Session,
):
    account = _create_account(db_session)
    _create_stock_holding(
        db_session,
        account_id=int(account.id),
        ticker="AAPL",
        quantity=10.0,
        cost_basis=100.0,
    )

    with patch(
        "application.portfolio.stock_split_service.get_stock_splits",
        return_value=[{"split_date": "2026-03-15", "ratio": 2.0}],
    ):
        first = check_splits(db_session, send_notifications=False)
        second = check_splits(db_session, send_notifications=False)

    assert first["checked_tickers"] == 1
    assert first["detected"] == 1
    assert first["auto_applied"] == 0
    assert len(first["events"]) == 1
    assert first["events"][0]["ticker"] == "AAPL"
    assert first["events"][0]["ratio_label"] == "2:1"
    assert second["detected"] == 0


def test_check_splits_should_auto_apply_when_preference_enabled(db_session: Session):
    account = _create_account(db_session)
    holding = _create_stock_holding(
        db_session,
        account_id=int(account.id),
        ticker="AAPL",
        quantity=10.0,
        cost_basis=100.0,
    )
    _enable_auto_apply(db_session)

    with patch(
        "application.portfolio.stock_split_service.get_stock_splits",
        return_value=[{"split_date": "2026-03-15", "ratio": 2.0}],
    ):
        result = check_splits(db_session, send_notifications=False)

    db_session.refresh(holding)
    event = db_session.exec(select(StockSplitEvent)).one()
    split_txn = db_session.exec(
        select(Transaction).where(
            Transaction.transaction_type == TransactionType.STOCK_SPLIT.value
        )
    ).one()

    assert result["detected"] == 1
    assert result["auto_applied"] == 1
    assert event.status == "applied"
    assert pytest.approx(holding.quantity, rel=1e-9) == 20.0
    assert pytest.approx(holding.cost_basis or 0.0, rel=1e-9) == 50.0
    assert pytest.approx(split_txn.quantity, rel=1e-9) == 10.0
    assert pytest.approx(split_txn.price or 0.0, rel=1e-9) == 2.0


def test_apply_split_should_raise_404_for_missing_event(db_session: Session):
    with pytest.raises(HTTPException) as exc:
        apply_split(db_session, 9999, lang="en")

    assert exc.value.status_code == 404


def test_dismiss_split_should_mark_pending_event_dismissed(db_session: Session):
    event = StockSplitEvent(
        ticker="AAPL",
        split_date=date(2026, 3, 15),
        ratio=2.0,
        status="pending",
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)

    result = dismiss_split(db_session, int(event.id or 0), lang="en")

    assert result["status"] == "dismissed"
    assert result["event"]["ticker"] == "AAPL"
