"""Tests for Stock repository functions in stock_repo.py.

Covers: find_stock_by_ticker, bulk_update_scan_signals,
        find_previous_distinct_signal.
"""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session

from domain.entities import ScanLog, Stock
from domain.enums import StockCategory
from infrastructure.repositories import (
    bulk_update_scan_signals,
    create_scan_log,
    find_stock_by_ticker,
    save_stock,
)


@pytest.fixture
def test_session() -> Iterator[Session]:
    from tests.conftest import test_engine

    with Session(test_engine) as session:
        yield session


@pytest.fixture(autouse=True)
def seed_stocks(test_session: Session):
    """Seed reusable test stocks before each test."""
    for ticker, cat in [
        ("STOCKREPO_A", StockCategory.MOAT),
        ("STOCKREPO_B", StockCategory.CRYPTO),
    ]:
        if test_session.get(Stock, ticker) is None:
            save_stock(test_session, Stock(ticker=ticker, category=cat))


# ===========================================================================
# find_stock_by_ticker
# ===========================================================================


class TestFindStockByTicker:
    def test_returns_stock_when_found(self, test_session: Session):
        result = find_stock_by_ticker(test_session, "STOCKREPO_A")
        assert result is not None
        assert result.ticker == "STOCKREPO_A"

    def test_returns_none_when_not_found(self, test_session: Session):
        assert find_stock_by_ticker(test_session, "NONEXISTENT_ZZZ") is None

    def test_returns_correct_category(self, test_session: Session):
        result = find_stock_by_ticker(test_session, "STOCKREPO_B")
        assert result is not None
        assert result.category == StockCategory.CRYPTO


# ===========================================================================
# bulk_update_scan_signals
# ===========================================================================


class TestBulkUpdateScanSignals:
    def test_updates_signal_for_known_ticker(self, test_session: Session):
        bulk_update_scan_signals(test_session, {"STOCKREPO_A": "DEEP_VALUE"})
        stock = find_stock_by_ticker(test_session, "STOCKREPO_A")
        assert stock is not None
        assert stock.last_scan_signal == "DEEP_VALUE"

    def test_noop_on_empty_dict(self, test_session: Session):
        # Should not raise
        bulk_update_scan_signals(test_session, {})

    def test_updates_signal_since_when_provided(self, test_session: Session):
        now = datetime.now(UTC)
        bulk_update_scan_signals(
            test_session,
            {"STOCKREPO_B": "OVERSOLD"},
            {"STOCKREPO_B": now},
        )
        stock = find_stock_by_ticker(test_session, "STOCKREPO_B")
        assert stock is not None
        assert stock.last_scan_signal == "OVERSOLD"
        assert stock.signal_since is not None

    def test_ignores_unknown_tickers_silently(self, test_session: Session):
        # No exception should be raised for a ticker that doesn't exist in the DB.
        bulk_update_scan_signals(test_session, {"TOTALLY_UNKNOWN_XYZ": "NORMAL"})

    def test_updates_multiple_tickers_in_one_call(self, test_session: Session):
        bulk_update_scan_signals(
            test_session,
            {"STOCKREPO_A": "CAUTION_HIGH", "STOCKREPO_B": "APPROACHING_BUY"},
        )
        a = find_stock_by_ticker(test_session, "STOCKREPO_A")
        b = find_stock_by_ticker(test_session, "STOCKREPO_B")
        assert a is not None
        assert a.last_scan_signal == "CAUTION_HIGH"
        assert b is not None
        assert b.last_scan_signal == "APPROACHING_BUY"


# ===========================================================================
# find_previous_distinct_signal
# ===========================================================================


class TestFindPreviousDistinctSignal:
    from infrastructure.repositories import find_previous_distinct_signal

    def test_returns_none_none_when_no_history(self, test_session: Session):
        from infrastructure.repositories import find_previous_distinct_signal

        prev, changed_at = find_previous_distinct_signal(
            test_session, "STOCKREPO_A", "NORMAL"
        )
        assert prev is None
        assert changed_at is None

    def test_finds_previous_distinct_signal(self, test_session: Session):
        from infrastructure.repositories import find_previous_distinct_signal

        now = datetime.now(UTC)
        # Older: OVERSOLD → newer: NORMAL
        for i, sig in enumerate(["OVERSOLD", "NORMAL", "NORMAL"]):
            create_scan_log(
                test_session,
                ScanLog(
                    stock_ticker="STOCKREPO_A",
                    signal=sig,
                    market_status="NEUTRAL",
                    scanned_at=now + timedelta(minutes=i),
                ),
            )
        test_session.commit()

        prev, changed_at = find_previous_distinct_signal(
            test_session, "STOCKREPO_A", "NORMAL"
        )
        assert prev == "OVERSOLD"
        assert changed_at is not None

    def test_returns_none_when_all_logs_have_same_signal(self, test_session: Session):
        from infrastructure.repositories import find_previous_distinct_signal

        now = datetime.now(UTC)
        for i in range(3):
            create_scan_log(
                test_session,
                ScanLog(
                    stock_ticker="STOCKREPO_B",
                    signal="DEEP_VALUE",
                    market_status="NEUTRAL",
                    scanned_at=now + timedelta(minutes=i),
                ),
            )
        test_session.commit()

        prev, _ = find_previous_distinct_signal(
            test_session, "STOCKREPO_B", "DEEP_VALUE"
        )
        assert prev is None
