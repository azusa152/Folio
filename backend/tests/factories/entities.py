"""
Entity factory functions.

Each function creates and commits one entity to the provided session.  All
parameters have sensible defaults; override any field with keyword arguments.

Design notes:
- Factories call ``session.commit()`` and ``session.refresh()`` so callers
  receive objects whose auto-generated primary keys (id) are populated.
- Factories do NOT define pytest fixtures.  Wrap them in fixtures inside
  conftest.py or individual test files when fixture-level scoping is needed.
- Keep this module import-time cheap: domain imports happen inside functions
  so tests that don't use a particular factory don't pay the import cost.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlmodel import Session

# ---------------------------------------------------------------------------
# Stock
# ---------------------------------------------------------------------------


def make_stock(
    session: Session,
    *,
    ticker: str = "AAPL",
    category: str = "Growth",
    current_thesis: str = "Test thesis.",
    current_tags: str = "Test",
    display_order: int = 0,
    is_etf: bool = False,
    is_active: bool = True,
    **kwargs: Any,
) -> Any:
    """Create and persist a ``Stock`` with sensible defaults."""
    from domain.core.entities import Stock
    from domain.core.enums import StockCategory

    stock = Stock(
        ticker=ticker,
        category=StockCategory(category),
        current_thesis=current_thesis,
        current_tags=current_tags,
        display_order=display_order,
        is_etf=is_etf,
        is_active=is_active,
        **kwargs,
    )
    session.add(stock)
    session.commit()
    session.refresh(stock)
    return stock


# ---------------------------------------------------------------------------
# Account
# ---------------------------------------------------------------------------


def make_account(
    session: Session,
    *,
    name: str = "Test Account",
    broker: str = "Test Broker",
    account_type: str = "brokerage",
    tax_wrapper: str | None = None,
    currency: str = "USD",
    market: str | None = "US",
    institution: str = "",
    note: str = "",
    is_active: bool = True,
    **kwargs: Any,
) -> Any:
    """Create and persist an ``Account`` with sensible defaults."""
    from domain.constants import DEFAULT_USER_ID
    from domain.core.entities import Account

    account = Account(
        user_id=DEFAULT_USER_ID,
        name=name,
        broker=broker,
        account_type=account_type,
        tax_wrapper=tax_wrapper,
        currency=currency,
        market=market,
        institution=institution,
        note=note,
        is_active=is_active,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        **kwargs,
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


# ---------------------------------------------------------------------------
# Holding
# ---------------------------------------------------------------------------


def make_holding(
    session: Session,
    *,
    ticker: str = "AAPL",
    category: str = "Growth",
    quantity: float = 10.0,
    cost_basis: float | None = 150.0,
    currency: str = "USD",
    account_id: int | None = None,
    is_cash: bool = False,
    broker: str | None = None,
    purchase_fx_rate: float | None = None,
    **kwargs: Any,
) -> Any:
    """Create and persist a ``Holding`` with sensible defaults.

    For cash holdings pass ``is_cash=True`` and a cash ticker (e.g. ``"USD"``).
    The ``category`` defaults to ``"Cash"`` automatically when ``is_cash=True``
    unless explicitly overridden.
    """
    from domain.constants import DEFAULT_USER_ID
    from domain.core.entities import Holding
    from domain.core.enums import StockCategory

    resolved_category = "Cash" if is_cash and category == "Growth" else category

    holding = Holding(
        user_id=DEFAULT_USER_ID,
        ticker=ticker,
        category=StockCategory(resolved_category),
        quantity=quantity,
        cost_basis=cost_basis,
        currency=currency,
        account_id=account_id,
        is_cash=is_cash,
        broker=broker,
        purchase_fx_rate=purchase_fx_rate,
        updated_at=datetime.now(UTC),
        **kwargs,
    )
    session.add(holding)
    session.commit()
    session.refresh(holding)
    return holding


def make_cash_holding(
    session: Session,
    *,
    ticker: str = "USD",
    amount: float = 10_000.0,
    currency: str = "USD",
    account_id: int | None = None,
    **kwargs: Any,
) -> Any:
    """Convenience wrapper for a cash ``Holding``."""
    return make_holding(
        session,
        ticker=ticker,
        category="Cash",
        quantity=amount,
        cost_basis=1.0,
        currency=currency,
        account_id=account_id,
        is_cash=True,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------


def make_transaction(
    session: Session,
    *,
    ticker: str = "AAPL",
    transaction_type: str = "BUY",
    quantity: float = 10.0,
    price: float | None = 150.0,
    total_amount: float = 1500.0,
    currency: str = "USD",
    fx_rate: float | None = None,
    fee: float = 0.0,
    note: str = "",
    transaction_date: date | None = None,
    account_id: int | None = None,
    holding_id: int | None = None,
    **kwargs: Any,
) -> Any:
    """Create and persist a ``Transaction`` with sensible defaults."""
    from domain.constants import DEFAULT_USER_ID
    from domain.core.entities import Transaction
    from domain.core.enums import TransactionType

    tx = Transaction(
        user_id=DEFAULT_USER_ID,
        ticker=ticker,
        transaction_type=TransactionType(transaction_type),
        quantity=quantity,
        price=price,
        total_amount=total_amount,
        currency=currency,
        fx_rate=fx_rate,
        fee=fee,
        note=note,
        transaction_date=transaction_date or date.today(),
        account_id=account_id,
        holding_id=holding_id,
        created_at=datetime.now(UTC),
        **kwargs,
    )
    session.add(tx)
    session.commit()
    session.refresh(tx)
    return tx


# ---------------------------------------------------------------------------
# EligibleAsset
# ---------------------------------------------------------------------------


def make_eligible_asset(
    session: Session,
    *,
    tax_wrapper: str = "nisa_growth",
    ticker: str = "AAPL",
    fund_name: str = "",
    asset_type: str = "stock",
    broker: str | None = None,
    trust_fee_pct: float | None = None,
    isin_code: str | None = None,
    is_active: bool = True,
    **kwargs: Any,
) -> Any:
    """Create and persist an ``EligibleAsset`` with sensible defaults."""
    from domain.core.entities import EligibleAsset

    asset = EligibleAsset(
        tax_wrapper=tax_wrapper,
        ticker=ticker,
        fund_name=fund_name or ticker,
        asset_type=asset_type,
        broker=broker,
        trust_fee_pct=trust_fee_pct,
        isin_code=isin_code,
        is_active=is_active,
        updated_at=datetime.now(UTC),
        **kwargs,
    )
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset
