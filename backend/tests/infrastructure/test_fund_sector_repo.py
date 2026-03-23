"""Tests for FundSectorWeight repository functions in fund_sector_repo.py.

Covers: get_sector_weights_for_funds, upsert_sector_weights, delete_sector_weights,
        find_all_fund_sector_weights.
"""

from collections.abc import Iterator

import pytest
from sqlmodel import Session

from infrastructure.persistence.repositories.fund_sector_repo import (
    find_all_fund_sector_weights,
)
from infrastructure.repositories import (
    delete_sector_weights,
    get_sector_weights_for_funds,
    upsert_sector_weights,
)


@pytest.fixture
def test_session() -> Iterator[Session]:
    from tests.conftest import test_engine

    with Session(test_engine) as session:
        yield session


_FUND_A = "TESTFUNDA"
_FUND_B = "TESTFUNDB"

_WEIGHTS_A = {"Technology": 0.30, "Industrials": 0.20, "Healthcare": 0.15}
_WEIGHTS_B = {"Financial Services": 0.40, "Consumer Cyclical": 0.25}


class TestUpsertSectorWeights:
    def test_should_insert_new_weights(self, test_session: Session) -> None:
        rows = upsert_sector_weights(test_session, _FUND_A, _WEIGHTS_A, source="seed")

        assert len(rows) == 3
        stored = get_sector_weights_for_funds(test_session, [_FUND_A])
        assert stored[_FUND_A] == _WEIGHTS_A

    def test_should_normalize_fund_code_to_uppercase(
        self, test_session: Session
    ) -> None:
        upsert_sector_weights(test_session, "lowercase_fund", {"Technology": 0.5})
        stored = get_sector_weights_for_funds(test_session, ["LOWERCASE_FUND"])
        assert "LOWERCASE_FUND" in stored

    def test_should_replace_existing_weights(self, test_session: Session) -> None:
        upsert_sector_weights(test_session, _FUND_A, _WEIGHTS_A, source="seed")
        new_weights = {"Energy": 0.60, "Utilities": 0.40}
        upsert_sector_weights(test_session, _FUND_A, new_weights, source="manual")

        stored = get_sector_weights_for_funds(test_session, [_FUND_A])
        assert stored[_FUND_A] == new_weights
        # Old sectors should be gone
        assert "Technology" not in stored[_FUND_A]

    def test_should_persist_source_field(self, test_session: Session) -> None:
        from sqlmodel import select

        from domain.core.entities import FundSectorWeight

        upsert_sector_weights(test_session, _FUND_A, _WEIGHTS_A, source="proxy_etf")
        row = test_session.exec(
            select(FundSectorWeight).where(
                FundSectorWeight.fund_code == _FUND_A,
                FundSectorWeight.sector == "Technology",
            )
        ).first()
        assert row is not None
        assert row.source == "proxy_etf"


class TestGetSectorWeightsForFunds:
    def test_should_return_empty_dict_for_empty_input(
        self, test_session: Session
    ) -> None:
        result = get_sector_weights_for_funds(test_session, [])
        assert result == {}

    def test_should_return_empty_when_no_data_for_fund(
        self, test_session: Session
    ) -> None:
        result = get_sector_weights_for_funds(test_session, ["NONEXISTENT"])
        assert result == {}

    def test_should_batch_load_multiple_funds(self, test_session: Session) -> None:
        upsert_sector_weights(test_session, _FUND_A, _WEIGHTS_A)
        upsert_sector_weights(test_session, _FUND_B, _WEIGHTS_B)

        result = get_sector_weights_for_funds(test_session, [_FUND_A, _FUND_B])
        assert result[_FUND_A] == _WEIGHTS_A
        assert result[_FUND_B] == _WEIGHTS_B

    def test_should_return_only_requested_funds(self, test_session: Session) -> None:
        upsert_sector_weights(test_session, _FUND_A, _WEIGHTS_A)
        upsert_sector_weights(test_session, _FUND_B, _WEIGHTS_B)

        result = get_sector_weights_for_funds(test_session, [_FUND_A])
        assert _FUND_A in result
        assert _FUND_B not in result


class TestDeleteSectorWeights:
    def test_should_delete_all_weights_for_fund(self, test_session: Session) -> None:
        upsert_sector_weights(test_session, _FUND_A, _WEIGHTS_A)
        count = delete_sector_weights(test_session, _FUND_A)

        assert count == len(_WEIGHTS_A)
        stored = get_sector_weights_for_funds(test_session, [_FUND_A])
        assert stored == {}

    def test_should_return_zero_when_no_rows_exist(self, test_session: Session) -> None:
        count = delete_sector_weights(test_session, "GHOST")
        assert count == 0

    def test_should_not_affect_other_funds(self, test_session: Session) -> None:
        upsert_sector_weights(test_session, _FUND_A, _WEIGHTS_A)
        upsert_sector_weights(test_session, _FUND_B, _WEIGHTS_B)
        delete_sector_weights(test_session, _FUND_A)

        stored = get_sector_weights_for_funds(test_session, [_FUND_B])
        assert _FUND_B in stored


class TestFindAllFundSectorWeights:
    def test_should_group_by_fund_code(self, test_session: Session) -> None:
        upsert_sector_weights(test_session, _FUND_A, _WEIGHTS_A)
        upsert_sector_weights(test_session, _FUND_B, _WEIGHTS_B)

        result = find_all_fund_sector_weights(test_session)
        assert _FUND_A in result
        assert _FUND_B in result
        assert len(result[_FUND_A]) == len(_WEIGHTS_A)

    def test_should_return_empty_when_no_data(self, test_session: Session) -> None:
        result = find_all_fund_sector_weights(test_session)
        # May contain other test data but not our fund codes
        assert _FUND_A not in result
