"""Regression tests for ledger migration script."""

from datetime import date

import pytest
from sqlmodel import Session, select

from domain.constants import DEFAULT_USER_ID
from domain.entities import Account, Holding, Transaction
from domain.enums import StockCategory, TransactionType


@pytest.fixture
def migration_module(db_session: Session, monkeypatch: pytest.MonkeyPatch):
    import scripts.migrate_ledger as migration

    # The migration creates its own Session(engine); using StaticPool keeps
    # both sessions on the same in-memory SQLite connection for test visibility.
    monkeypatch.setattr(migration, "engine", db_session.get_bind())
    return migration


def _create_account(session: Session, name: str = "IB Main") -> Account:
    account = Account(
        user_id=DEFAULT_USER_ID,
        name=name,
        broker="Interactive Brokers",
        account_type="brokerage",
        currency="USD",
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


def _create_holding(
    session: Session,
    *,
    ticker: str,
    quantity: float,
    account_id: int | None,
    is_cash: bool = False,
    cost_basis: float | None = None,
) -> Holding:
    holding = Holding(
        user_id=DEFAULT_USER_ID,
        ticker=ticker,
        category=StockCategory.CASH if is_cash else StockCategory.GROWTH,
        quantity=quantity,
        cost_basis=cost_basis,
        broker="Interactive Brokers",
        account_id=account_id,
        currency="USD",
        account_type="brokerage",
        is_cash=is_cash,
    )
    session.add(holding)
    session.commit()
    session.refresh(holding)
    return holding


def test_migrate_should_assign_orphans_and_create_opening_balances(
    db_session: Session, migration_module
):
    orphan_holding = _create_holding(
        db_session,
        ticker="AAPL",
        quantity=3.0,
        account_id=None,
        is_cash=False,
        cost_basis=100.0,
    )
    _create_holding(
        db_session,
        ticker="MSFT",
        quantity=0.0,
        account_id=None,
        is_cash=False,
        cost_basis=200.0,
    )
    orphan_txn = Transaction(
        user_id=DEFAULT_USER_ID,
        account_id=None,
        holding_id=None,
        ticker="USD",
        transaction_type=TransactionType.DEPOSIT,
        quantity=1.0,
        price=None,
        total_amount=200.0,
        currency="USD",
        fee=0.0,
        note="legacy orphan",
        transaction_date=date(2026, 3, 11),
    )
    db_session.add(orphan_txn)
    db_session.commit()

    stats = migration_module.migrate(dry_run=False)

    default_account = db_session.exec(
        select(Account).where(Account.name == "Default", Account.broker == "Default")
    ).one()
    db_session.refresh(orphan_holding)
    db_session.refresh(orphan_txn)
    assert orphan_holding.account_id == default_account.id
    assert orphan_txn.account_id == default_account.id
    assert stats["orphan_holdings"] >= 2
    assert stats["orphan_transactions"] >= 1

    opening_balance_txns = db_session.exec(
        select(Transaction).where(
            Transaction.holding_id == orphan_holding.id,
            Transaction.transaction_type == TransactionType.OPENING_BALANCE,
        )
    ).all()
    assert len(opening_balance_txns) == 1
    assert opening_balance_txns[0].account_id == default_account.id
    assert opening_balance_txns[0].quantity == 3.0


def test_migrate_should_be_idempotent(db_session: Session, migration_module):
    account = _create_account(db_session)
    holding = _create_holding(
        db_session,
        ticker="NVDA",
        quantity=2.0,
        account_id=account.id,
        is_cash=False,
        cost_basis=500.0,
    )

    first_run = migration_module.migrate(dry_run=False)
    second_run = migration_module.migrate(dry_run=False)

    ob_txns = db_session.exec(
        select(Transaction).where(
            Transaction.holding_id == holding.id,
            Transaction.transaction_type == TransactionType.OPENING_BALANCE,
        )
    ).all()
    assert first_run["opening_balances"] == 1
    assert second_run["opening_balances"] == 0
    assert len(ob_txns) == 1


def test_migrate_should_skip_zero_quantity_holding(
    db_session: Session, migration_module
):
    account = _create_account(db_session)
    zero_holding = _create_holding(
        db_session,
        ticker="MSFT",
        quantity=0.0,
        account_id=account.id,
        is_cash=False,
        cost_basis=150.0,
    )

    stats = migration_module.migrate(dry_run=False)

    ob_txns = db_session.exec(
        select(Transaction).where(
            Transaction.holding_id == zero_holding.id,
            Transaction.transaction_type == TransactionType.OPENING_BALANCE,
        )
    ).all()
    assert ob_txns == []
    assert stats["skipped"] >= 1


def test_migrate_dry_run_should_not_commit(db_session: Session, migration_module):
    orphan_holding = _create_holding(
        db_session,
        ticker="TSLA",
        quantity=1.0,
        account_id=None,
        is_cash=False,
        cost_basis=250.0,
    )

    preview = migration_module.migrate(dry_run=True)

    db_session.refresh(orphan_holding)
    assert orphan_holding.account_id is None
    assert preview["opening_balances"] == 1

    default_account = db_session.exec(
        select(Account).where(Account.name == "Default", Account.broker == "Default")
    ).first()
    ob_txns = db_session.exec(
        select(Transaction).where(
            Transaction.holding_id == orphan_holding.id,
            Transaction.transaction_type == TransactionType.OPENING_BALANCE,
        )
    ).all()
    assert default_account is None
    assert ob_txns == []
