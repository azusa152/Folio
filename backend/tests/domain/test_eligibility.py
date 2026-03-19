"""Domain tests for wrapper eligibility rules."""

from domain.portfolio.eligibility import check_eligibility


def test_tokutei_always_eligible() -> None:
    result = check_eligibility(ticker="AAPL", wrapper="tokutei")
    assert result.eligible is True
    assert result.reasons == []


def test_tsumitate_approved_fund() -> None:
    result = check_eligibility(
        ticker="0331418A",
        wrapper="nisa_tsumitate",
        approved_tickers={"0331418A"},
    )
    assert result.eligible is True
    assert result.reasons == []


def test_tsumitate_unapproved_fund_suggests_growth() -> None:
    result = check_eligibility(
        ticker="AAPL",
        wrapper="nisa_tsumitate",
        approved_tickers={"0331418A"},
    )
    assert result.eligible is False
    assert "eligibility.not_in_tsumitate_approved_list" in result.reasons
    assert result.suggested_wrapper == "nisa_growth"


def test_growth_stock_eligible() -> None:
    result = check_eligibility(
        ticker="AAPL",
        wrapper="nisa_growth",
        asset_type="stock",
    )
    assert result.eligible is True
    assert result.reasons == []


def test_growth_leveraged_excluded() -> None:
    result = check_eligibility(
        ticker="SPXL",
        wrapper="nisa_growth",
        asset_type="etf",
        flags={"leveraged"},
    )
    assert result.eligible is False
    assert "eligibility.excluded_flag" in result.reasons


def test_growth_monthly_dist_excluded() -> None:
    result = check_eligibility(
        ticker="XYZFUND",
        wrapper="nisa_growth",
        asset_type="mutual_fund",
        flags={"monthly_distribution"},
    )
    assert result.eligible is False
    assert "eligibility.excluded_flag" in result.reasons


def test_growth_short_trust_period_excluded() -> None:
    result = check_eligibility(
        ticker="ABCD",
        wrapper="nisa_growth",
        asset_type="mutual_fund",
        trust_period_years=10,
    )
    assert result.eligible is False
    assert "eligibility.trust_period_too_short" in result.reasons


def test_ideco_in_lineup() -> None:
    result = check_eligibility(
        ticker="0331418A",
        wrapper="ideco",
        broker_lineup={"0331418A", "2931113C"},
    )
    assert result.eligible is True
    assert result.reasons == []


def test_ideco_not_in_lineup() -> None:
    result = check_eligibility(
        ticker="AAPL",
        wrapper="ideco",
        broker_lineup={"0331418A", "2931113C"},
    )
    assert result.eligible is False
    assert "eligibility.not_in_ideco_lineup" in result.reasons
    assert result.suggested_wrapper == "tokutei"
