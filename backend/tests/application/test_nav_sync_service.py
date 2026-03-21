"""Tests for the mutual fund NAV sync service."""

from datetime import date
from unittest.mock import patch

import pytest
from sqlmodel import Session

import application.portfolio.nav_sync_service as nav_sync_module
from domain.entities import EligibleAsset, MutualFundNav, Stock
from domain.enums import StockCategory
from tests.conftest import test_engine


def _seed_mutual_fund(session: Session, ticker: str, isin: str) -> None:
    """Seed a Mutual_Fund stock and its eligible asset record."""
    session.add(
        Stock(
            ticker=ticker,
            category=StockCategory.MUTUAL_FUND,
            is_active=True,
        )
    )
    session.add(
        EligibleAsset(
            tax_wrapper="nisa_growth",
            ticker=ticker,
            fund_name="Test Fund",
            asset_type="mutual_fund",
            isin_code=isin,
            is_active=True,
        )
    )
    session.commit()


class TestSyncSingleFundNav:
    def test_should_upsert_nav_for_single_fund(self, db_session):
        """On-demand sync should fetch and upsert NAV for one fund."""
        _seed_mutual_fund(db_session, "0131310B", "JP90C000HR46")

        fake_csv = [
            {"date": date(2026, 3, 14), "nav": 15432.0, "net_assets": 1200.0},
            {"date": date(2026, 3, 13), "nav": 15380.0, "net_assets": 1190.0},
        ]

        with patch.object(nav_sync_module, "fetch_fund_nav_csv", return_value=fake_csv):
            result = nav_sync_module.sync_single_fund_nav(db_session, "0131310B")

        assert result is True

        from sqlmodel import select

        navs = list(
            db_session.exec(
                select(MutualFundNav).where(MutualFundNav.fund_code == "0131310B")
            ).all()
        )
        assert len(navs) >= 1

    @pytest.mark.slow
    def test_should_return_false_when_no_isin(self, db_session):
        """Fund without ISIN should return False."""
        db_session.add(
            Stock(
                ticker="NOISINFUND",
                category=StockCategory.MUTUAL_FUND,
                is_active=True,
            )
        )
        db_session.commit()

        with patch.object(nav_sync_module, "lookup_isin", return_value=None):
            result = nav_sync_module.sync_single_fund_nav(db_session, "NOISINFUND")
        assert result is False

    def test_should_use_isin_fallback_from_toushin_lib(self, db_session):
        """When DB has no ISIN, fallback to toushin-lib lookup."""
        db_session.add(
            Stock(
                ticker="01311143",
                category=StockCategory.MUTUAL_FUND,
                is_active=True,
            )
        )
        db_session.add(
            EligibleAsset(
                tax_wrapper="nisa_growth",
                ticker="01311143",
                fund_name="Test Fund",
                asset_type="mutual_fund",
                isin_code=None,
                is_active=True,
            )
        )
        db_session.commit()

        fake_csv = [
            {"date": date(2026, 3, 14), "nav": 10074.0, "net_assets": 100.0},
        ]

        with (
            patch.object(nav_sync_module, "lookup_isin", return_value="JP90C000A808"),
            patch.object(nav_sync_module, "fetch_fund_nav_csv", return_value=fake_csv),
        ):
            result = nav_sync_module.sync_single_fund_nav(db_session, "01311143")

        assert result is True

    def test_should_resolve_legacy_fund_name_ticker(self, db_session):
        """Legacy fund-name ticker should be resolved to fund code."""
        db_session.add(
            Stock(
                ticker="EMAXIS S&P500",
                category=StockCategory.MUTUAL_FUND,
                is_active=True,
            )
        )
        db_session.commit()

        fake_csv = [
            {"date": date(2026, 3, 14), "nav": 25000.0, "net_assets": 5000.0},
        ]

        with (
            patch.object(
                nav_sync_module, "resolve_fund_code_from_name", return_value="0331220C"
            ),
            patch.object(nav_sync_module, "lookup_isin", return_value="JP90C000L110"),
            patch.object(
                nav_sync_module, "fetch_fund_nav_csv", return_value=fake_csv
            ) as mock_fetch,
        ):
            result = nav_sync_module.sync_single_fund_nav(db_session, "EMAXIS S&P500")

        assert result is True
        mock_fetch.assert_called_once_with("0331220C", "JP90C000L110")

    def test_should_use_db_fund_code_for_legacy_ticker_when_isin_exists(
        self, db_session
    ):
        """When legacy ticker already has ISIN, resolve fund code from DB (no API)."""
        db_session.add(
            Stock(
                ticker="EMAXIS S&P500",
                category=StockCategory.MUTUAL_FUND,
                is_active=True,
            )
        )
        db_session.add(
            EligibleAsset(
                tax_wrapper="nisa_growth",
                ticker="EMAXIS S&P500",
                fund_name="EMAXIS S&P500",
                asset_type="mutual_fund",
                isin_code="JP90C000L110",
                is_active=True,
            )
        )
        db_session.add(
            EligibleAsset(
                tax_wrapper="nisa_growth",
                ticker="0331220C",
                fund_name="EMAXIS S&P500",
                asset_type="mutual_fund",
                isin_code="JP90C000L110",
                is_active=True,
            )
        )
        db_session.commit()

        fake_csv = [
            {"date": date(2026, 3, 14), "nav": 25000.0, "net_assets": 5000.0},
        ]

        with (
            patch.object(
                nav_sync_module, "resolve_fund_code_from_name", return_value=None
            ) as mock_resolve_name,
            patch.object(
                nav_sync_module, "lookup_isin", return_value=None
            ) as mock_lookup,
            patch.object(
                nav_sync_module, "fetch_fund_nav_csv", return_value=fake_csv
            ) as mock_fetch,
        ):
            result = nav_sync_module.sync_single_fund_nav(db_session, "EMAXIS S&P500")

        assert result is True
        mock_fetch.assert_called_once_with("0331220C", "JP90C000L110")
        mock_resolve_name.assert_not_called()
        mock_lookup.assert_not_called()

    def test_should_return_false_when_csv_empty(self, db_session):
        """Empty CSV result should return False."""
        _seed_mutual_fund(db_session, "0131310B", "JP90C000HR46")

        with patch.object(nav_sync_module, "fetch_fund_nav_csv", return_value=None):
            result = nav_sync_module.sync_single_fund_nav(db_session, "0131310B")

        assert result is False

    def test_should_not_raise_on_fetch_error(self, db_session):
        """Network errors should be caught gracefully."""
        _seed_mutual_fund(db_session, "0131310B", "JP90C000HR46")

        with patch.object(
            nav_sync_module,
            "fetch_fund_nav_csv",
            side_effect=RuntimeError("network down"),
        ):
            result = nav_sync_module.sync_single_fund_nav(db_session, "0131310B")

        assert result is False


class TestSyncMutualFundNavs:
    def test_should_upsert_nav_rows(self, db_session):
        """NAV rows from toushin-lib should be written to DB."""
        _seed_mutual_fund(db_session, "0131310B", "JP90C000HR46")

        fake_csv = [
            {"date": date(2026, 3, 14), "nav": 15432.0, "net_assets": 1200.0},
            {"date": date(2026, 3, 13), "nav": 15380.0, "net_assets": 1190.0},
        ]

        with (
            patch.object(nav_sync_module, "engine", test_engine),
            patch.object(
                nav_sync_module,
                "fetch_fund_nav_csv",
                return_value=fake_csv,
            ),
        ):
            result = nav_sync_module.sync_mutual_fund_navs()

        assert result["synced"] == 1
        assert result["failed"] == 0
        assert result["failed_tickers"] == []
        assert result["failed_details"] == []

        # Verify rows were actually written
        from sqlmodel import select

        navs = list(
            db_session.exec(
                select(MutualFundNav).where(MutualFundNav.fund_code == "0131310B")
            ).all()
        )
        assert len(navs) >= 1

    def test_should_count_failed_when_no_isin(self, db_session):
        """Stocks without ISIN should count as failed."""
        db_session.add(
            Stock(
                ticker="NOISINFUND",
                category=StockCategory.MUTUAL_FUND,
                is_active=True,
            )
        )
        db_session.commit()

        with (
            patch.object(nav_sync_module, "engine", test_engine),
            patch.object(nav_sync_module, "lookup_isin", return_value=None),
        ):
            result = nav_sync_module.sync_mutual_fund_navs()

        assert result["failed"] == 1
        assert result["synced"] == 0
        assert result["failed_tickers"] == ["NOISINFUND"]
        assert result["failed_details"] == [
            {"ticker": "NOISINFUND", "reason": "missing_isin"}
        ]

    def test_should_return_zero_when_no_mutual_funds(self, db_session):
        """No Mutual_Fund stocks means nothing to sync."""
        db_session.add(
            Stock(
                ticker="AAPL",
                category=StockCategory.GROWTH,
                is_active=True,
            )
        )
        db_session.commit()

        with patch.object(nav_sync_module, "engine", test_engine):
            result = nav_sync_module.sync_mutual_fund_navs()

        assert result["synced"] == 0
        assert result["failed"] == 0
        assert result["failed_tickers"] == []
        assert result["failed_details"] == []

    def test_should_use_isin_from_inactive_eligible_asset(self, db_session):
        """Fallback lookup should recover ISIN from inactive eligible row."""
        db_session.add(
            Stock(
                ticker="0131310B",
                category=StockCategory.MUTUAL_FUND,
                is_active=True,
            )
        )
        db_session.add(
            EligibleAsset(
                tax_wrapper="nisa_growth",
                ticker="0131310B",
                fund_name="Test Fund",
                asset_type="mutual_fund",
                isin_code="JP90C000HR46",
                is_active=False,
            )
        )
        db_session.commit()

        fake_csv = [
            {"date": date(2026, 3, 14), "nav": 15432.0, "net_assets": 1200.0},
            {"date": date(2026, 3, 13), "nav": 15380.0, "net_assets": 1190.0},
        ]

        with (
            patch.object(nav_sync_module, "engine", test_engine),
            patch.object(nav_sync_module, "fetch_fund_nav_csv", return_value=fake_csv),
        ):
            result = nav_sync_module.sync_mutual_fund_navs()

        assert result["synced"] == 1
        assert result["failed"] == 0
