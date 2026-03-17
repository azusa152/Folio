"""
Tests for new market-data wrapper methods added to stock_service.py.
All infrastructure.market_data calls are mocked — no network I/O.
"""

from unittest.mock import patch

import pytest

STOCK_MODULE = "application.stock.stock_service"


class TestGetSignalsForTicker:
    def test_returns_signals_with_bias_distribution(self, db_session) -> None:
        from domain.entities import Stock
        from infrastructure.repositories import save_stock

        save_stock(db_session, Stock(ticker="AAPL", category="Growth"))

        mock_signals = {"rsi": 55.0, "bias": 10.0}
        mock_dist = {"historical_biases": [1.0, 2.0], "count": 2}
        with (
            patch(f"{STOCK_MODULE}.get_technical_signals", return_value=mock_signals),
            patch(f"{STOCK_MODULE}.get_bias_distribution", return_value=mock_dist),
        ):
            from application.stock.stock_service import get_signals_for_ticker

            result = get_signals_for_ticker(db_session, "AAPL")

        assert result is not None
        assert result["rsi"] == 55.0
        assert result["bias_distribution"] == mock_dist

    def test_returns_signals_unchanged_when_signals_none(self, db_session) -> None:
        with (
            patch(f"{STOCK_MODULE}.get_technical_signals", return_value=None),
            patch(f"{STOCK_MODULE}.get_bias_distribution") as mock_dist,
        ):
            from application.stock.stock_service import get_signals_for_ticker

            result = get_signals_for_ticker(db_session, "AAPL")

        assert result is None
        mock_dist.assert_not_called()

    def test_returns_nav_for_mutual_fund(self, db_session) -> None:
        from datetime import date

        from domain.entities import MutualFundNav, Stock
        from domain.enums import StockCategory
        from infrastructure.repositories import save_stock

        save_stock(
            db_session,
            Stock(ticker="0131310B", category=StockCategory.MUTUAL_FUND),
        )
        db_session.add(
            MutualFundNav(
                fund_code="0131310B",
                isin_code="JP90C000HR46",
                nav_date=date(2026, 3, 14),
                nav=15432.0,
                nav_previous=15380.0,
            )
        )
        db_session.commit()

        with patch(f"{STOCK_MODULE}.get_technical_signals") as mock_yf:
            from application.stock.stock_service import get_signals_for_ticker

            result = get_signals_for_ticker(db_session, "0131310B")

        mock_yf.assert_not_called()
        assert result is not None
        assert result["price"] == 15432.0

    def test_returns_empty_for_skip_category(self, db_session) -> None:
        from domain.entities import Stock
        from infrastructure.repositories import save_stock

        save_stock(db_session, Stock(ticker="CASH_JPY", category="Cash"))

        with patch(f"{STOCK_MODULE}.get_technical_signals") as mock_yf:
            from application.stock.stock_service import get_signals_for_ticker

            result = get_signals_for_ticker(db_session, "CASH_JPY")

        mock_yf.assert_not_called()
        assert result == {}


class TestGetPriceHistoryForTicker:
    def test_delegates_to_yfinance_for_regular_stock(self, db_session) -> None:
        from domain.entities import Stock
        from infrastructure.repositories import save_stock

        save_stock(db_session, Stock(ticker="AAPL", category="Growth"))
        mock_history = [{"date": "2024-01-01", "close": 100.0}]
        with patch(f"{STOCK_MODULE}._get_price_history", return_value=mock_history):
            from application.stock.stock_service import get_price_history_for_ticker

            result = get_price_history_for_ticker(db_session, "AAPL")

        assert result == mock_history

    def test_returns_empty_for_unknown_ticker(self, db_session) -> None:
        with patch(f"{STOCK_MODULE}._get_price_history", return_value=None):
            from application.stock.stock_service import get_price_history_for_ticker

            result = get_price_history_for_ticker(db_session, "UNKNOWN")

        assert result == []


class TestGetEarningsForTicker:
    def test_returns_earnings_date(self, db_session) -> None:
        from domain.entities import Stock
        from infrastructure.repositories import save_stock

        save_stock(db_session, Stock(ticker="AAPL", category="Growth"))

        mock_earnings = {"next_earnings_date": "2025-04-30"}
        with patch(f"{STOCK_MODULE}.get_earnings_date", return_value=mock_earnings):
            from application.stock.stock_service import get_earnings_for_ticker

            result = get_earnings_for_ticker(db_session, "AAPL")

        assert result == mock_earnings

    def test_returns_none_when_not_available(self, db_session) -> None:
        from domain.entities import Stock
        from infrastructure.repositories import save_stock

        save_stock(db_session, Stock(ticker="AAPL", category="Growth"))

        with patch(f"{STOCK_MODULE}.get_earnings_date", return_value=None):
            from application.stock.stock_service import get_earnings_for_ticker

            result = get_earnings_for_ticker(db_session, "AAPL")

        assert result is None

    def test_skips_yfinance_for_mutual_fund(self, db_session) -> None:
        from domain.entities import Stock
        from infrastructure.repositories import save_stock

        save_stock(db_session, Stock(ticker="01313139", category="Mutual_Fund"))

        with patch(f"{STOCK_MODULE}.get_earnings_date") as mock_yf:
            from application.stock.stock_service import get_earnings_for_ticker

            result = get_earnings_for_ticker(db_session, "01313139")

        assert result is None
        mock_yf.assert_not_called()


class TestGetDividendForTicker:
    def test_returns_dividend_info(self, db_session) -> None:
        from domain.entities import Stock
        from infrastructure.repositories import save_stock

        save_stock(db_session, Stock(ticker="AAPL", category="Moat"))

        mock_div = {"yield": 0.5, "amount": 0.25}
        with patch(f"{STOCK_MODULE}.get_dividend_info", return_value=mock_div):
            from application.stock.stock_service import get_dividend_for_ticker

            result = get_dividend_for_ticker(db_session, "AAPL")

        assert result == mock_div

    def test_returns_none_when_not_available(self, db_session) -> None:
        from domain.entities import Stock
        from infrastructure.repositories import save_stock

        save_stock(db_session, Stock(ticker="AAPL", category="Moat"))

        with patch(f"{STOCK_MODULE}.get_dividend_info", return_value=None):
            from application.stock.stock_service import get_dividend_for_ticker

            result = get_dividend_for_ticker(db_session, "AAPL")

        assert result is None

    def test_skips_yfinance_for_mutual_fund(self, db_session) -> None:
        from domain.entities import Stock
        from infrastructure.repositories import save_stock

        save_stock(db_session, Stock(ticker="01313139", category="Mutual_Fund"))

        with patch(f"{STOCK_MODULE}.get_dividend_info") as mock_yf:
            from application.stock.stock_service import get_dividend_for_ticker

            result = get_dividend_for_ticker(db_session, "01313139")

        assert result is None
        mock_yf.assert_not_called()


class TestGetFundamentalsForTicker:
    def test_returns_fundamentals(self, db_session) -> None:
        from domain.entities import Stock
        from infrastructure.repositories import save_stock

        save_stock(db_session, Stock(ticker="AAPL", category="Growth"))

        payload = {"ticker": "AAPL", "trailing_pe": 22.3}
        with patch(f"{STOCK_MODULE}.get_fundamentals", return_value=payload):
            from application.stock.stock_service import get_fundamentals_for_ticker

            result = get_fundamentals_for_ticker(db_session, "AAPL")

        assert result == payload

    def test_skips_yfinance_for_mutual_fund(self, db_session) -> None:
        from domain.entities import Stock
        from infrastructure.repositories import save_stock

        save_stock(db_session, Stock(ticker="01313139", category="Mutual_Fund"))

        with patch(f"{STOCK_MODULE}.get_fundamentals") as mock_yf:
            from application.stock.stock_service import get_fundamentals_for_ticker

            result = get_fundamentals_for_ticker(db_session, "01313139")

        assert result == {"ticker": "01313139"}
        mock_yf.assert_not_called()


# ===========================================================================
# list_removed_stocks
# ===========================================================================


class TestListRemovedStocks:
    def test_returns_empty_when_no_inactive_stocks(self, db_session) -> None:
        from application.stock.stock_service import list_removed_stocks

        result = list_removed_stocks(db_session)
        assert result == []

    def test_returns_inactive_stock_with_removal_reason(self, db_session) -> None:
        from domain.entities import RemovalLog, Stock
        from domain.enums import StockCategory
        from infrastructure.repositories import save_stock

        stock = save_stock(
            db_session,
            Stock(ticker="REMOVED1", category=StockCategory.MOAT, is_active=False),
        )
        log = RemovalLog(stock_ticker=stock.ticker, reason="Thesis invalidated")
        db_session.add(log)
        db_session.commit()

        from application.stock.stock_service import list_removed_stocks

        result = list_removed_stocks(db_session)
        assert len(result) == 1
        assert result[0]["ticker"] == "REMOVED1"
        assert result[0]["removal_reason"] == "Thesis invalidated"

    def test_returns_unknown_reason_when_no_removal_log(self, db_session) -> None:
        from domain.entities import Stock
        from domain.enums import StockCategory
        from infrastructure.repositories import save_stock

        save_stock(
            db_session,
            Stock(ticker="REMOVED2", category=StockCategory.MOAT, is_active=False),
        )
        db_session.commit()

        from application.stock.stock_service import list_removed_stocks

        result = list_removed_stocks(db_session)
        match = next((r for r in result if r["ticker"] == "REMOVED2"), None)
        assert match is not None
        # No removal log → removal_reason should be a non-empty fallback string
        assert isinstance(match["removal_reason"], str)
        assert len(match["removal_reason"]) > 0


# ===========================================================================
# import_stocks
# ===========================================================================


class TestImportStocks:
    def test_creates_new_stock_on_import(self, db_session) -> None:
        with patch(f"{STOCK_MODULE}.detect_is_etf", return_value=False):
            from application.stock.stock_service import import_stocks

            result = import_stocks(
                db_session,
                [{"ticker": "NEW1", "category": "Growth", "thesis": "Strong growth"}],
            )

        assert result["created"] == 1
        assert result["updated"] == 0
        assert result["errors"] == []

    def test_updates_existing_stock_on_import(self, db_session) -> None:
        from domain.entities import Stock
        from domain.enums import StockCategory
        from infrastructure.repositories import save_stock

        save_stock(
            db_session,
            Stock(ticker="EXIST1", category=StockCategory.MOAT),
        )

        with patch(f"{STOCK_MODULE}.detect_is_etf", return_value=False):
            from application.stock.stock_service import import_stocks

            result = import_stocks(
                db_session,
                [{"ticker": "EXIST1", "category": "Moat", "thesis": "Updated thesis"}],
            )

        assert result["created"] == 0
        assert result["updated"] == 1

    def test_error_on_missing_ticker(self, db_session) -> None:
        from application.stock.stock_service import import_stocks

        result = import_stocks(db_session, [{"category": "Growth", "thesis": "Oops"}])

        assert result["created"] == 0
        assert len(result["errors"]) == 1

    def test_error_on_invalid_category(self, db_session) -> None:
        from application.stock.stock_service import import_stocks

        result = import_stocks(
            db_session,
            [{"ticker": "BAD1", "category": "INVALID_CAT", "thesis": "Bad category"}],
        )

        assert len(result["errors"]) == 1

    def test_is_etf_from_payload_overrides_auto_detect(self, db_session) -> None:
        with patch(f"{STOCK_MODULE}.detect_is_etf") as mock_detect:
            from application.stock.stock_service import import_stocks

            result = import_stocks(
                db_session,
                [
                    {
                        "ticker": "ETF1",
                        "category": "Growth",
                        "thesis": "",
                        "is_etf": True,
                    }
                ],
            )

        assert result["created"] == 1
        mock_detect.assert_not_called()

    def test_handles_empty_list(self, db_session) -> None:
        from application.stock.stock_service import import_stocks

        result = import_stocks(db_session, [])
        assert result["created"] == 0
        assert result["updated"] == 0


# ===========================================================================
# ensure_stock_on_radar
# ===========================================================================


class TestEnsureStockOnRadar:
    def test_active_existing_stock_should_autocorrect_to_mutual_fund_category(
        self, db_session
    ) -> None:
        from application.stock.stock_service import ensure_stock_on_radar
        from domain.entities import EligibleAsset, Stock
        from domain.enums import StockCategory
        from infrastructure import repositories as repo

        repo.save_stock(
            db_session,
            Stock(
                ticker="0131217A",
                category=StockCategory.GROWTH,
                current_thesis="Legacy",
                current_tags="",
                is_active=True,
                is_etf=False,
            ),
        )
        db_session.add(
            EligibleAsset(
                tax_wrapper="nisa_tsumitate",
                ticker="0131217A",
                fund_name="テスト投信",
                asset_type="mutual_fund",
                is_active=True,
            )
        )
        db_session.commit()

        with patch(f"{STOCK_MODULE}.detect_is_etf") as mock_detect:
            stock, created = ensure_stock_on_radar(db_session, "0131217A")

        assert created is False
        assert stock.category == StockCategory.MUTUAL_FUND
        assert stock.is_etf is False
        mock_detect.assert_not_called()

    def test_reactivate_inactive_stock_should_autocorrect_to_mutual_fund_category(
        self, db_session
    ) -> None:
        from application.stock.stock_service import ensure_stock_on_radar
        from domain.entities import EligibleAsset, Stock
        from domain.enums import StockCategory
        from infrastructure import repositories as repo

        repo.save_stock(
            db_session,
            Stock(
                ticker="0131217A",
                category=StockCategory.GROWTH,
                current_thesis="Legacy",
                current_tags="legacy",
                is_active=False,
                is_etf=False,
            ),
        )
        db_session.add(
            EligibleAsset(
                tax_wrapper="nisa_tsumitate",
                ticker="0131217A",
                fund_name="テスト投信",
                asset_type="mutual_fund",
                is_active=True,
            )
        )
        db_session.commit()

        with patch(f"{STOCK_MODULE}.detect_is_etf") as mock_detect:
            stock, created = ensure_stock_on_radar(db_session, "0131217A")

        assert created is True
        assert stock.is_active is True
        assert stock.category == StockCategory.MUTUAL_FUND
        assert stock.is_etf is False
        mock_detect.assert_not_called()

    def test_detects_eligible_mutual_fund_and_assigns_category(
        self, db_session
    ) -> None:
        from application.stock.stock_service import ensure_stock_on_radar
        from domain.entities import EligibleAsset
        from domain.enums import StockCategory

        db_session.add(
            EligibleAsset(
                tax_wrapper="nisa_tsumitate",
                ticker="0131217A",
                fund_name="テスト投信",
                asset_type="mutual_fund",
                is_active=True,
            )
        )
        db_session.commit()

        with patch(f"{STOCK_MODULE}.detect_is_etf", return_value=False):
            stock, created = ensure_stock_on_radar(db_session, "0131217A")

        assert created is True
        assert stock.category == StockCategory.MUTUAL_FUND
        assert stock.is_etf is False

    def test_creates_new_stock_with_thesis_and_etf_category(self, db_session) -> None:
        from application.stock.stock_service import ensure_stock_on_radar
        from domain.enums import StockCategory
        from infrastructure import repositories as repo

        with patch(f"{STOCK_MODULE}.detect_is_etf", return_value=True):
            stock, created = ensure_stock_on_radar(
                db_session, "vti", thesis=" Core ETF thesis "
            )

        history = repo.find_thesis_history(db_session, "VTI")
        assert created is True
        assert stock.ticker == "VTI"
        assert stock.category == StockCategory.TREND_SETTER
        assert stock.is_etf is True
        assert stock.current_thesis == "Core ETF thesis"
        assert len(history) == 1
        assert history[0].content == "Core ETF thesis"

    def test_uses_default_thesis_when_input_is_blank(self, db_session) -> None:
        from application.stock.stock_service import ensure_stock_on_radar
        from domain.enums import StockCategory

        with (
            patch(f"{STOCK_MODULE}.detect_is_etf", return_value=False),
            patch(f"{STOCK_MODULE}.t", return_value="Auto-tracked via transaction"),
        ):
            stock, created = ensure_stock_on_radar(db_session, "msft", thesis="   ")

        assert created is True
        assert stock.ticker == "MSFT"
        assert stock.category == StockCategory.GROWTH
        assert stock.current_thesis == "Auto-tracked via transaction"

    def test_returns_existing_stock_without_creating_new_thesis_log(
        self, db_session
    ) -> None:
        from application.stock.stock_service import ensure_stock_on_radar
        from domain.entities import Stock
        from domain.enums import StockCategory
        from infrastructure import repositories as repo

        existing = repo.save_stock(
            db_session,
            Stock(
                ticker="AAPL",
                category=StockCategory.GROWTH,
                current_thesis="Original thesis",
                current_tags="",
                is_active=True,
                is_etf=False,
            ),
        )

        stock, created = ensure_stock_on_radar(
            db_session, "AAPL", thesis="Should not overwrite"
        )
        history = repo.find_thesis_history(db_session, "AAPL")

        assert created is False
        assert stock.ticker == existing.ticker
        assert stock.current_thesis == "Original thesis"
        assert history == []

    def test_repairs_existing_active_stock_is_etf_when_detected(
        self, db_session
    ) -> None:
        from application.stock.stock_service import ensure_stock_on_radar
        from domain.entities import Stock
        from domain.enums import StockCategory
        from infrastructure import repositories as repo

        repo.save_stock(
            db_session,
            Stock(
                ticker="0050.TW",
                category=StockCategory.GROWTH,
                current_thesis="Legacy thesis",
                current_tags="",
                is_active=True,
                is_etf=False,
            ),
        )

        with patch(f"{STOCK_MODULE}.detect_is_etf", return_value=True):
            stock, created = ensure_stock_on_radar(db_session, "0050.TW")

        assert created is False
        assert stock.is_etf is True

    def test_reactivates_inactive_stock_and_marks_as_created(self, db_session) -> None:
        from application.stock.stock_service import ensure_stock_on_radar
        from domain.entities import Stock
        from domain.enums import StockCategory
        from infrastructure import repositories as repo

        repo.save_stock(
            db_session,
            Stock(
                ticker="QQQ",
                category=StockCategory.TREND_SETTER,
                current_thesis="Old thesis",
                current_tags="legacy",
                is_active=False,
                is_etf=True,
                last_scan_signal="THESIS_BROKEN",
            ),
        )

        stock, created = ensure_stock_on_radar(
            db_session, "QQQ", thesis="Reactivated thesis"
        )
        history = repo.find_thesis_history(db_session, "QQQ")

        assert created is True
        assert stock.is_active is True
        assert stock.category == StockCategory.TREND_SETTER
        assert stock.current_thesis == "Reactivated thesis"
        assert stock.current_tags == ""
        assert stock.last_scan_signal == "NORMAL"
        assert len(history) == 1
        assert history[0].content == "Reactivated thesis"

    def test_reactivate_with_blank_thesis_preserves_existing_thesis_and_tags(
        self, db_session
    ) -> None:
        from application.stock.stock_service import ensure_stock_on_radar
        from domain.entities import Stock
        from domain.enums import StockCategory
        from infrastructure import repositories as repo

        repo.save_stock(
            db_session,
            Stock(
                ticker="META",
                category=StockCategory.GROWTH,
                current_thesis="Original thesis",
                current_tags="ai,ads",
                is_active=False,
                is_etf=False,
                last_scan_signal="THESIS_BROKEN",
            ),
        )

        stock, created = ensure_stock_on_radar(db_session, "META", thesis="   ")
        history = repo.find_thesis_history(db_session, "META")

        assert created is True
        assert stock.is_active is True
        assert stock.current_thesis == "Original thesis"
        assert stock.current_tags == "ai,ads"
        assert stock.last_scan_signal == "NORMAL"
        assert len(history) == 1
        assert isinstance(history[0].content, str)
        assert len(history[0].content) > 0

    def test_reactivate_with_category_updates_stock_category(self, db_session) -> None:
        from application.stock.stock_service import ensure_stock_on_radar
        from domain.entities import Stock
        from domain.enums import StockCategory
        from infrastructure import repositories as repo

        repo.save_stock(
            db_session,
            Stock(
                ticker="CSCO",
                category=StockCategory.GROWTH,
                current_thesis="Old thesis",
                current_tags="legacy",
                is_active=False,
                is_etf=False,
                last_scan_signal="THESIS_BROKEN",
            ),
        )

        stock, created = ensure_stock_on_radar(
            db_session, "CSCO", thesis="Reactivated", category="Moat"
        )

        assert created is True
        assert stock.is_active is True
        assert stock.category == StockCategory.MOAT
        assert stock.current_thesis == "Reactivated"

    def test_invalid_category_should_raise_value_error(self, db_session) -> None:
        from application.stock.stock_service import ensure_stock_on_radar

        with (
            patch(f"{STOCK_MODULE}.detect_is_etf", return_value=False),
            pytest.raises(ValueError, match="Invalid_Category"),
        ):
            ensure_stock_on_radar(
                db_session,
                "AAPL",
                thesis="Any thesis",
                category="Invalid_Category",
            )


# ===========================================================================
# get_moat_for_ticker
# ===========================================================================


class TestGetMoatForTicker:
    def test_returns_na_for_bond_category(self, db_session) -> None:
        from domain.entities import Stock
        from domain.enums import StockCategory
        from infrastructure.repositories import save_stock

        save_stock(db_session, Stock(ticker="TLT", category=StockCategory.BOND))

        with patch(f"{STOCK_MODULE}.analyze_moat_trend") as mock_analyze:
            from application.stock.stock_service import get_moat_for_ticker

            result = get_moat_for_ticker(db_session, "TLT")

        assert result["moat"] == "N/A"
        assert "TLT" in result["ticker"]
        mock_analyze.assert_not_called()

    def test_returns_na_for_cash_category(self, db_session) -> None:
        from domain.entities import Stock
        from domain.enums import StockCategory
        from infrastructure.repositories import save_stock

        save_stock(db_session, Stock(ticker="CASH1", category=StockCategory.CASH))

        with patch(f"{STOCK_MODULE}.analyze_moat_trend") as mock_analyze:
            from application.stock.stock_service import get_moat_for_ticker

            result = get_moat_for_ticker(db_session, "CASH1")

        assert result["moat"] == "N/A"
        mock_analyze.assert_not_called()

    def test_delegates_to_analyze_moat_trend_for_moat_stocks(self, db_session) -> None:
        from domain.entities import Stock
        from domain.enums import StockCategory
        from infrastructure.repositories import save_stock

        save_stock(db_session, Stock(ticker="AAPL", category=StockCategory.MOAT))
        mock_moat = {"ticker": "AAPL", "moat": "護城河穩固", "yoy_change": 2.1}

        with patch(f"{STOCK_MODULE}.analyze_moat_trend", return_value=mock_moat):
            from application.stock.stock_service import get_moat_for_ticker

            result = get_moat_for_ticker(db_session, "AAPL")

        assert result["moat"] == "護城河穩固"

    def test_delegates_to_analyze_when_stock_not_in_db(self, db_session) -> None:
        """Stock not in DB should still call analyze_moat_trend (no category to skip)."""
        mock_moat = {"ticker": "UNKNOWN", "moat": "N/A"}

        with patch(f"{STOCK_MODULE}.analyze_moat_trend", return_value=mock_moat):
            from application.stock.stock_service import get_moat_for_ticker

            result = get_moat_for_ticker(db_session, "UNKNOWN")

        assert result["ticker"] == "UNKNOWN"


# ===========================================================================
# get_enriched_stocks
# ===========================================================================


class TestGetEnrichedStocks:
    def test_returns_empty_list_when_no_active_stocks(self, db_session) -> None:
        from application.stock.stock_service import get_enriched_stocks

        result = get_enriched_stocks(db_session)
        assert result == []

    def test_returns_enriched_data_for_active_stocks(self, db_session) -> None:
        from domain.entities import Stock
        from domain.enums import StockCategory
        from infrastructure.repositories import save_stock

        save_stock(db_session, Stock(ticker="NVDA", category=StockCategory.MOAT))

        mock_signals = {"rsi": 60.0, "bias": 5.0, "ma200": 100.0}
        mock_earnings = {"next_earnings_date": "2025-07-30"}
        mock_dividend = {"dividend_yield": 0.02}
        mock_fundamentals = {"market_cap": 123456789, "trailing_pe": 18.2}

        with (
            patch(f"{STOCK_MODULE}.get_technical_signals", return_value=mock_signals),
            patch(f"{STOCK_MODULE}.get_earnings_date", return_value=mock_earnings),
            patch(f"{STOCK_MODULE}.get_dividend_info", return_value=mock_dividend),
            patch(f"{STOCK_MODULE}.get_fundamentals", return_value=mock_fundamentals),
            patch(f"{STOCK_MODULE}.get_ticker_sector_cached", return_value=None),
        ):
            from application.stock.stock_service import get_enriched_stocks

            result = get_enriched_stocks(db_session)

        assert len(result) == 1
        assert result[0]["ticker"] == "NVDA"
        assert result[0]["signals"] == mock_signals
        assert result[0]["earnings"] == mock_earnings
        assert result[0]["dividend"] == mock_dividend
        assert result[0]["fundamentals"] == mock_fundamentals
        assert result[0]["market_cap"] == 123456789
        assert result[0]["trailing_pe"] == 18.2

    def test_force_refresh_should_recompute_cached_enriched_data(
        self, db_session
    ) -> None:
        from domain.entities import Stock
        from domain.enums import StockCategory
        from infrastructure.repositories import save_stock

        save_stock(db_session, Stock(ticker="AAPL", category=StockCategory.MOAT))

        with (
            patch(
                f"{STOCK_MODULE}.get_technical_signals",
                side_effect=[
                    {"rsi": 50.0, "bias": 1.0, "price": 100.0},
                    {"rsi": 60.0, "bias": 2.0, "price": 110.0},
                ],
            ) as mock_signals,
            patch(f"{STOCK_MODULE}.get_earnings_date", return_value=None),
            patch(f"{STOCK_MODULE}.get_dividend_info", return_value=None),
            patch(f"{STOCK_MODULE}.get_fundamentals", return_value=None),
            patch(f"{STOCK_MODULE}.get_ticker_sector_cached", return_value=None),
        ):
            from application.stock.stock_service import get_enriched_stocks

            first = get_enriched_stocks(db_session)
            refreshed = get_enriched_stocks(db_session, force_refresh=True)

        assert first[0]["price"] == 100.0
        assert refreshed[0]["price"] == 110.0
        assert mock_signals.call_count == 2

    def test_sector_field_included_in_enriched_response(self, db_session) -> None:
        """sector field from yfinance cache should be present in each enriched stock dict."""
        from domain.entities import Stock
        from domain.enums import StockCategory
        from infrastructure.repositories import save_stock

        save_stock(db_session, Stock(ticker="AAPL", category=StockCategory.MOAT))

        mock_signals = {"rsi": 55.0, "bias": 3.0, "price": 195.0, "change_pct": 1.2}

        with (
            patch(f"{STOCK_MODULE}.get_technical_signals", return_value=mock_signals),
            patch(f"{STOCK_MODULE}.get_earnings_date", return_value=None),
            patch(f"{STOCK_MODULE}.get_dividend_info", return_value=None),
            patch(f"{STOCK_MODULE}.get_fundamentals", return_value=None),
            patch(
                f"{STOCK_MODULE}.get_ticker_sector_cached", return_value="Technology"
            ),
        ):
            from application.stock.stock_service import get_enriched_stocks

            result = get_enriched_stocks(db_session)

        assert len(result) == 1
        item = result[0]
        assert item["sector"] == "Technology"
        assert item["price"] == 195.0
        assert item["change_pct"] == 1.2
        assert item["rsi"] == 55.0

    def test_sector_none_when_cache_miss(self, db_session) -> None:
        """sector should be None when not yet in disk cache (non-blocking)."""
        from domain.entities import Stock
        from domain.enums import StockCategory
        from infrastructure.repositories import save_stock

        save_stock(db_session, Stock(ticker="NOCACHE", category=StockCategory.GROWTH))

        with (
            patch(f"{STOCK_MODULE}.get_technical_signals", return_value=None),
            patch(f"{STOCK_MODULE}.get_earnings_date", return_value=None),
            patch(f"{STOCK_MODULE}.get_dividend_info", return_value=None),
            patch(f"{STOCK_MODULE}.get_fundamentals", return_value=None),
            patch(f"{STOCK_MODULE}.get_ticker_sector_cached", return_value=None),
        ):
            from application.stock.stock_service import get_enriched_stocks

            result = get_enriched_stocks(db_session)

        assert result[0]["sector"] is None

    def test_thesis_broken_signal_preserved(self, db_session) -> None:
        """Stocks with THESIS_BROKEN last_scan_signal should keep computed_signal='THESIS_BROKEN'."""
        from domain.entities import Stock
        from domain.enums import StockCategory
        from infrastructure.repositories import save_stock

        stock = Stock(
            ticker="BROKEN1",
            category=StockCategory.MOAT,
            last_scan_signal="THESIS_BROKEN",
        )
        save_stock(db_session, stock)

        mock_signals = {"rsi": 50.0, "bias": 2.0}

        with (
            patch(f"{STOCK_MODULE}.get_technical_signals", return_value=mock_signals),
            patch(f"{STOCK_MODULE}.get_earnings_date", return_value=None),
            patch(f"{STOCK_MODULE}.get_dividend_info", return_value=None),
            patch(f"{STOCK_MODULE}.get_fundamentals", return_value=None),
            patch(f"{STOCK_MODULE}.get_ticker_sector_cached", return_value=None),
        ):
            from application.stock.stock_service import get_enriched_stocks

            result = get_enriched_stocks(db_session)

        broken = next(r for r in result if r["ticker"] == "BROKEN1")
        assert broken["computed_signal"] == "THESIS_BROKEN"

    def test_signals_skipped_for_cash_category(self, db_session) -> None:
        """Cash category stocks should not have signals fetched."""
        from domain.entities import Stock
        from domain.enums import StockCategory
        from infrastructure.repositories import save_stock

        save_stock(db_session, Stock(ticker="CASH_A", category=StockCategory.CASH))

        with (
            patch(f"{STOCK_MODULE}.get_technical_signals") as mock_signals,
            patch(f"{STOCK_MODULE}.get_earnings_date", return_value=None),
            patch(f"{STOCK_MODULE}.get_dividend_info", return_value=None),
            patch(f"{STOCK_MODULE}.get_fundamentals", return_value=None),
            patch(f"{STOCK_MODULE}.get_ticker_sector_cached", return_value=None),
        ):
            from application.stock.stock_service import get_enriched_stocks

            result = get_enriched_stocks(db_session)

        assert len(result) == 1
        mock_signals.assert_not_called()
        assert result[0]["signals"] is None

    def test_signals_skipped_for_mutual_fund_category(self, db_session) -> None:
        """Mutual_Fund category stocks should not have yfinance signals fetched.

        When no NAV data exists in the DB, signals remain None.
        """
        from domain.entities import Stock
        from domain.enums import StockCategory
        from infrastructure.repositories import save_stock
        from tests.conftest import test_engine

        save_stock(
            db_session,
            Stock(ticker="0131217A", category=StockCategory.MUTUAL_FUND),
        )

        with (
            patch(f"{STOCK_MODULE}.engine", test_engine),
            patch(f"{STOCK_MODULE}.get_technical_signals") as mock_signals,
            patch(f"{STOCK_MODULE}.get_earnings_date", return_value=None),
            patch(f"{STOCK_MODULE}.get_dividend_info", return_value=None),
            patch(f"{STOCK_MODULE}.get_fundamentals", return_value=None),
            patch(f"{STOCK_MODULE}.get_ticker_sector_cached", return_value=None),
        ):
            from application.stock.stock_service import get_enriched_stocks

            result = get_enriched_stocks(db_session)

        assert len(result) == 1
        mock_signals.assert_not_called()
        assert result[0]["signals"] is None


class TestReclassifyMutualFundStocks:
    def test_reclassifies_active_growth_stocks_matching_eligible_fund_codes(
        self, db_session
    ) -> None:
        from application.stock.stock_service import reclassify_mutual_fund_stocks
        from domain.entities import EligibleAsset, Stock
        from domain.enums import StockCategory
        from infrastructure.repositories import save_stock

        save_stock(
            db_session,
            Stock(
                ticker="0131217A",
                category=StockCategory.GROWTH,
                is_active=True,
                is_etf=False,
            ),
        )
        save_stock(
            db_session,
            Stock(
                ticker="AAPL",
                category=StockCategory.GROWTH,
                is_active=True,
                is_etf=False,
            ),
        )
        db_session.add(
            EligibleAsset(
                tax_wrapper="nisa_tsumitate",
                ticker="0131217A",
                fund_name="テスト投信",
                asset_type="mutual_fund",
                is_active=True,
            )
        )
        db_session.commit()

        updated = reclassify_mutual_fund_stocks(db_session)

        assert updated == 1
        reclassified = db_session.get(Stock, "0131217A")
        assert reclassified is not None
        assert reclassified.category == StockCategory.MUTUAL_FUND
        unchanged = db_session.get(Stock, "AAPL")
        assert unchanged is not None
        assert unchanged.category == StockCategory.GROWTH
