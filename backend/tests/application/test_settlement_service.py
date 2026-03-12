"""Settlement regression tests for account-linked transactions."""

from datetime import date

import pytest
from fastapi import HTTPException
from sqlmodel import Session, select

from application.portfolio.settlement_service import verify_positions
from application.portfolio.transaction_service import (
    create_transaction,
    remove_transaction,
)
from domain.constants import DEFAULT_USER_ID, ERROR_INSUFFICIENT_BALANCE
from domain.entities import Account, Holding, Stock, Transaction
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


def _create_stock_holding(
    session: Session, account_id: int, ticker: str, quantity: float
) -> Holding:
    holding = Holding(
        user_id=DEFAULT_USER_ID,
        ticker=ticker,
        category=StockCategory.GROWTH,
        quantity=quantity,
        cost_basis=100.0,
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


def test_buy_transaction_should_create_stock_and_deduct_cash(db_session: Session):
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
    stock_holding = db_session.exec(
        select(Holding).where(
            Holding.account_id == account.id,
            Holding.ticker == "AAPL",
            Holding.is_cash == False,  # noqa: E712
        )
    ).one()
    assert result["account_id"] == account.id
    assert pytest.approx(cash_holding.quantity, rel=1e-9) == 890.0
    assert pytest.approx(stock_holding.quantity, rel=1e-9) == 1.0


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


def test_sell_transaction_should_reduce_stock_and_credit_cash(db_session: Session):
    account = _create_account(db_session)
    cash_holding = _create_cash_holding(db_session, account.id, 100.0)
    stock_holding = _create_stock_holding(db_session, account.id, "AAPL", 5.0)

    result = create_transaction(
        db_session,
        {
            "account_id": account.id,
            "ticker": "AAPL",
            "transaction_type": "SELL",
            "quantity": 2,
            "price": 100.0,
            "total_amount": 200.0,
            "currency": "USD",
            "fee": 5.0,
            "transaction_date": date(2026, 3, 10),
        },
        "en",
    )

    db_session.refresh(cash_holding)
    db_session.refresh(stock_holding)
    assert result["account_id"] == account.id
    assert pytest.approx(cash_holding.quantity, rel=1e-9) == 295.0
    assert pytest.approx(stock_holding.quantity, rel=1e-9) == 3.0


def test_sell_transaction_should_reject_when_shares_insufficient(db_session: Session):
    account = _create_account(db_session)
    _create_cash_holding(db_session, account.id, 100.0)
    _create_stock_holding(db_session, account.id, "AAPL", 1.0)

    with pytest.raises(HTTPException) as exc:
        create_transaction(
            db_session,
            {
                "account_id": account.id,
                "ticker": "AAPL",
                "transaction_type": "SELL",
                "quantity": 2,
                "price": 100.0,
                "total_amount": 200.0,
                "currency": "USD",
                "fee": 0.0,
                "transaction_date": date(2026, 3, 10),
            },
            "en",
        )

    assert exc.value.status_code == 422
    assert exc.value.detail["error_code"] == ERROR_INSUFFICIENT_BALANCE


def test_sell_should_match_existing_stock_holding_case_insensitively(
    db_session: Session,
):
    account = _create_account(db_session)
    cash_holding = _create_cash_holding(db_session, account.id, 100.0)
    stock_holding = _create_stock_holding(db_session, account.id, "aapl", 5.0)

    create_transaction(
        db_session,
        {
            "account_id": account.id,
            "ticker": "AAPL",
            "transaction_type": "SELL",
            "quantity": 2,
            "price": 100.0,
            "total_amount": 200.0,
            "currency": "USD",
            "fee": 0.0,
            "transaction_date": date(2026, 3, 10),
        },
        "en",
    )

    db_session.refresh(cash_holding)
    db_session.refresh(stock_holding)
    assert pytest.approx(stock_holding.quantity, rel=1e-9) == 3.0
    assert pytest.approx(cash_holding.quantity, rel=1e-9) == 300.0


def test_remove_buy_transaction_should_reverse_stock_and_cash(db_session: Session):
    account = _create_account(db_session)
    cash_holding = _create_cash_holding(db_session, account.id, 1000.0)

    created = create_transaction(
        db_session,
        {
            "account_id": account.id,
            "ticker": "AAPL",
            "transaction_type": "BUY",
            "quantity": 2,
            "price": 100.0,
            "total_amount": 200.0,
            "currency": "USD",
            "fee": 10.0,
            "transaction_date": date(2026, 3, 10),
        },
        "en",
    )
    remove_transaction(db_session, int(created["id"]), "en")

    db_session.refresh(cash_holding)
    stock_holding = db_session.exec(
        select(Holding).where(
            Holding.account_id == account.id,
            Holding.ticker == "AAPL",
            Holding.is_cash == False,  # noqa: E712
        )
    ).one()
    assert pytest.approx(cash_holding.quantity, rel=1e-9) == 1000.0
    assert pytest.approx(stock_holding.quantity, rel=1e-9) == 0.0
    assert db_session.exec(select(Transaction)).all() == []


def test_remove_buy_transaction_should_restore_original_cost_basis(db_session: Session):
    account = _create_account(db_session)
    _create_cash_holding(db_session, account.id, 3000.0)
    stock_holding = _create_stock_holding(db_session, account.id, "AAPL", 10.0)

    created = create_transaction(
        db_session,
        {
            "account_id": account.id,
            "ticker": "AAPL",
            "transaction_type": "BUY",
            "quantity": 10,
            "price": 120.0,
            "total_amount": 1200.0,
            "currency": "USD",
            "fee": 0.0,
            "transaction_date": date(2026, 3, 10),
        },
        "en",
    )

    db_session.refresh(stock_holding)
    assert pytest.approx(stock_holding.cost_basis, rel=1e-9) == 110.0
    assert pytest.approx(stock_holding.quantity, rel=1e-9) == 20.0

    remove_transaction(db_session, int(created["id"]), "en")

    db_session.refresh(stock_holding)
    assert pytest.approx(stock_holding.quantity, rel=1e-9) == 10.0
    assert pytest.approx(stock_holding.cost_basis, rel=1e-9) == 100.0


def test_opening_balance_cash_ticker_should_credit_cash_only(db_session: Session):
    account = _create_account(db_session)

    result = create_transaction(
        db_session,
        {
            "account_id": account.id,
            "ticker": "USD",
            "transaction_type": "OPENING_BALANCE",
            "quantity": 1,
            "price": 1.0,
            "total_amount": 500.0,
            "currency": "USD",
            "fee": 0.0,
            "transaction_date": date(2026, 3, 10),
        },
        "en",
    )

    holding = db_session.exec(
        select(Holding).where(Holding.account_id == account.id, Holding.is_cash == True)  # noqa: E712
    ).one()
    non_cash = db_session.exec(
        select(Holding).where(
            Holding.account_id == account.id,
            Holding.is_cash == False,  # noqa: E712
        )
    ).all()
    assert result["account_id"] == account.id
    assert pytest.approx(holding.quantity, rel=1e-9) == 500.0
    assert non_cash == []


def test_opening_balance_stock_ticker_should_create_stock_without_touching_cash(
    db_session: Session,
):
    account = _create_account(db_session)
    cash_holding = _create_cash_holding(db_session, account.id, 1000.0)

    create_transaction(
        db_session,
        {
            "account_id": account.id,
            "ticker": "AAPL",
            "transaction_type": "OPENING_BALANCE",
            "quantity": 10,
            "price": 100.0,
            "total_amount": 1000.0,
            "currency": "USD",
            "fee": 0.0,
            "transaction_date": date(2026, 3, 10),
        },
        "en",
    )

    db_session.refresh(cash_holding)
    stock_holding = db_session.exec(
        select(Holding).where(
            Holding.account_id == account.id,
            Holding.ticker == "AAPL",
            Holding.is_cash == False,  # noqa: E712
        )
    ).one()
    assert pytest.approx(cash_holding.quantity, rel=1e-9) == 1000.0
    assert pytest.approx(stock_holding.quantity, rel=1e-9) == 10.0


def test_opening_balance_stock_should_use_existing_radar_category(
    db_session: Session,
):
    account = _create_account(db_session)
    db_session.add(
        Stock(
            ticker="QQQ",
            category=StockCategory.TREND_SETTER,
            current_thesis="ETF thesis",
            current_tags="",
            is_active=True,
            is_etf=True,
        )
    )
    db_session.commit()

    create_transaction(
        db_session,
        {
            "account_id": account.id,
            "ticker": "QQQ",
            "transaction_type": "OPENING_BALANCE",
            "quantity": 3,
            "price": 100.0,
            "total_amount": 300.0,
            "currency": "USD",
            "fee": 0.0,
            "transaction_date": date(2026, 3, 10),
        },
        "en",
    )

    stock_holding = db_session.exec(
        select(Holding).where(
            Holding.account_id == account.id,
            Holding.ticker == "QQQ",
            Holding.is_cash == False,  # noqa: E712
        )
    ).one()
    assert stock_holding.category == StockCategory.TREND_SETTER


def test_adjustment_stock_ticker_should_modify_stock_without_touching_cash(
    db_session: Session,
):
    account = _create_account(db_session)
    cash_holding = _create_cash_holding(db_session, account.id, 1000.0)
    stock_holding = _create_stock_holding(db_session, account.id, "AAPL", 10.0)

    create_transaction(
        db_session,
        {
            "account_id": account.id,
            "ticker": "AAPL",
            "transaction_type": "ADJUSTMENT",
            "quantity": 3,
            "price": None,
            "total_amount": 1.0,
            "currency": "USD",
            "fee": 0.0,
            "transaction_date": date(2026, 3, 10),
        },
        "en",
    )
    db_session.refresh(cash_holding)
    db_session.refresh(stock_holding)
    assert pytest.approx(cash_holding.quantity, rel=1e-9) == 1000.0
    assert pytest.approx(stock_holding.quantity, rel=1e-9) == 13.0

    create_transaction(
        db_session,
        {
            "account_id": account.id,
            "ticker": "AAPL",
            "transaction_type": "ADJUSTMENT",
            "quantity": 4,
            "price": None,
            "total_amount": -1.0,
            "currency": "USD",
            "fee": 0.0,
            "transaction_date": date(2026, 3, 11),
        },
        "en",
    )
    db_session.refresh(cash_holding)
    db_session.refresh(stock_holding)
    assert pytest.approx(cash_holding.quantity, rel=1e-9) == 1000.0
    assert pytest.approx(stock_holding.quantity, rel=1e-9) == 9.0


def test_transfer_in_and_transfer_out_should_adjust_cash_balance(db_session: Session):
    account = _create_account(db_session)
    cash_holding = _create_cash_holding(db_session, account.id, 100.0)

    create_transaction(
        db_session,
        {
            "account_id": account.id,
            "ticker": "USD",
            "transaction_type": "TRANSFER_IN",
            "quantity": 1,
            "price": None,
            "total_amount": 200.0,
            "currency": "USD",
            "fee": 5.0,
            "transaction_date": date(2026, 3, 10),
        },
        "en",
    )
    db_session.refresh(cash_holding)
    assert pytest.approx(cash_holding.quantity, rel=1e-9) == 295.0

    create_transaction(
        db_session,
        {
            "account_id": account.id,
            "ticker": "USD",
            "transaction_type": "TRANSFER_OUT",
            "quantity": 1,
            "price": None,
            "total_amount": 50.0,
            "currency": "USD",
            "fee": 2.0,
            "transaction_date": date(2026, 3, 11),
        },
        "en",
    )
    db_session.refresh(cash_holding)
    assert pytest.approx(cash_holding.quantity, rel=1e-9) == 243.0


def test_adjustment_cash_ticker_should_adjust_cash_balance(db_session: Session):
    account = _create_account(db_session)
    cash_holding = _create_cash_holding(db_session, account.id, 100.0)

    create_transaction(
        db_session,
        {
            "account_id": account.id,
            "ticker": "USD",
            "transaction_type": "ADJUSTMENT",
            "quantity": 1,
            "price": None,
            "total_amount": 25.0,
            "currency": "USD",
            "fee": 0.0,
            "transaction_date": date(2026, 3, 10),
        },
        "en",
    )
    db_session.refresh(cash_holding)
    assert pytest.approx(cash_holding.quantity, rel=1e-9) == 125.0

    create_transaction(
        db_session,
        {
            "account_id": account.id,
            "ticker": "USD",
            "transaction_type": "ADJUSTMENT",
            "quantity": 1,
            "price": None,
            "total_amount": -10.0,
            "currency": "USD",
            "fee": 0.0,
            "transaction_date": date(2026, 3, 11),
        },
        "en",
    )
    db_session.refresh(cash_holding)
    assert pytest.approx(cash_holding.quantity, rel=1e-9) == 115.0


def test_verify_positions_should_return_empty_for_consistent_data(db_session: Session):
    account = _create_account(db_session)
    create_transaction(
        db_session,
        {
            "account_id": account.id,
            "ticker": "USD",
            "transaction_type": "OPENING_BALANCE",
            "quantity": 1,
            "price": 1.0,
            "total_amount": 1000.0,
            "currency": "USD",
            "fee": 0.0,
            "transaction_date": date(2026, 3, 9),
        },
        "en",
    )

    create_transaction(
        db_session,
        {
            "account_id": account.id,
            "ticker": "AAPL",
            "transaction_type": "BUY",
            "quantity": 2,
            "price": 100.0,
            "total_amount": 200.0,
            "currency": "USD",
            "fee": 0.0,
            "transaction_date": date(2026, 3, 10),
        },
        "en",
    )
    create_transaction(
        db_session,
        {
            "account_id": account.id,
            "ticker": "AAPL",
            "transaction_type": "SELL",
            "quantity": 1,
            "price": 120.0,
            "total_amount": 120.0,
            "currency": "USD",
            "fee": 0.0,
            "transaction_date": date(2026, 3, 11),
        },
        "en",
    )

    assert verify_positions(db_session) == []


def test_verify_positions_should_normalize_mixed_case_holding_ticker(
    db_session: Session,
):
    account = _create_account(db_session)
    create_transaction(
        db_session,
        {
            "account_id": account.id,
            "ticker": "USD",
            "transaction_type": "OPENING_BALANCE",
            "quantity": 1,
            "price": 1.0,
            "total_amount": 1000.0,
            "currency": "USD",
            "fee": 0.0,
            "transaction_date": date(2026, 3, 9),
        },
        "en",
    )

    create_transaction(
        db_session,
        {
            "account_id": account.id,
            "ticker": "AAPL",
            "transaction_type": "OPENING_BALANCE",
            "quantity": 1,
            "price": 100.0,
            "total_amount": 100.0,
            "currency": "USD",
            "fee": 0.0,
            "transaction_date": date(2026, 3, 9),
        },
        "en",
    )

    stock_holding = db_session.exec(
        select(Holding).where(
            Holding.account_id == account.id,
            Holding.ticker == "AAPL",
            Holding.is_cash == False,  # noqa: E712
        )
    ).one()
    stock_holding.ticker = "aapl"
    db_session.add(stock_holding)
    db_session.commit()

    assert verify_positions(db_session) == []


def test_verify_positions_should_detect_discrepancy(db_session: Session):
    account = _create_account(db_session)
    create_transaction(
        db_session,
        {
            "account_id": account.id,
            "ticker": "USD",
            "transaction_type": "OPENING_BALANCE",
            "quantity": 1,
            "price": 1.0,
            "total_amount": 1000.0,
            "currency": "USD",
            "fee": 0.0,
            "transaction_date": date(2026, 3, 9),
        },
        "en",
    )
    cash_holding = db_session.exec(
        select(Holding).where(Holding.account_id == account.id, Holding.is_cash == True)  # noqa: E712
    ).one()

    create_transaction(
        db_session,
        {
            "account_id": account.id,
            "ticker": "USD",
            "transaction_type": "DEPOSIT",
            "quantity": 1,
            "price": None,
            "total_amount": 100.0,
            "currency": "USD",
            "fee": 0.0,
            "transaction_date": date(2026, 3, 10),
        },
        "en",
    )

    cash_holding.quantity = 999.0
    db_session.add(cash_holding)
    db_session.commit()

    discrepancies = verify_positions(db_session)
    assert len(discrepancies) == 1
    assert discrepancies[0]["account_id"] == account.id
    assert discrepancies[0]["ticker"] == "USD"
    assert discrepancies[0]["is_cash"] is True
