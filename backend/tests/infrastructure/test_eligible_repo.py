"""Tests for EligibleAsset repository functions in eligible_repo.py.

Covers: upsert_eligible_assets, find_eligible_tickers,
        count_eligible_assets, find_isin_for_ticker.
"""

from collections.abc import Iterator

import pytest
from sqlmodel import Session

from infrastructure.repositories import (
    count_eligible_assets,
    find_eligible_tickers,
    find_isin_for_ticker,
    upsert_eligible_assets,
)

_WRAPPER = "test_eligible_repo_wrapper"

_SAMPLE_ROWS: list[dict] = [
    {
        "ticker": "ELIGREPO_A",
        "fund_name": "Eligible Repo Test Fund A",
        "asset_type": "mutual_fund",
        "trust_fee_pct": 0.1,
        "isin_code": "JP0000000001",
    },
    {
        "ticker": "ELIGREPO_B",
        "fund_name": "Eligible Repo Test Fund B",
        "asset_type": "etf",
        "trust_fee_pct": 0.05,
        "isin_code": None,
    },
]


@pytest.fixture
def test_session() -> Iterator[Session]:
    from tests.conftest import test_engine

    with Session(test_engine) as session:
        yield session


# ===========================================================================
# upsert_eligible_assets
# ===========================================================================


class TestUpsertEligibleAssets:
    def test_inserts_new_assets(self, test_session: Session):
        result = upsert_eligible_assets(
            test_session, _WRAPPER, _SAMPLE_ROWS, autocommit=False
        )
        test_session.commit()

        assert result["added"] >= 2
        assert count_eligible_assets(test_session, _WRAPPER) >= 2

    def test_upsert_is_idempotent(self, test_session: Session):
        upsert_eligible_assets(test_session, _WRAPPER, _SAMPLE_ROWS, autocommit=False)
        test_session.commit()
        count_before = count_eligible_assets(test_session, _WRAPPER)

        upsert_eligible_assets(test_session, _WRAPPER, _SAMPLE_ROWS, autocommit=False)
        test_session.commit()
        count_after = count_eligible_assets(test_session, _WRAPPER)

        # No new rows should be added on re-upsert with same data.
        assert count_after == count_before

    def test_returns_stats_dict(self, test_session: Session):
        result = upsert_eligible_assets(
            test_session, _WRAPPER, _SAMPLE_ROWS, autocommit=False
        )
        assert "added" in result
        assert "updated" in result
        assert "deactivated" in result

    def test_deactivates_missing_tickers(self, test_session: Session):
        upsert_eligible_assets(test_session, _WRAPPER, _SAMPLE_ROWS, autocommit=False)
        test_session.commit()

        # Re-upsert with only one ticker: the other should be deactivated.
        single_row = [_SAMPLE_ROWS[0]]
        result = upsert_eligible_assets(
            test_session, _WRAPPER, single_row, autocommit=False
        )
        test_session.commit()

        assert result["deactivated"] >= 1
        # Active count should reflect only the remaining row.
        assert count_eligible_assets(test_session, _WRAPPER) == 1

    def test_empty_rows_deactivates_all(self, test_session: Session):
        upsert_eligible_assets(test_session, _WRAPPER, _SAMPLE_ROWS, autocommit=False)
        test_session.commit()

        result = upsert_eligible_assets(test_session, _WRAPPER, [], autocommit=False)
        test_session.commit()

        assert result["deactivated"] >= 2
        assert count_eligible_assets(test_session, _WRAPPER) == 0


# ===========================================================================
# find_eligible_tickers
# ===========================================================================


class TestFindEligibleTickers:
    def test_returns_tickers_for_wrapper(self, test_session: Session):
        upsert_eligible_assets(test_session, _WRAPPER, _SAMPLE_ROWS, autocommit=False)
        test_session.commit()

        tickers = find_eligible_tickers(test_session, _WRAPPER)
        assert "ELIGREPO_A" in tickers
        assert "ELIGREPO_B" in tickers

    def test_returns_empty_for_unknown_wrapper(self, test_session: Session):
        tickers = find_eligible_tickers(test_session, "nonexistent_wrapper_xyz")
        assert tickers == set()

    def test_returns_set_type(self, test_session: Session):
        result = find_eligible_tickers(test_session, _WRAPPER)
        assert isinstance(result, set)


# ===========================================================================
# find_isin_for_ticker
# ===========================================================================


class TestFindIsinForTicker:
    def test_returns_isin_when_present(self, test_session: Session):
        upsert_eligible_assets(test_session, _WRAPPER, _SAMPLE_ROWS, autocommit=False)
        test_session.commit()

        isin = find_isin_for_ticker(test_session, "ELIGREPO_A")
        assert isin == "JP0000000001"

    def test_returns_none_when_isin_is_null(self, test_session: Session):
        upsert_eligible_assets(test_session, _WRAPPER, _SAMPLE_ROWS, autocommit=False)
        test_session.commit()

        isin = find_isin_for_ticker(test_session, "ELIGREPO_B")
        assert isin is None

    def test_returns_none_for_unknown_ticker(self, test_session: Session):
        isin = find_isin_for_ticker(test_session, "TOTALLY_UNKNOWN_ISIN_TICKER")
        assert isin is None

    def test_is_case_insensitive(self, test_session: Session):
        upsert_eligible_assets(test_session, _WRAPPER, _SAMPLE_ROWS, autocommit=False)
        test_session.commit()

        isin = find_isin_for_ticker(test_session, "eligrepo_a")
        assert isin == "JP0000000001"
