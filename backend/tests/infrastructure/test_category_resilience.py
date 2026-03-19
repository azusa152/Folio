"""Regression tests for category parsing resilience."""

from sqlalchemy import text

from domain.constants import DEFAULT_USER_ID
from domain.entities import Account, Holding
from domain.enums import StockCategory
from infrastructure import repositories as repo


def test_find_all_holdings_should_coerce_unknown_category_and_log_warning(
    db_session, caplog
):
    """Unknown raw DB category values should not crash loading holdings."""
    account = Account(
        user_id=DEFAULT_USER_ID,
        name="Resilience Account",
        broker="Test Broker",
        account_type="brokerage",
        currency="USD",
        is_active=True,
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)

    holding = Holding(
        user_id=DEFAULT_USER_ID,
        ticker="BADCAT",
        category=StockCategory.GROWTH,
        quantity=1.0,
        currency="USD",
        is_cash=False,
        account_id=account.id,
    )
    db_session.add(holding)
    db_session.commit()
    db_session.refresh(holding)

    # Simulate legacy/bad raw DB value bypassing enum validation.
    db_session.execute(
        text("UPDATE holding SET category = :category WHERE id = :id"),
        {"category": "ALIEN_CATEGORY", "id": holding.id},
    )
    db_session.commit()
    db_session.expire_all()

    with caplog.at_level("WARNING", logger="domain.core.entities"):
        rows = repo.find_all_holdings(db_session)

    assert len(rows) == 1
    assert rows[0].category == StockCategory.GROWTH
    assert "Unknown stock category 'ALIEN_CATEGORY'" in caplog.text


def test_find_all_holdings_should_resolve_uppercase_member_name_without_warning(
    db_session, caplog
):
    """Uppercase enum member names stored by older DB rows must resolve correctly.

    The database historically stored category as the Python member name (e.g.,
    ``MOAT``, ``TREND_SETTER``) rather than the enum value (``Moat``,
    ``Trend_Setter``). Loading such rows must return the correct StockCategory
    without emitting any warning.
    """
    account = Account(
        user_id=DEFAULT_USER_ID,
        name="Legacy Name Account",
        broker="Test Broker",
        account_type="brokerage",
        currency="USD",
        is_active=True,
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)

    holding = Holding(
        user_id=DEFAULT_USER_ID,
        ticker="LEGACYMOAT",
        category=StockCategory.GROWTH,
        quantity=1.0,
        currency="USD",
        is_cash=False,
        account_id=account.id,
    )
    db_session.add(holding)
    db_session.commit()
    db_session.refresh(holding)

    # Write the uppercase member name directly, simulating pre-migration DB state.
    db_session.execute(
        text("UPDATE holding SET category = :category WHERE id = :id"),
        {"category": "MOAT", "id": holding.id},
    )
    db_session.commit()
    db_session.expire_all()

    with caplog.at_level("WARNING", logger="domain.core.entities"):
        rows = repo.find_all_holdings(db_session)

    assert len(rows) == 1
    assert rows[0].category == StockCategory.MOAT
    assert "Unknown stock category" not in caplog.text
