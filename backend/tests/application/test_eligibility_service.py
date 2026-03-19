"""Unit tests for application-layer eligibility service (check_asset_eligibility)."""

from sqlmodel import Session

from application.portfolio.eligibility_service import check_asset_eligibility
from domain.entities import EligibleAsset


def _seed_asset(
    session: Session, *, wrapper: str, ticker: str, asset_type: str
) -> None:
    session.add(
        EligibleAsset(
            tax_wrapper=wrapper,
            ticker=ticker,
            fund_name=ticker,
            asset_type=asset_type,
            is_active=True,
        )
    )
    session.commit()


def test_bare_4digit_ticker_normalizes_to_dot_t(db_session: Session) -> None:
    """A bare 4-digit JP code ('7203') should be treated as '7203.T'."""
    _seed_asset(db_session, wrapper="nisa_growth", ticker="7203.T", asset_type="stock")

    result = check_asset_eligibility(db_session, ticker="7203", wrapper="nisa_growth")

    assert result.eligible is True
    assert result.asset_type == "stock"


def test_bare_4digit_not_in_approved_list_still_allowed(db_session: Session) -> None:
    """A bare 4-digit JP stock not in approved list passes (exclusion model)."""
    _seed_asset(db_session, wrapper="nisa_growth", ticker="2558.T", asset_type="etf")

    result = check_asset_eligibility(db_session, ticker="6758", wrapper="nisa_growth")

    assert result.eligible is True
    assert result.asset_type == "stock"


def test_non_stock_non_jp_ticker_not_in_approved_list_is_rejected(
    db_session: Session,
) -> None:
    """A non-JP ticker not in the ingested approved list is rejected."""
    _seed_asset(db_session, wrapper="nisa_growth", ticker="2558.T", asset_type="etf")

    result = check_asset_eligibility(db_session, ticker="AAPL", wrapper="nisa_growth")

    assert result.eligible is False
    assert "eligibility.not_in_growth_approved_list" in result.reasons


def test_full_width_4digit_reit_code_normalizes_to_dot_t(db_session: Session) -> None:
    """Full-width JP digit input (e.g. '８９５１') should normalize to '8951.T'."""
    _seed_asset(db_session, wrapper="nisa_growth", ticker="8951.T", asset_type="reit")

    result = check_asset_eligibility(
        db_session, ticker="８９５１", wrapper="nisa_growth"
    )

    assert result.eligible is True
    assert result.asset_type == "reit"


def test_full_width_dot_t_ticker_normalizes(db_session: Session) -> None:
    """Full-width digits + full-width period (e.g. '８９５１．Ｔ') should normalize to '8951.T'."""
    _seed_asset(db_session, wrapper="nisa_growth", ticker="8951.T", asset_type="reit")

    result = check_asset_eligibility(
        db_session, ticker="８９５１．Ｔ", wrapper="nisa_growth"
    )

    assert result.eligible is True
    assert result.asset_type == "reit"


def test_dot_t_ticker_in_approved_list_uses_ingested_asset_type(
    db_session: Session,
) -> None:
    """A .T ticker that is in the approved list uses the ingested asset_type, not 'stock'."""
    _seed_asset(db_session, wrapper="nisa_growth", ticker="1306.T", asset_type="etf")

    result = check_asset_eligibility(db_session, ticker="1306.T", wrapper="nisa_growth")

    assert result.eligible is True
    assert result.asset_type == "etf"
