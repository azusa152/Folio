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
