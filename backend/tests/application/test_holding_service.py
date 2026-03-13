"""Tests for read-only holding_service behavior in ledger mode."""

import pytest
from fastapi import HTTPException
from sqlmodel import Session

from application.portfolio.holding_service import get_holdings_by_account, list_holdings
from domain.constants import DEFAULT_USER_ID
from domain.entities import Account, Holding
from domain.enums import StockCategory

_LANG = "en"


def _seed_account(
    session: Session,
    *,
    name: str = "Default",
    broker: str = "Default",
    active: bool = True,
) -> Account:
    account = Account(
        user_id=DEFAULT_USER_ID,
        name=name,
        broker=broker,
        account_type="brokerage",
        currency="USD",
        is_active=active,
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


def _seed_holding(
    session: Session,
    *,
    ticker: str,
    account_id: int | None,
    quantity: float = 5.0,
    is_cash: bool = False,
) -> Holding:
    holding = Holding(
        user_id=DEFAULT_USER_ID,
        ticker=ticker,
        category=StockCategory.CASH if is_cash else StockCategory.TREND_SETTER,
        quantity=quantity,
        currency="USD",
        account_id=account_id,
        is_cash=is_cash,
    )
    session.add(holding)
    session.commit()
    session.refresh(holding)
    return holding


class TestListHoldings:
    def test_returns_empty_when_no_holdings(self, db_session: Session) -> None:
        assert list_holdings(db_session) == []

    def test_returns_holdings_for_active_accounts_only(
        self, db_session: Session
    ) -> None:
        active = _seed_account(db_session, name="Active", broker="Active", active=True)
        inactive = _seed_account(
            db_session, name="Inactive", broker="Inactive", active=False
        )
        _seed_holding(db_session, ticker="AAPL", account_id=active.id)
        _seed_holding(db_session, ticker="MSFT", account_id=inactive.id)

        result = list_holdings(db_session)
        tickers = {item["ticker"] for item in result}
        assert tickers == {"AAPL"}

    def test_excludes_unlinked_orphan_holdings(self, db_session: Session) -> None:
        active = _seed_account(db_session, name="Active", broker="Active", active=True)
        _seed_holding(db_session, ticker="AAPL", account_id=active.id)
        _seed_holding(db_session, ticker="ORPHAN", account_id=None)

        result = list_holdings(db_session)
        tickers = {item["ticker"] for item in result}
        assert tickers == {"AAPL"}


class TestGetHoldingsByAccount:
    def test_returns_account_holdings(self, db_session: Session) -> None:
        account = _seed_account(db_session)
        _seed_holding(db_session, ticker="AAPL", account_id=account.id)
        _seed_holding(db_session, ticker="MSFT", account_id=account.id)

        result = get_holdings_by_account(db_session, account.id, _LANG)  # type: ignore[arg-type]
        tickers = {item["ticker"] for item in result}
        assert tickers == {"AAPL", "MSFT"}

    def test_raises_404_when_account_not_found(self, db_session: Session) -> None:
        with pytest.raises(HTTPException) as exc_info:
            get_holdings_by_account(db_session, 99999, _LANG)
        assert exc_info.value.status_code == 404
