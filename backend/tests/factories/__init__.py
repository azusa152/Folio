"""
Shared test factories for building domain entities in tests.

Each factory function creates and persists a single entity with sensible
defaults; every field can be overridden via keyword arguments.

Usage::

    from tests.factories import make_account, make_holding, make_stock, make_transaction

    account = make_account(db_session)
    holding = make_holding(db_session, account_id=account.id, ticker="AAPL")
    tx = make_transaction(db_session, account_id=account.id, holding_id=holding.id, ticker="AAPL")
"""

from tests.factories.entities import (
    make_account,
    make_cash_holding,
    make_eligible_asset,
    make_holding,
    make_stock,
    make_transaction,
)

__all__ = [
    "make_account",
    "make_cash_holding",
    "make_eligible_asset",
    "make_holding",
    "make_stock",
    "make_transaction",
]
