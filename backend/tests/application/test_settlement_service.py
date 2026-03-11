"""Settlement regression tests for account-linked transactions."""

from datetime import date

import pytest
from fastapi import HTTPException
from sqlmodel import Session, select

from application.portfolio.transaction_service import (
    create_transaction,
    remove_transaction,
)
from domain.constants import DEFAULT_USER_ID, ERROR_INSUFFICIENT_BALANCE
from domain.entities import Account, Holding, Transaction
from domain.enums import StockCategory


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


def _create_cash_holding(session: Session, account_id: int, amount: float) -> Holding:
    holding = Holding(
        user_id=DEFAULT_USER_ID,
        ticker="USD",
        category=StockCategory.CASH,
        quantity=amount,
        cost_basis=1.0,
        broker="Interactive Brokers",
        account_id=account_id,
        currency="USD",
        account_type="brokerage",
        is_cash=True,
        purchase_fx_rate=1.0,
    )
    session.add(holding)
    session.commit()
    session.refresh(holding)
    return holding


def test_buy_transaction_should_deduct_cash_balance(db_session: Session):
    account = _create_account(db_session)
    cash_holding = _create_cash_holding(db_session, account.id, 1000.0)

    result = create_transaction(
        db_session,
        {
            "account_id": account.id,
            "ticker": "AAPL",
            "transaction_type": "BUY",
            "quantity": 1,
            "price": 100.0,
            "total_amount": 100.0,
            "currency": "USD",
            "fee": 10.0,
            "transaction_date": date(2026, 3, 10),
        },
        "en",
    )

    db_session.refresh(cash_holding)
    assert result["account_id"] == account.id
    assert pytest.approx(cash_holding.quantity, rel=1e-9) == 890.0


def test_buy_transaction_should_reject_when_balance_insufficient(db_session: Session):
    account = _create_account(db_session)
    cash_holding = _create_cash_holding(db_session, account.id, 50.0)

    with pytest.raises(HTTPException) as exc:
        create_transaction(
            db_session,
            {
                "account_id": account.id,
                "ticker": "AAPL",
                "transaction_type": "BUY",
                "quantity": 1,
                "price": 100.0,
                "total_amount": 100.0,
                "currency": "USD",
                "fee": 0.0,
                "transaction_date": date(2026, 3, 10),
            },
            "en",
        )

    detail = exc.value.detail
    assert exc.value.status_code == 422
    assert detail["error_code"] == ERROR_INSUFFICIENT_BALANCE
    db_session.refresh(cash_holding)
    assert pytest.approx(cash_holding.quantity, rel=1e-9) == 50.0
    assert db_session.exec(select(Transaction)).all() == []


def test_deposit_transaction_should_auto_create_cash_holding(db_session: Session):
    account = _create_account(db_session)

    result = create_transaction(
        db_session,
        {
            "account_id": account.id,
            "ticker": "USD",
            "transaction_type": "DEPOSIT",
            "quantity": 1,
            "price": None,
            "total_amount": 250.0,
            "currency": "USD",
            "fee": 0.0,
            "transaction_date": date(2026, 3, 10),
        },
        "en",
    )

    holding = db_session.exec(
        select(Holding).where(Holding.account_id == account.id, Holding.is_cash == True)  # noqa: E712
    ).one()
    assert result["account_id"] == account.id
    assert pytest.approx(holding.quantity, rel=1e-9) == 250.0


def test_sell_transaction_should_auto_create_cash_holding(db_session: Session):
    account = _create_account(db_session)

    result = create_transaction(
        db_session,
        {
            "account_id": account.id,
            "ticker": "AAPL",
            "transaction_type": "SELL",
            "quantity": 1,
            "price": 300.0,
            "total_amount": 300.0,
            "currency": "USD",
            "fee": 10.0,
            "transaction_date": date(2026, 3, 10),
        },
        "en",
    )

    holding = db_session.exec(
        select(Holding).where(Holding.account_id == account.id, Holding.is_cash == True)  # noqa: E712
    ).one()
    assert result["account_id"] == account.id
    assert pytest.approx(holding.quantity, rel=1e-9) == 290.0


def test_dividend_transaction_should_auto_create_cash_holding(db_session: Session):
    account = _create_account(db_session)

    result = create_transaction(
        db_session,
        {
            "account_id": account.id,
            "ticker": "AAPL",
            "transaction_type": "DIVIDEND",
            "quantity": 1,
            "price": None,
            "total_amount": 50.0,
            "currency": "USD",
            "fee": 0.0,
            "transaction_date": date(2026, 3, 10),
        },
        "en",
    )

    holding = db_session.exec(
        select(Holding).where(Holding.account_id == account.id, Holding.is_cash == True)  # noqa: E712
    ).one()
    assert result["account_id"] == account.id
    assert pytest.approx(holding.quantity, rel=1e-9) == 50.0


def test_remove_transaction_should_reverse_settlement(db_session: Session):
    account = _create_account(db_session)
    cash_holding = _create_cash_holding(db_session, account.id, 1000.0)

    created = create_transaction(
        db_session,
        {
            "account_id": account.id,
            "ticker": "AAPL",
            "transaction_type": "BUY",
            "quantity": 1,
            "price": 100.0,
            "total_amount": 100.0,
            "currency": "USD",
            "fee": 5.0,
            "transaction_date": date(2026, 3, 10),
        },
        "en",
    )
    remove_transaction(db_session, int(created["id"]), "en")

    db_session.refresh(cash_holding)
    assert pytest.approx(cash_holding.quantity, rel=1e-9) == 1000.0
    assert db_session.exec(select(Transaction)).all() == []
