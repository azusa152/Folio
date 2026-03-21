"""Tests for stock management routes (CRUD + signals)."""

from unittest.mock import patch

import pytest

from domain.entities import Stock
from domain.enums import StockCategory


class TestCreateStock:
    """Tests for POST /ticker."""

    def test_create_stock_should_return_201_equivalent(self, client):
        # Act
        resp = client.post(
            "/ticker",
            json={
                "ticker": "NVDA",
                "category": "Growth",
                "thesis": "AI leader",
                "tags": ["AI", "GPU"],
            },
        )

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["ticker"] == "NVDA"
        assert body["category"] == "Growth"
        assert body["is_active"] is True
        assert body["current_tags"] == ["AI", "GPU"]

    def test_create_stock_should_return_409_when_duplicate(self, client):
        # Arrange
        client.post(
            "/ticker",
            json={"ticker": "NVDA", "category": "Growth", "thesis": "AI leader"},
        )

        # Act
        resp = client.post(
            "/ticker",
            json={"ticker": "NVDA", "category": "Growth", "thesis": "Duplicate"},
        )

        # Assert
        assert resp.status_code == 409
        body = resp.json()
        assert body["detail"]["error_code"] == "STOCK_ALREADY_EXISTS"

    def test_create_stock_should_return_422_when_missing_fields(self, client):
        # Act
        resp = client.post("/ticker", json={"ticker": "NVDA"})

        # Assert
        assert resp.status_code == 422


class TestListStocks:
    """Tests for GET /stocks."""

    def test_list_stocks_should_return_empty_initially(self, client):
        # Act
        resp = client.get("/stocks")

        # Assert
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_stocks_should_return_added_stocks(self, client):
        # Arrange
        client.post(
            "/ticker",
            json={"ticker": "NVDA", "category": "Growth", "thesis": "AI leader"},
        )

        # Act
        resp = client.get("/stocks")

        # Assert
        assert resp.status_code == 200
        stocks = resp.json()
        assert len(stocks) == 1
        assert stocks[0]["ticker"] == "NVDA"

    def test_list_stocks_should_include_last_scan_signal(self, client):
        # Arrange — newly added stock defaults to NORMAL signal
        client.post(
            "/ticker",
            json={"ticker": "NVDA", "category": "Growth", "thesis": "AI leader"},
        )

        # Act
        resp = client.get("/stocks")

        # Assert
        assert resp.status_code == 200
        stock = resp.json()[0]
        assert "last_scan_signal" in stock
        assert stock["last_scan_signal"] == "NORMAL"

    def test_list_stocks_should_reflect_updated_scan_signal(self, client, db_session):
        # Arrange — seed stock directly via DB to control last_scan_signal precisely.
        # `client` and `db_session` share the same StaticPool connection (see conftest.py),
        # so writes committed here are visible to the TestClient's session.
        db_session.add(
            Stock(
                ticker="SNPS",
                category=StockCategory.MOAT,
                current_thesis="EDA leader",
                last_scan_signal="THESIS_BROKEN",
                is_active=True,
            )
        )
        db_session.commit()

        # Act
        resp = client.get("/stocks")

        # Assert
        assert resp.status_code == 200
        stock = next(s for s in resp.json() if s["ticker"] == "SNPS")
        assert stock["last_scan_signal"] == "THESIS_BROKEN"


class TestDeactivateStock:
    """Tests for POST /ticker/{ticker}/deactivate."""

    def test_deactivate_should_succeed(self, client):
        # Arrange
        client.post(
            "/ticker",
            json={"ticker": "NVDA", "category": "Growth", "thesis": "AI leader"},
        )

        # Act
        resp = client.post("/ticker/NVDA/deactivate", json={"reason": "Overvalued"})

        # Assert
        assert resp.status_code == 200
        assert "message" in resp.json()

    def test_deactivate_should_return_404_for_unknown_stock(self, client):
        # Act
        resp = client.post("/ticker/UNKNOWN/deactivate", json={"reason": "Test"})

        # Assert
        assert resp.status_code == 404
        assert resp.json()["detail"]["error_code"] == "STOCK_NOT_FOUND"

    def test_deactivate_should_return_409_when_already_inactive(self, client):
        # Arrange
        client.post(
            "/ticker",
            json={"ticker": "NVDA", "category": "Growth", "thesis": "AI leader"},
        )
        client.post("/ticker/NVDA/deactivate", json={"reason": "First deactivation"})

        # Act
        resp = client.post(
            "/ticker/NVDA/deactivate", json={"reason": "Second deactivation"}
        )

        # Assert
        assert resp.status_code == 409
        assert resp.json()["detail"]["error_code"] == "STOCK_ALREADY_INACTIVE"


class TestReactivateStock:
    """Tests for POST /ticker/{ticker}/reactivate."""

    def test_reactivate_should_succeed(self, client):
        # Arrange
        client.post(
            "/ticker",
            json={"ticker": "NVDA", "category": "Growth", "thesis": "AI leader"},
        )
        client.post("/ticker/NVDA/deactivate", json={"reason": "Test"})

        # Act
        resp = client.post("/ticker/NVDA/reactivate", json={})

        # Assert
        assert resp.status_code == 200

    def test_reactivate_should_return_409_when_already_active(self, client):
        # Arrange
        client.post(
            "/ticker",
            json={"ticker": "NVDA", "category": "Growth", "thesis": "AI leader"},
        )

        # Act
        resp = client.post("/ticker/NVDA/reactivate", json={})

        # Assert
        assert resp.status_code == 409
        assert resp.json()["detail"]["error_code"] == "STOCK_ALREADY_ACTIVE"


class TestUpdateCategory:
    """Tests for PATCH /ticker/{ticker}/category."""

    def test_update_category_should_succeed(self, client):
        # Arrange
        client.post(
            "/ticker",
            json={"ticker": "NVDA", "category": "Growth", "thesis": "AI leader"},
        )

        # Act
        resp = client.patch("/ticker/NVDA/category", json={"category": "Moat"})

        # Assert
        assert resp.status_code == 200

    def test_update_category_should_return_404_for_unknown_stock(self, client):
        # Act
        resp = client.patch("/ticker/UNKNOWN/category", json={"category": "Moat"})

        # Assert
        assert resp.status_code == 404
        assert resp.json()["detail"]["error_code"] == "STOCK_NOT_FOUND"

    def test_update_category_should_return_409_when_unchanged(self, client):
        # Arrange
        client.post(
            "/ticker",
            json={"ticker": "NVDA", "category": "Growth", "thesis": "AI leader"},
        )

        # Act
        resp = client.patch("/ticker/NVDA/category", json={"category": "Growth"})

        # Assert
        assert resp.status_code == 409
        assert resp.json()["detail"]["error_code"] == "CATEGORY_UNCHANGED"


class TestCreateStockETF:
    """Tests for is_etf field in POST /ticker."""

    def test_create_stock_should_default_is_etf_to_false(self, client):
        # Act — no is_etf provided, mock returns False
        resp = client.post(
            "/ticker",
            json={"ticker": "NVDA", "category": "Growth", "thesis": "AI leader"},
        )

        # Assert
        assert resp.status_code == 200
        assert resp.json()["is_etf"] is False

    def test_create_stock_should_accept_explicit_is_etf_true(self, client):
        # Act — explicitly pass is_etf=True
        resp = client.post(
            "/ticker",
            json={
                "ticker": "VTI",
                "category": "Trend_Setter",
                "thesis": "US Market ETF",
                "is_etf": True,
            },
        )

        # Assert
        assert resp.status_code == 200
        assert resp.json()["is_etf"] is True

    def test_export_should_include_is_etf_field(self, client):
        # Arrange
        client.post(
            "/ticker",
            json={
                "ticker": "VTI",
                "category": "Trend_Setter",
                "thesis": "ETF",
                "is_etf": True,
            },
        )

        # Act
        resp = client.get("/stocks/export")

        # Assert
        assert resp.status_code == 200
        exported = resp.json()
        assert len(exported) == 1
        assert exported[0]["is_etf"] is True

    def test_list_stocks_should_include_is_etf_field(self, client):
        # Arrange
        client.post(
            "/ticker",
            json={
                "ticker": "MSFT",
                "category": "Trend_Setter",
                "thesis": "Cloud",
            },
        )

        # Act
        resp = client.get("/stocks")

        # Assert
        assert resp.status_code == 200
        stocks = resp.json()
        assert len(stocks) == 1
        assert stocks[0]["is_etf"] is False


class TestGetSummary:
    """Tests for GET /summary."""

    def test_summary_should_return_plain_text(self, client):
        # Act
        resp = client.get("/summary")

        # Assert
        assert resp.status_code == 200
        assert "text/plain" in resp.headers["content-type"]


class TestPriceHistoryRoute:
    """Tests for GET /ticker/{ticker}/price-history."""

    @pytest.mark.slow
    def test_price_history_should_return_nav_data_for_mutual_fund(self, client):
        """Mutual_Fund stocks return NAV history from DB, not yfinance."""
        client.post(
            "/ticker",
            json={
                "ticker": "01311143",
                "category": "Mutual_Fund",
                "thesis": "NISA fund",
            },
        )

        with patch("application.stock.stock_service._get_price_history") as mock_ph:
            resp = client.get("/ticker/01311143/price-history")

        assert resp.status_code == 200
        # Returns (possibly empty) NAV history from DB, yfinance is never called
        assert isinstance(resp.json(), list)
        mock_ph.assert_not_called()

    def test_price_history_should_call_yfinance_for_regular_stock(self, client):
        """Regular stocks should still fetch price history normally."""
        client.post(
            "/ticker",
            json={
                "ticker": "AAPL",
                "category": "Growth",
                "thesis": "iPhone",
            },
        )

        resp = client.get("/ticker/AAPL/price-history")
        assert resp.status_code == 200


class TestCreateStockMutualFund:
    """Mutual_Fund stocks must skip detect_is_etf and trigger on-demand NAV sync."""

    @patch("api.routes.stock_routes.sync_single_fund_nav")
    def test_create_mutual_fund_should_skip_detect_is_etf(self, mock_nav_sync, client):
        with patch("application.stock.stock_service.detect_is_etf") as mock_detect:
            resp = client.post(
                "/ticker",
                json={
                    "ticker": "0131310B",
                    "category": "Mutual_Fund",
                    "thesis": "NISA fund",
                },
            )

        assert resp.status_code == 200
        assert resp.json()["is_etf"] is False
        mock_detect.assert_not_called()

    @patch("api.routes.stock_routes.sync_single_fund_nav")
    def test_create_mutual_fund_should_trigger_on_demand_nav_sync(
        self, mock_nav_sync, client
    ):
        resp = client.post(
            "/ticker",
            json={
                "ticker": "0131310B",
                "category": "Mutual_Fund",
                "thesis": "NISA fund",
            },
        )

        assert resp.status_code == 200
        mock_nav_sync.assert_called_once()

    @patch("api.routes.stock_routes.sync_single_fund_nav")
    def test_create_non_mf_should_not_trigger_nav_sync(self, mock_nav_sync, client):
        resp = client.post(
            "/ticker",
            json={
                "ticker": "AAPL",
                "category": "Growth",
                "thesis": "Tech stock",
            },
        )

        assert resp.status_code == 200
        mock_nav_sync.assert_not_called()


class TestSignalsRoute:
    """Tests for GET /ticker/{ticker}/signals."""

    def test_signals_should_return_nav_for_mutual_fund(self, client):
        from datetime import date

        from domain.entities import MutualFundNav

        with patch("api.routes.stock_routes.sync_single_fund_nav"):
            client.post(
                "/ticker",
                json={
                    "ticker": "0131310B",
                    "category": "Mutual_Fund",
                    "thesis": "NISA fund",
                },
            )

        from sqlmodel import Session as SqlSession

        from tests.conftest import test_engine

        with SqlSession(test_engine) as s:
            s.add(
                MutualFundNav(
                    fund_code="0131310B",
                    isin_code="JP90C000HR46",
                    nav_date=date(2026, 3, 14),
                    nav=15432.0,
                    nav_previous=15380.0,
                )
            )
            s.commit()

        with patch("application.stock.stock_service.get_technical_signals") as mock_yf:
            resp = client.get("/ticker/0131310B/signals")

        assert resp.status_code == 200
        body = resp.json()
        assert body.get("price") == 15432.0
        mock_yf.assert_not_called()


class TestFundamentalsRoute:
    """Tests for GET /ticker/{ticker}/fundamentals."""

    def test_get_fundamentals_should_return_200_with_shape(self, client):
        # Act
        resp = client.get("/ticker/NVDA/fundamentals")

        # Assert
        assert resp.status_code == 200
        body = resp.json()
        assert body["ticker"] == "NVDA"
        for key in [
            "trailing_pe",
            "forward_pe",
            "trailing_eps",
            "forward_eps",
            "market_cap",
            "price_to_book",
            "price_to_sales",
            "profit_margins",
            "operating_margins",
            "return_on_equity",
            "revenue_growth",
            "earnings_growth",
        ]:
            assert key in body

    @patch("api.routes.stock_routes.sync_single_fund_nav")
    def test_fundamentals_should_return_200_for_mutual_fund(self, _mock_nav, client):
        """Mutual_Fund stocks return ticker-only response, no yfinance call."""
        client.post(
            "/ticker",
            json={
                "ticker": "01313139",
                "category": "Mutual_Fund",
                "thesis": "NISA fund",
            },
        )

        with patch("application.stock.stock_service.get_fundamentals") as mock_yf:
            resp = client.get("/ticker/01313139/fundamentals")

        assert resp.status_code == 200
        body = resp.json()
        assert body["ticker"] == "01313139"
        assert body["trailing_pe"] is None
        assert body["market_cap"] is None
        mock_yf.assert_not_called()
