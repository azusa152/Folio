from sqlmodel import select

from domain.entities import EligibleAsset
from infrastructure import repositories as repo


def _seed_eligible(session, *, ticker: str, isin_code: str | None):
    session.add(
        EligibleAsset(
            tax_wrapper="nisa_growth",
            ticker=ticker,
            fund_name="Test Fund",
            asset_type="mutual_fund",
            isin_code=isin_code,
            is_active=True,
        )
    )
    session.commit()


def test_backfill_isin_for_ticker_should_update_missing_isin(db_session):
    _seed_eligible(db_session, ticker="01311143", isin_code=None)

    changed = repo.backfill_isin_for_ticker(db_session, "01311143", "JP90C000A808")

    assert changed is True
    row = db_session.exec(
        select(EligibleAsset).where(EligibleAsset.ticker == "01311143")
    ).first()
    assert row is not None
    assert row.isin_code == "JP90C000A808"


def test_backfill_isin_for_ticker_should_treat_empty_string_as_missing(db_session):
    _seed_eligible(db_session, ticker="01311237", isin_code="")

    changed = repo.backfill_isin_for_ticker(db_session, "01311237", "JP90C000PSP2")

    assert changed is True
    row = db_session.exec(
        select(EligibleAsset).where(EligibleAsset.ticker == "01311237")
    ).first()
    assert row is not None
    assert row.isin_code == "JP90C000PSP2"


def test_backfill_isin_for_ticker_should_not_overwrite_existing_isin(db_session):
    _seed_eligible(db_session, ticker="01312179", isin_code="JP90C000FFC8")

    changed = repo.backfill_isin_for_ticker(db_session, "01312179", "JP90C000XXXX")

    assert changed is False
    row = db_session.exec(
        select(EligibleAsset).where(EligibleAsset.ticker == "01312179")
    ).first()
    assert row is not None
    assert row.isin_code == "JP90C000FFC8"


def test_find_fund_code_by_isin_should_return_8char_fund_code(db_session):
    _seed_eligible(db_session, ticker="EMAXIS S&P500", isin_code="JP90C000L110")
    _seed_eligible(db_session, ticker="0331220C", isin_code="JP90C000L110")

    fund_code = repo.find_fund_code_by_isin(db_session, "JP90C000L110")
    assert fund_code == "0331220C"


def test_find_fund_code_by_isin_should_return_none_when_no_match(db_session):
    _seed_eligible(db_session, ticker="EMAXIS S&P500", isin_code="JP90C000L110")

    fund_code = repo.find_fund_code_by_isin(db_session, "JP90C000XXXX")
    assert fund_code is None
