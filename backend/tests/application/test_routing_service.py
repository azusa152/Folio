from datetime import date
from unittest.mock import patch

import pytest
from sqlmodel import Session

from application.portfolio.routing_service import (
    _compute_realized_gains_ytd,
    get_detax_suggestions,
    suggest_transaction_routing,
)
from application.portfolio.transaction_service import create_transaction
from domain.constants import DEFAULT_USER_ID
from domain.entities import Account, EligibleAsset, Transaction


def _create_account(
    session: Session,
    *,
    name: str,
    broker: str,
    tax_wrapper: str,
    currency: str = "JPY",
) -> Account:
    account = Account(
        user_id=DEFAULT_USER_ID,
        name=name,
        broker=broker,
        account_type="brokerage",
        tax_wrapper=tax_wrapper,
        currency=currency,
        is_active=True,
    )
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
) -> None:
    session.add(
        EligibleAsset(
            tax_wrapper=wrapper,
            ticker=ticker,
            fund_name=ticker,
            asset_type=asset_type,
            broker=broker,
            is_active=True,
        )
    )
    session.commit()


def test_suggest_transaction_routing_should_include_ideco_when_eligible(
    db_session: Session,
):
    ideco = _create_account(
        db_session,
        name="iDeCo",
        broker="SBI",
        tax_wrapper="ideco",
        currency="JPY",
    )
    _create_eligible_asset(
        db_session,
        wrapper="ideco",
        ticker="1306.T",
        broker="SBI",
    )

    suggestions = suggest_transaction_routing(
        session=db_session,
        ticker="1306.T",
        total_amount=120_000,
    )
    assert suggestions
    assert suggestions[0].wrapper == "ideco"
    assert suggestions[0].amount == pytest.approx(120_000)
    assert suggestions[0].reason == "routing.ideco_tax_deferred"
    assert ideco.id is not None


@patch("application.portfolio.routing_service.get_technical_signals")
def test_get_detax_suggestions_should_use_realized_gains_not_sell_proceeds(
    mock_get_technical_signals,
    db_session: Session,
):
    account = _create_account(
        db_session,
        name="Tokutei",
        broker="SBI",
        tax_wrapper="tokutei",
        currency="USD",
    )
    create_transaction(
        db_session,
        {
            "account_id": account.id,
            "ticker": "USD",
            "transaction_type": "DEPOSIT",
            "quantity": 1,
            "price": 1.0,
            "total_amount": 250_000.0,
            "currency": "USD",
            "transaction_date": date(2026, 1, 2),
        },
        "en",
    )
    create_transaction(
        db_session,
        {
            "account_id": account.id,
            "ticker": "AAA",
            "transaction_type": "BUY",
            "quantity": 500,
            "price": 100.0,
            "total_amount": 50_000.0,
            "currency": "USD",
            "transaction_date": date(2026, 1, 3),
        },
        "en",
    )
    create_transaction(
        db_session,
        {
            "account_id": account.id,
            "ticker": "AAA",
            "transaction_type": "SELL",
            "quantity": 500,
            "price": 200.0,
            "total_amount": 100_000.0,
            "currency": "USD",
            "transaction_date": date(2026, 1, 4),
        },
        "en",
    )
    create_transaction(
        db_session,
        {
            "account_id": account.id,
            "ticker": "BBB",
            "transaction_type": "BUY",
            "quantity": 500,
            "price": 100.0,
            "total_amount": 50_000.0,
            "currency": "USD",
            "transaction_date": date(2026, 1, 5),
        },
        "en",
    )

    def _fake_price(ticker: str):
        return {"price": 50.0 if ticker == "BBB" else 200.0}

    mock_get_technical_signals.side_effect = _fake_price

    opportunities = get_detax_suggestions(db_session)
    assert len(opportunities) == 1
    assert opportunities[0].ticker == "BBB"
    # Loss = 25,000 => tax saved = 25,000 * 0.20315 = 5,078.75
    assert opportunities[0].estimated_tax_saved == pytest.approx(5_078.75)


def test_realized_gains_should_prorate_fee_when_sell_qty_exceeds_position():
    txns = [
        Transaction(
            id=1,
            user_id=DEFAULT_USER_ID,
            account_id=10,
            ticker="AAA",
            transaction_type="BUY",
            quantity=100,
            price=100.0,
            total_amount=10_000.0,
            currency="USD",
            fee=0.0,
            transaction_date=date(2026, 1, 2),
        ),
        Transaction(
            id=2,
            user_id=DEFAULT_USER_ID,
            account_id=10,
            ticker="AAA",
            transaction_type="SELL",
            quantity=150,  # exceeds position; effective sell qty must clamp to 100
            price=200.0,
            total_amount=30_000.0,
            currency="USD",
            fee=300.0,
            transaction_date=date(2026, 1, 3),
        ),
    ]
    realized = _compute_realized_gains_ytd(
        txns,
        {10},
        start_of_year=date(2026, 1, 1),
        today=date(2026, 12, 31),
    )
    # Fee should be prorated: 300 * (100 / 150) = 200.
    # Realized gain = (200 - 100) * 100 - 200 = 9,800.
    assert realized == pytest.approx(9_800.0)
