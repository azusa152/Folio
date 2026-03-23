"""
Tests for Mutual_Fund sector look-through using DB sector weight overrides.

Covers:
- Mutual_Fund with DB sector weights distributes MV by stored weights.
- Mutual_Fund without DB weights falls through to get_ticker_sector → "Unknown".
- Mixed portfolio: fund with weights + direct stock combined correctly.
- Balanced fund with partial equity weights (weights sum < 1.0) included correctly.
"""

import json
from unittest.mock import patch

import pytest
from sqlmodel import Session

from application.portfolio.rebalance_service import calculate_rebalance
from domain.core.entities import Account, Holding, Stock, UserInvestmentProfile
from domain.enums import StockCategory
from infrastructure.repositories import upsert_sector_weights

_MOCK_SIGNALS = {
    "price": 100.0,
    "previous_close": 100.0,
    "change_pct": 0.0,
    "rsi": 50.0,
    "ma200": 90.0,
    "ma60": 95.0,
    "bias": 0.0,
    "volume_ratio": 1.0,
    "status": [],
}

_BASE_PATCHES = [
    "application.portfolio.rebalance_service.prewarm_signals_batch",
    "application.portfolio.rebalance_service.prewarm_etf_holdings_batch",
    "application.portfolio.rebalance_service.get_forex_history",
    "application.portfolio.rebalance_service.get_forex_history_long",
]


def _seed_account(session: Session) -> Account:
    account = Account(
        user_id="default",
        name="Test",
        broker="Test",
        account_type="brokerage",
        currency="USD",
    )
    session.add(account)
    session.flush()
    return account


def _add_profile(session: Session) -> None:
    session.add(
        UserInvestmentProfile(
            user_id="default",
            config=json.dumps({"Mutual_Fund": 100}),
            is_active=True,
        )
    )


def _add_mf_holding(
    session: Session,
    ticker: str,
    quantity: float = 100.0,
    *,
    account_id: int | None = None,
) -> None:
    session.add(
        Holding(
            user_id="default",
            ticker=ticker,
            category=StockCategory.MUTUAL_FUND,
            quantity=quantity,
            cost_basis=100.0,
            currency="USD",
            is_cash=False,
            account_id=account_id,
        )
    )


def _add_stock(session: Session, ticker: str) -> None:
    session.add(
        Stock(
            ticker=ticker,
            category=StockCategory.MUTUAL_FUND,
            is_etf=False,
        )
    )


class TestFundSectorLookthrough:
    """Sector exposure correctly uses DB sector weight overrides for Mutual_Fund."""

    @patch("application.portfolio.rebalance_service.get_etf_sector_weights")
    @patch("application.portfolio.rebalance_service.get_etf_top_holdings")
    @patch("application.portfolio.rebalance_service.get_ticker_sector")
    @patch("application.portfolio.rebalance_service.get_exchange_rates")
    @patch("application.portfolio.pricing_service.get_technical_signals")
    @patch("application.portfolio.rebalance_service.prewarm_etf_sector_weights_batch")
    @patch("application.portfolio.rebalance_service.prewarm_etf_holdings_batch")
    @patch("application.portfolio.rebalance_service.prewarm_signals_batch")
    def test_should_distribute_mv_by_stored_sector_weights(
        self,
        _mock_prewarm_signals,
        _mock_prewarm_etf,
        _mock_prewarm_etf_sw,
        mock_signals,
        mock_fx,
        mock_sector,
        mock_etf_holdings,
        mock_etf_weights,
        db_session: Session,
    ) -> None:
        """Mutual_Fund with DB sector weights: MV distributed proportionally."""
        # Arrange
        acct = _seed_account(db_session)
        _add_profile(db_session)
        _add_mf_holding(db_session, "01311143", quantity=100.0, account_id=acct.id)
        _add_stock(db_session, "01311143")
        upsert_sector_weights(
            db_session,
            "01311143",
            {"Technology": 0.40, "Industrials": 0.35, "Healthcare": 0.25},
            source="seed",
        )
        db_session.commit()

        mock_signals.return_value = {**_MOCK_SIGNALS, "price": 10.0}
        mock_fx.return_value = {"USD": 1.0}
        mock_etf_holdings.return_value = None
        mock_etf_weights.return_value = None

        # Act
        result = calculate_rebalance(db_session, "USD")

        # Assert: fund MV distributed by stored weights.
        # MUTUAL_FUND with no NAV data falls back to cost_basis for MV:
        # qty=100 * cost_basis=100.0 = 10000
        sector_map = {s["sector"]: s for s in result["sector_exposure"]}
        total_mv = 100.0 * 100.0  # qty * cost_basis (no NAV seeded)

        assert "Technology" in sector_map
        assert "Industrials" in sector_map
        assert "Healthcare" in sector_map
        assert "Unknown" not in sector_map

        assert sector_map["Technology"]["value"] == pytest.approx(
            total_mv * 0.40, rel=0.01
        )
        assert sector_map["Industrials"]["value"] == pytest.approx(
            total_mv * 0.35, rel=0.01
        )
        assert sector_map["Healthcare"]["value"] == pytest.approx(
            total_mv * 0.25, rel=0.01
        )
        # Verify get_ticker_sector was NOT called for the fund ticker
        mock_sector.assert_not_called()

    @patch("application.portfolio.rebalance_service.get_etf_sector_weights")
    @patch("application.portfolio.rebalance_service.get_etf_top_holdings")
    @patch("application.portfolio.rebalance_service.detect_is_etf", return_value=False)
    @patch("application.portfolio.rebalance_service.get_ticker_sector")
    @patch("application.portfolio.rebalance_service.get_exchange_rates")
    @patch("application.portfolio.pricing_service.get_technical_signals")
    @patch("application.portfolio.rebalance_service.prewarm_etf_sector_weights_batch")
    @patch("application.portfolio.rebalance_service.prewarm_etf_holdings_batch")
    @patch("application.portfolio.rebalance_service.prewarm_signals_batch")
    def test_should_fall_back_to_unknown_when_no_db_weights(
        self,
        _mock_prewarm_signals,
        _mock_prewarm_etf,
        _mock_prewarm_etf_sw,
        mock_signals,
        mock_fx,
        mock_sector,
        _mock_detect_etf,
        mock_etf_holdings,
        mock_etf_weights,
        db_session: Session,
    ) -> None:
        """Mutual_Fund without DB weights falls through to get_ticker_sector."""
        # Arrange
        acct = _seed_account(db_session)
        _add_profile(db_session)
        _add_mf_holding(db_session, "01311143", quantity=100.0, account_id=acct.id)
        _add_stock(db_session, "01311143")
        # No upsert — no DB weights
        db_session.commit()

        mock_signals.return_value = {**_MOCK_SIGNALS, "price": 10.0}
        mock_fx.return_value = {"USD": 1.0}
        mock_etf_holdings.return_value = None
        mock_etf_weights.return_value = None
        mock_sector.return_value = None  # yfinance returns None → "Unknown"

        # Act
        result = calculate_rebalance(db_session, "USD")

        # Assert: falls through to Unknown
        sector_map = {s["sector"]: s for s in result["sector_exposure"]}
        assert "Unknown" in sector_map

    @patch("application.portfolio.rebalance_service.get_etf_sector_weights")
    @patch("application.portfolio.rebalance_service.get_etf_top_holdings")
    @patch("application.portfolio.rebalance_service.detect_is_etf", return_value=False)
    @patch("application.portfolio.rebalance_service.get_ticker_sector")
    @patch("application.portfolio.rebalance_service.get_exchange_rates")
    @patch("application.portfolio.pricing_service.get_technical_signals")
    @patch("application.portfolio.rebalance_service.prewarm_etf_sector_weights_batch")
    @patch("application.portfolio.rebalance_service.prewarm_etf_holdings_batch")
    @patch("application.portfolio.rebalance_service.prewarm_signals_batch")
    def test_balanced_fund_partial_weights_included_correctly(
        self,
        _mock_prewarm_signals,
        _mock_prewarm_etf,
        _mock_prewarm_etf_sw,
        mock_signals,
        mock_fx,
        mock_sector,
        _mock_detect_etf,
        mock_etf_holdings,
        mock_etf_weights,
        db_session: Session,
    ) -> None:
        """Balanced fund: weights sum < 1.0 (equity portion only); non-equity excluded."""
        # Arrange
        acct = _seed_account(db_session)
        _add_profile(db_session)
        _add_mf_holding(db_session, "01312179", quantity=100.0, account_id=acct.id)
        _add_stock(db_session, "01312179")
        # 6-asset balanced fund: equity ~33% of total NAV
        equity_weights = {
            "Industrials": 0.11,
            "Technology": 0.10,
            "Financial Services": 0.09,
        }
        upsert_sector_weights(db_session, "01312179", equity_weights, source="seed")
        db_session.commit()

        mock_signals.return_value = {**_MOCK_SIGNALS, "price": 10.0}
        mock_fx.return_value = {"USD": 1.0}
        mock_etf_holdings.return_value = None
        mock_etf_weights.return_value = None

        # Act
        result = calculate_rebalance(db_session, "USD")

        # Assert: only equity sectors appear; total sector value < total fund MV.
        # MUTUAL_FUND falls back to cost_basis: qty=100 * cost_basis=100.0 = 10000
        sector_map = {s["sector"]: s for s in result["sector_exposure"]}
        total_mv = 100.0 * 100.0  # qty * cost_basis (no NAV seeded)

        assert "Industrials" in sector_map
        assert "Technology" in sector_map
        assert "Financial Services" in sector_map
        assert "Unknown" not in sector_map

        total_sector_value = sum(s["value"] for s in result["sector_exposure"])
        # Weights sum = 0.30, so total sector value should be ~30% of MV
        assert total_sector_value == pytest.approx(total_mv * 0.30, rel=0.01)
