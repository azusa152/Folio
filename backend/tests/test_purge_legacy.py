"""Tests for the purge_legacy_holdings script."""

from datetime import date

import pytest
from sqlalchemy import inspect, text
from sqlmodel import Session, select

from domain.constants import DEFAULT_USER_ID
from domain.entities import Account, Holding, Transaction
from domain.enums import StockCategory, TransactionType


@pytest.fixture
def purge_module(db_session: Session, monkeypatch: pytest.MonkeyPatch):
    import scripts.purge_legacy_holdings as purge

    monkeypatch.setattr(purge, "engine", db_session.get_bind())
    return purge


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
) -> Holding:
    holding = Holding(
        user_id=DEFAULT_USER_ID,
        ticker=ticker,
        category=StockCategory.CASH if is_cash else StockCategory.GROWTH,
        quantity=quantity,
        account_id=account_id,
        currency="USD",
        is_cash=is_cash,
    )
    session.add(holding)
    session.commit()
    session.refresh(holding)
    return holding


class TestPurgeLegacyHoldings:
    def test_should_delete_orphan_holdings(
        self, db_session: Session, purge_module
    ) -> None:
        account = _create_account(db_session)
        _create_holding(db_session, ticker="AAPL", quantity=5.0, account_id=account.id)
        _create_holding(db_session, ticker="ORPHAN", quantity=3.0, account_id=None)

        stats = purge_module.purge(dry_run=False)

        assert stats["orphan_holdings_deleted"] == 1
        remaining = db_session.exec(select(Holding)).all()
        tickers = {h.ticker for h in remaining}
        assert "ORPHAN" not in tickers
        assert "AAPL" in tickers

    def test_should_delete_orphan_transactions(
        self, db_session: Session, purge_module
    ) -> None:
        orphan_txn = Transaction(
            user_id=DEFAULT_USER_ID,
            account_id=None,
            ticker="USD",
            transaction_type=TransactionType.DEPOSIT,
            quantity=1.0,
            total_amount=200.0,
            currency="USD",
            fee=0.0,
            note="legacy",
            transaction_date=date(2026, 3, 11),
        )
        db_session.add(orphan_txn)
        db_session.commit()

        stats = purge_module.purge(dry_run=False)

        assert stats["orphan_transactions_deleted"] == 1
        assert db_session.exec(select(Transaction)).all() == []

    def test_should_delete_zero_quantity_stock_holdings(
        self, db_session: Session, purge_module
    ) -> None:
        account = _create_account(db_session)
        _create_holding(db_session, ticker="GHOST", quantity=0.0, account_id=account.id)
        _create_holding(
            db_session,
            ticker="USD",
            quantity=0.0,
            account_id=account.id,
            is_cash=True,
        )
        _create_holding(db_session, ticker="AAPL", quantity=10.0, account_id=account.id)

        stats = purge_module.purge(dry_run=False)

        assert stats["zero_qty_holdings_deleted"] == 1
        remaining = db_session.exec(select(Holding)).all()
        tickers = {h.ticker for h in remaining}
        assert "GHOST" not in tickers
        assert "USD" in tickers  # zero-qty cash is kept
        assert "AAPL" in tickers

    def test_dry_run_should_not_commit(self, db_session: Session, purge_module) -> None:
        _create_holding(db_session, ticker="ORPHAN", quantity=3.0, account_id=None)

        stats = purge_module.purge(dry_run=True)

        assert stats["orphan_holdings_deleted"] == 1
        remaining = db_session.exec(select(Holding)).all()
        assert len(remaining) == 1  # not deleted because dry-run

    def test_should_report_discrepancies(
        self, db_session: Session, purge_module
    ) -> None:
        account = _create_account(db_session)
        _create_holding(db_session, ticker="AAPL", quantity=10.0, account_id=account.id)

        stats = purge_module.purge(dry_run=False)

        assert isinstance(stats["discrepancies"], list)
        aapl_diffs = [d for d in stats["discrepancies"] if d["ticker"] == "AAPL"]
        assert len(aapl_diffs) == 1
        assert aapl_diffs[0]["materialized"] == 10.0
        assert aapl_diffs[0]["computed"] == 0.0

    def test_should_drop_legacy_net_worth_tables(
        self, db_session: Session, purge_module
    ) -> None:
        engine = db_session.get_bind()
        with engine.begin() as conn:
            conn.execute(
                text("CREATE TABLE IF NOT EXISTS networthitem (id INTEGER PRIMARY KEY)")
            )
            conn.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS networthsnapshot (id INTEGER PRIMARY KEY)"
                )
            )

        assert "networthitem" in inspect(engine).get_table_names()

        stats = purge_module.purge(dry_run=False)

        assert stats["legacy_tables_dropped"] == ["networthitem", "networthsnapshot"]
        assert "networthitem" not in inspect(engine).get_table_names()
        assert "networthsnapshot" not in inspect(engine).get_table_names()

    def test_dry_run_should_not_drop_legacy_tables(
        self, db_session: Session, purge_module
    ) -> None:
        engine = db_session.get_bind()
        with engine.begin() as conn:
            conn.execute(
                text("CREATE TABLE IF NOT EXISTS networthitem (id INTEGER PRIMARY KEY)")
            )

        stats = purge_module.purge(dry_run=True)

        assert stats["legacy_tables_dropped"] == ["networthitem"]
        assert "networthitem" in inspect(engine).get_table_names()
