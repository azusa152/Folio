"""Settlement regression tests for account-linked transactions."""

from datetime import date

import pytest
from fastapi import HTTPException
from sqlmodel import Session, select

from application.portfolio.account_service import remove_account
from application.portfolio.settlement_service import verify_positions
from application.portfolio.transaction_service import (
    create_transaction,
    remove_transaction,
)
from application.portfolio.wrapper_service import get_all_wrapper_quotas
from domain.constants import DEFAULT_USER_ID, ERROR_INSUFFICIENT_BALANCE
from domain.entities import (
    Account,
    ContributionLedgerEntry,
    EligibleAsset,
    Holding,
    Stock,
    Transaction,
)
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


def _create_nisa_account(session: Session, wrapper: str) -> Account:
    account = _create_account(session)
    account.tax_wrapper = wrapper
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


def _create_eligible_asset(
    session: Session,
    *,
    wrapper: str,
    ticker: str,
    broker: str | None = None,
    asset_type: str = "stock",
) -> EligibleAsset:
    item = EligibleAsset(
        tax_wrapper=wrapper,
        ticker=ticker,
        fund_name=ticker,
        asset_type=asset_type,
        broker=broker,
        is_active=True,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


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


def test_existing_stock_holding_should_sync_category_from_radar_on_new_transaction(
    db_session: Session,
):
    account = _create_account(db_session)
    _create_cash_holding(db_session, account.id, 1000.0)
    stock_holding = _create_stock_holding(db_session, account.id, "AAPL", 10.0)
    assert stock_holding.category == StockCategory.GROWTH

    db_session.add(
        Stock(
            ticker="AAPL",
            category=StockCategory.MOAT,
            current_thesis="Updated on radar",
            current_tags="",
            is_active=True,
            is_etf=False,
        )
    )
    db_session.commit()

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
            "transaction_date": date(2026, 3, 12),
        },
        "en",
    )

    db_session.refresh(stock_holding)
    assert stock_holding.category == StockCategory.MOAT


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


def test_stock_split_should_adjust_quantity_and_cost_basis_without_cash_change(
    db_session: Session,
):
    account = _create_account(db_session)
    cash_holding = _create_cash_holding(db_session, account.id, 1000.0)
    stock_holding = _create_stock_holding(db_session, account.id, "AAPL", 10.0)

    created = create_transaction(
        db_session,
        {
            "account_id": account.id,
            "ticker": "AAPL",
            "transaction_type": "STOCK_SPLIT",
            "quantity": 10.0,  # additive delta for 2:1 split
            "price": 2.0,  # split ratio
            "total_amount": 0.0,
            "currency": "USD",
            "fee": 0.0,
            "transaction_date": date(2026, 3, 12),
        },
        "en",
    )

    db_session.refresh(cash_holding)
    db_session.refresh(stock_holding)
    assert created["account_id"] == account.id
    assert pytest.approx(cash_holding.quantity, rel=1e-9) == 1000.0
    assert pytest.approx(stock_holding.quantity, rel=1e-9) == 20.0
    assert pytest.approx(stock_holding.cost_basis or 0.0, rel=1e-9) == 50.0


def test_remove_stock_split_should_restore_quantity_and_cost_basis(db_session: Session):
    account = _create_account(db_session)
    _create_cash_holding(db_session, account.id, 1000.0)
    stock_holding = _create_stock_holding(db_session, account.id, "AAPL", 10.0)

    created = create_transaction(
        db_session,
        {
            "account_id": account.id,
            "ticker": "AAPL",
            "transaction_type": "STOCK_SPLIT",
            "quantity": 10.0,
            "price": 2.0,
            "total_amount": 0.0,
            "currency": "USD",
            "fee": 0.0,
            "transaction_date": date(2026, 3, 12),
        },
        "en",
    )
    db_session.refresh(stock_holding)
    assert pytest.approx(stock_holding.quantity, rel=1e-9) == 20.0
    assert pytest.approx(stock_holding.cost_basis or 0.0, rel=1e-9) == 50.0

    remove_transaction(db_session, int(created["id"]), "en")

    db_session.refresh(stock_holding)
    assert pytest.approx(stock_holding.quantity, rel=1e-9) == 10.0
    assert pytest.approx(stock_holding.cost_basis or 0.0, rel=1e-9) == 100.0


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


def test_verify_positions_should_include_stock_split_quantity_delta(
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
            "quantity": 10,
            "price": 100.0,
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
            "transaction_type": "STOCK_SPLIT",
            "quantity": 10.0,
            "price": 2.0,
            "total_amount": 0.0,
            "currency": "USD",
            "fee": 0.0,
            "transaction_date": date(2026, 3, 12),
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


@pytest.mark.slow
def test_nisa_buy_should_reject_when_quota_exceeded(db_session: Session):
    account = _create_nisa_account(db_session, "nisa_tsumitate")
    _create_cash_holding(db_session, account.id, 2_000_000.0)
    _create_eligible_asset(
        db_session,
        wrapper="nisa_tsumitate",
        ticker="AAPL",
        asset_type="mutual_fund",
    )

    # Preload near annual limit.
    db_session.add(
        ContributionLedgerEntry(
            user_id=DEFAULT_USER_ID,
            tax_wrapper="nisa_tsumitate",
            entry_type="CONTRIBUTION",
            fiscal_year=2026,
            amount=1_150_000.0,
            effective_date=date(2026, 1, 10),
        )
    )
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        create_transaction(
            db_session,
            {
                "account_id": account.id,
                "ticker": "AAPL",
                "transaction_type": "BUY",
                "quantity": 1,
                "price": 100.0,
                "total_amount": 100_000.0,
                "currency": "USD",
                "fee": 0.0,
                "transaction_date": date(2026, 3, 10),
            },
            "en",
        )

    assert exc.value.status_code == 422
    assert exc.value.detail["error_code"] == "QUOTA_EXCEEDED"


def test_nisa_buy_should_reject_when_asset_not_eligible(db_session: Session):
    account = _create_nisa_account(db_session, "nisa_tsumitate")
    _create_cash_holding(db_session, account.id, 2_000_000.0)
    _create_eligible_asset(
        db_session,
        wrapper="nisa_tsumitate",
        ticker="0331418A",
        asset_type="mutual_fund",
    )

    with pytest.raises(HTTPException) as exc:
        create_transaction(
            db_session,
            {
                "account_id": account.id,
                "ticker": "AAPL",
                "transaction_type": "BUY",
                "quantity": 1,
                "price": 100.0,
                "total_amount": 1_000.0,
                "currency": "USD",
                "fee": 0.0,
                "transaction_date": date(2026, 3, 10),
            },
            "en",
        )

    assert exc.value.status_code == 422
    assert exc.value.detail["error_code"] == "ASSET_NOT_ELIGIBLE"
    assert "eligibility.not_in_tsumitate_approved_list" in exc.value.detail["reasons"]
    assert exc.value.detail["suggested_wrapper"] == "nisa_growth"


def test_nisa_growth_buy_should_reject_when_not_in_growth_approved_list(
    db_session: Session,
):
    account = _create_nisa_account(db_session, "nisa_growth")
    _create_cash_holding(db_session, account.id, 2_000_000.0)
    _create_eligible_asset(
        db_session,
        wrapper="nisa_growth",
        ticker="7203.T",
        asset_type="stock",
    )

    with pytest.raises(HTTPException) as exc:
        create_transaction(
            db_session,
            {
                "account_id": account.id,
                "ticker": "AAPL",
                "transaction_type": "BUY",
                "quantity": 1,
                "price": 100.0,
                "total_amount": 1_000.0,
                "currency": "USD",
                "fee": 0.0,
                "transaction_date": date(2026, 3, 10),
            },
            "en",
        )

    assert exc.value.status_code == 422
    assert exc.value.detail["error_code"] == "ASSET_NOT_ELIGIBLE"
    assert "eligibility.not_in_growth_approved_list" in exc.value.detail["reasons"]
    assert exc.value.detail["suggested_wrapper"] == "tokutei"


def test_nisa_growth_buy_should_allow_stock_ticker_not_in_approved_list(
    db_session: Session,
):
    account = _create_nisa_account(db_session, "nisa_growth")
    _create_cash_holding(db_session, account.id, 2_000_000.0)
    _create_eligible_asset(
        db_session,
        wrapper="nisa_growth",
        ticker="2558.T",
        asset_type="etf",
    )

    created = create_transaction(
        db_session,
        {
            "account_id": account.id,
            "ticker": "6758.T",
            "transaction_type": "BUY",
            "quantity": 1,
            "price": 100.0,
            "total_amount": 1_000.0,
            "currency": "USD",
            "fee": 0.0,
            "transaction_date": date(2026, 3, 10),
        },
        "en",
    )

    holding = db_session.exec(
        select(Holding).where(
            Holding.account_id == account.id,
            Holding.ticker == "6758.T",
            Holding.is_cash == False,  # noqa: E712
        )
    ).one()
    assert created["account_id"] == account.id
    assert holding.category == StockCategory.GROWTH


def test_nisa_growth_buy_should_normalize_bare_4digit_ticker(
    db_session: Session,
):
    """Bare 4-digit JP code (e.g. '6758') is accepted by eligibility logic.

    Note: the eligibility service normalises the ticker to '6758.T' internally,
    but create_transaction stores whatever ticker string was passed in.  The
    holding query therefore accepts both forms.
    """
    account = _create_nisa_account(db_session, "nisa_growth")
    _create_cash_holding(db_session, account.id, 2_000_000.0)
    _create_eligible_asset(
        db_session,
        wrapper="nisa_growth",
        ticker="2558.T",
        asset_type="etf",
    )

    created = create_transaction(
        db_session,
        {
            "account_id": account.id,
            "ticker": "6758",
            "transaction_type": "BUY",
            "quantity": 1,
            "price": 100.0,
            "total_amount": 1_000.0,
            "currency": "USD",
            "fee": 0.0,
            "transaction_date": date(2026, 3, 10),
        },
        "en",
    )

    holding = db_session.exec(
        select(Holding).where(
            Holding.account_id == account.id,
            Holding.is_cash == False,  # noqa: E712
            Holding.ticker.in_(["6758", "6758.T"]),  # type: ignore[union-attr]
        )
    ).first()
    assert created["account_id"] == account.id
    assert holding is not None


def test_nisa_tsumitate_buy_should_force_mutual_fund_category(db_session: Session):
    account = _create_nisa_account(db_session, "nisa_tsumitate")
    _create_cash_holding(db_session, account.id, 2_000_000.0)
    _create_eligible_asset(
        db_session,
        wrapper="nisa_tsumitate",
        ticker="0331418A",
        asset_type="mutual_fund",
    )

    create_transaction(
        db_session,
        {
            "account_id": account.id,
            "ticker": "0331418A",
            "transaction_type": "BUY",
            "quantity": 10,
            "price": 100.0,
            "total_amount": 1_000.0,
            "currency": "USD",
            "fee": 0.0,
            "category": "Growth",
            "transaction_date": date(2026, 3, 10),
        },
        "en",
    )

    stock_holding = db_session.exec(
        select(Holding).where(
            Holding.account_id == account.id,
            Holding.ticker == "0331418A",
            Holding.is_cash == False,  # noqa: E712
        )
    ).one()
    assert stock_holding.category == StockCategory.MUTUAL_FUND


def test_nisa_growth_buy_should_force_mutual_fund_category_for_mutual_fund_asset(
    db_session: Session,
):
    account = _create_nisa_account(db_session, "nisa_growth")
    _create_cash_holding(db_session, account.id, 2_000_000.0)
    _create_eligible_asset(
        db_session,
        wrapper="nisa_growth",
        ticker="01312179",
        asset_type="mutual_fund",
    )

    create_transaction(
        db_session,
        {
            "account_id": account.id,
            "ticker": "01312179",
            "transaction_type": "BUY",
            "quantity": 10,
            "price": 100.0,
            "total_amount": 1_000.0,
            "currency": "USD",
            "fee": 0.0,
            "category": "Growth",
            "transaction_date": date(2026, 3, 10),
        },
        "en",
    )

    stock_holding = db_session.exec(
        select(Holding).where(
            Holding.account_id == account.id,
            Holding.ticker == "01312179",
            Holding.is_cash == False,  # noqa: E712
        )
    ).one()
    assert stock_holding.category == StockCategory.MUTUAL_FUND


def test_nisa_buy_and_sell_should_record_contribution_and_restoration(
    db_session: Session,
):
    account = _create_nisa_account(db_session, "nisa_growth")
    _create_cash_holding(db_session, account.id, 10_000.0)

    created_buy = create_transaction(
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
    created_sell = create_transaction(
        db_session,
        {
            "account_id": account.id,
            "ticker": "AAPL",
            "transaction_type": "SELL",
            "quantity": 1,
            "price": 100.0,
            "total_amount": 100.0,
            "currency": "USD",
            "fee": 0.0,
            "transaction_date": date(2026, 3, 11),
        },
        "en",
    )

    entries = db_session.exec(
        select(ContributionLedgerEntry).order_by(ContributionLedgerEntry.id)
    ).all()
    assert len(entries) == 2
    assert entries[0].entry_type == "CONTRIBUTION"
    assert entries[0].transaction_id == created_buy["id"]
    assert entries[0].amount == 200.0
    assert entries[1].entry_type == "RESTORATION"
    assert entries[1].transaction_id == created_sell["id"]
    assert entries[1].amount == -100.0


def test_remove_account_should_delete_nisa_ledger_entries(db_session: Session):
    account = _create_nisa_account(db_session, "nisa_growth")
    _create_cash_holding(db_session, account.id, 10_000.0)

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
            "fee": 0.0,
            "transaction_date": date(2026, 3, 10),
        },
        "en",
    )
    assert created["id"] is not None

    entries_before = db_session.exec(select(ContributionLedgerEntry)).all()
    assert len(entries_before) == 1
    quotas_before = get_all_wrapper_quotas(
        db_session,
        user_id=DEFAULT_USER_ID,
        year=2026,
        as_of=date(2026, 3, 10),
    )
    assert quotas_before["nisa_growth"]["wrapper_annual_used"] > 0

    remove_account(db_session, account.id, "en")

    entries_after = db_session.exec(select(ContributionLedgerEntry)).all()
    transactions_after = db_session.exec(
        select(Transaction).where(Transaction.account_id == account.id)
    ).all()
    holdings_after = db_session.exec(
        select(Holding).where(Holding.account_id == account.id)
    ).all()
    assert entries_after == []
    assert transactions_after == []
    assert holdings_after == []
    quotas_after = get_all_wrapper_quotas(
        db_session,
        user_id=DEFAULT_USER_ID,
        year=2026,
        as_of=date(2026, 3, 10),
    )
    assert quotas_after["nisa_growth"]["wrapper_annual_used"] == 0


# ---------------------------------------------------------------------------
# reclassify_mutual_fund_holdings
# ---------------------------------------------------------------------------


class TestReclassifyMutualFundHoldings:
    def test_reclassifies_growth_holdings_matching_eligible_fund(
        self, db_session: Session
    ):
        from application.portfolio.settlement_service import (
            reclassify_mutual_fund_holdings,
        )

        account = _create_account(db_session)
        db_session.add(
            Holding(
                user_id=DEFAULT_USER_ID,
                ticker="0131217A",
                category=StockCategory.GROWTH,
                quantity=100,
                account_id=account.id,
                currency="JPY",
                is_cash=False,
            )
        )
        db_session.add(
            Holding(
                user_id=DEFAULT_USER_ID,
                ticker="AAPL",
                category=StockCategory.GROWTH,
                quantity=10,
                account_id=account.id,
                currency="USD",
                is_cash=False,
            )
        )
        db_session.add(
            EligibleAsset(
                tax_wrapper="nisa_tsumitate",
                ticker="0131217A",
                fund_name="テスト投信",
                asset_type="mutual_fund",
                is_active=True,
            )
        )
        db_session.commit()

        updated = reclassify_mutual_fund_holdings(db_session)

        assert updated == 1
        holdings = db_session.exec(
            select(Holding).where(Holding.ticker == "0131217A")
        ).all()
        assert all(h.category == StockCategory.MUTUAL_FUND for h in holdings)
        aapl = db_session.exec(select(Holding).where(Holding.ticker == "AAPL")).first()
        assert aapl is not None
        assert aapl.category == StockCategory.GROWTH

    def test_skips_holdings_already_mutual_fund(self, db_session: Session):
        from application.portfolio.settlement_service import (
            reclassify_mutual_fund_holdings,
        )

        account = _create_account(db_session)
        db_session.add(
            Holding(
                user_id=DEFAULT_USER_ID,
                ticker="0131217A",
                category=StockCategory.MUTUAL_FUND,
                quantity=100,
                account_id=account.id,
                currency="JPY",
                is_cash=False,
            )
        )
        db_session.add(
            EligibleAsset(
                tax_wrapper="nisa_tsumitate",
                ticker="0131217A",
                fund_name="テスト投信",
                asset_type="mutual_fund",
                is_active=True,
            )
        )
        db_session.commit()

        updated = reclassify_mutual_fund_holdings(db_session)

        assert updated == 0


# ---------------------------------------------------------------------------
# _infer_category eligible fund fallback
# ---------------------------------------------------------------------------


class TestInferCategoryEligibleFund:
    def test_infers_mutual_fund_from_eligible_master(self, db_session: Session):
        from application.portfolio.settlement_service import _infer_category

        db_session.add(
            EligibleAsset(
                tax_wrapper="nisa_tsumitate",
                ticker="01313139",
                fund_name="テスト投信",
                asset_type="mutual_fund",
                is_active=True,
            )
        )
        db_session.commit()

        result = _infer_category(db_session, {"ticker": "01313139"})

        assert result == StockCategory.MUTUAL_FUND

    def test_prefers_radar_stock_over_eligible_master(self, db_session: Session):
        from application.portfolio.settlement_service import _infer_category

        db_session.add(
            Stock(
                ticker="01313139",
                category=StockCategory.GROWTH,
                is_active=True,
                is_etf=False,
            )
        )
        db_session.add(
            EligibleAsset(
                tax_wrapper="nisa_tsumitate",
                ticker="01313139",
                fund_name="テスト投信",
                asset_type="mutual_fund",
                is_active=True,
            )
        )
        db_session.commit()

        result = _infer_category(db_session, {"ticker": "01313139"})

        assert result == StockCategory.GROWTH

    def test_falls_back_to_payload_when_no_match(self, db_session: Session):
        from application.portfolio.settlement_service import _infer_category

        result = _infer_category(db_session, {"ticker": "UNKNOWN", "category": "Bond"})

        assert result == StockCategory.BOND
