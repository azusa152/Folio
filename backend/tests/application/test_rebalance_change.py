"""Tests for portfolio-level daily change calculation in rebalance_service."""

import json
from unittest.mock import patch

import pytest
from sqlmodel import Session

from application.portfolio.rebalance_service import calculate_rebalance
from domain.constants import DEFAULT_USER_ID
from domain.entities import Account, Holding, UserInvestmentProfile, UserPreferences
from domain.enums import StockCategory


def _seed_active_account(db_session: Session, name: str = "Test Account") -> Account:
    account = Account(
        user_id=DEFAULT_USER_ID,
        name=name,
        broker="Test Broker",
        account_type="brokerage",
        currency="USD",
        is_active=True,
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


class TestRebalancePortfolioChange:
    """Tests for portfolio-level daily change calculation."""

    @patch("application.portfolio.rebalance_service.get_technical_signals")
    @patch("application.portfolio.rebalance_service.get_exchange_rates")
    @patch("application.portfolio.rebalance_service.prewarm_signals_batch")
    @patch("application.portfolio.rebalance_service.prewarm_etf_holdings_batch")
    @patch("application.portfolio.rebalance_service.prewarm_etf_sector_weights_batch")
    @patch(
        "application.portfolio.rebalance_service.get_etf_top_holdings",
        return_value=None,
    )
    @patch(
        "application.portfolio.rebalance_service.get_etf_sector_weights",
        return_value=None,
    )
    def test_calculate_rebalance_should_include_total_change(
        self,
        _mock_etf_weights,
        _mock_etf,
        _mock_etf_sector_prewarm,
        _mock_etf_prewarm,
        mock_prewarm,
        mock_fx,
        mock_signals,
        db_session: Session,
    ):
        # Arrange
        profile = UserInvestmentProfile(
            user_id="default",
            config=json.dumps({"Growth": 100}),
            is_active=True,
        )
        db_session.add(profile)
        account = _seed_active_account(db_session, "Total Change Account")

        holding = Holding(
            user_id="default",
            ticker="NVDA",
            category=StockCategory.GROWTH,
            quantity=10.0,
            cost_basis=100.0,
            currency="USD",
            is_cash=False,
            account_id=account.id,
        )
        db_session.add(holding)
        db_session.commit()

        # Mock signals with current and previous price
        mock_signals.return_value = {
            "price": 120.0,
            "previous_close": 110.0,
            "change_pct": 9.09,
        }
        mock_fx.return_value = {"USD": 1.0}

        # Act
        result = calculate_rebalance(db_session, "USD")

        # Assert
        assert "total_value" in result
        assert "previous_total_value" in result
        assert "total_value_change" in result
        assert "total_value_change_pct" in result

        # Current: 10 * 120 = 1200
        # Previous: 10 * 110 = 1100
        # Change: 1200 - 1100 = 100
        # Change %: (100 / 1100) * 100 = 9.09%
        assert result["total_value"] == pytest.approx(1200.0, rel=0.01)
        assert result["previous_total_value"] == pytest.approx(1100.0, rel=0.01)
        assert result["total_value_change"] == pytest.approx(100.0, rel=0.01)
        assert result["total_value_change_pct"] == pytest.approx(9.09, rel=0.01)

    @patch("application.portfolio.rebalance_service.get_technical_signals")
    @patch("application.portfolio.rebalance_service.get_exchange_rates")
    @patch("application.portfolio.rebalance_service.prewarm_signals_batch")
    @patch("application.portfolio.rebalance_service.prewarm_etf_holdings_batch")
    @patch("application.portfolio.rebalance_service.prewarm_etf_sector_weights_batch")
    @patch(
        "application.portfolio.rebalance_service.get_etf_top_holdings",
        return_value=None,
    )
    @patch(
        "application.portfolio.rebalance_service.get_etf_sector_weights",
        return_value=None,
    )
    def test_calculate_rebalance_should_include_holding_change_pct(
        self,
        _mock_etf_weights,
        _mock_etf,
        _mock_etf_sector_prewarm,
        _mock_etf_prewarm,
        mock_prewarm,
        mock_fx,
        mock_signals,
        db_session: Session,
    ):
        # Arrange
        profile = UserInvestmentProfile(
            user_id="default",
            config=json.dumps({"Growth": 100}),
            is_active=True,
        )
        db_session.add(profile)
        account = _seed_active_account(db_session, "Holding Change Account")

        holding = Holding(
            user_id="default",
            ticker="AAPL",
            category=StockCategory.GROWTH,
            quantity=5.0,
            cost_basis=150.0,
            currency="USD",
            is_cash=False,
            account_id=account.id,
        )
        db_session.add(holding)
        db_session.commit()

        # Mock signals
        mock_signals.return_value = {
            "price": 180.0,
            "previous_close": 175.0,
            "change_pct": 2.86,
        }
        mock_fx.return_value = {"USD": 1.0}

        # Act
        result = calculate_rebalance(db_session, "USD")

        # Assert
        assert "holdings_detail" in result
        assert len(result["holdings_detail"]) == 1

        holding_detail = result["holdings_detail"][0]
        assert "change_pct" in holding_detail
        assert "change_value" in holding_detail
        assert "total_gain_value" in holding_detail
        assert "total_gain_pct" in holding_detail

        # Current MV: 5 * 180 = 900
        # Previous MV: 5 * 175 = 875
        # Change: 900 - 875 = 25
        # Change %: (900 - 875) / 875 * 100 = 2.86%
        # Total gain: 900 - (5 * 150) = 150
        # Total gain %: 150 / 750 * 100 = 20%
        assert holding_detail["change_value"] == pytest.approx(25.0, rel=0.01)
        assert holding_detail["change_pct"] == pytest.approx(2.86, rel=0.01)
        assert holding_detail["total_gain_value"] == pytest.approx(150.0, rel=0.01)
        assert holding_detail["total_gain_pct"] == pytest.approx(20.0, rel=0.01)

    @patch("application.portfolio.rebalance_service.get_technical_signals")
    @patch("application.portfolio.rebalance_service.get_exchange_rates")
    @patch("application.portfolio.rebalance_service.prewarm_signals_batch")
    @patch("application.portfolio.rebalance_service.prewarm_etf_holdings_batch")
    @patch("application.portfolio.rebalance_service.prewarm_etf_sector_weights_batch")
    @patch(
        "application.portfolio.rebalance_service.get_etf_top_holdings",
        return_value=None,
    )
    @patch(
        "application.portfolio.rebalance_service.get_etf_sector_weights",
        return_value=None,
    )
    def test_calculate_rebalance_should_handle_missing_previous_close(
        self,
        _mock_etf_weights,
        _mock_etf,
        _mock_etf_sector_prewarm,
        _mock_etf_prewarm,
        mock_prewarm,
        mock_fx,
        mock_signals,
        db_session: Session,
    ):
        # Arrange: New stock with no previous_close
        profile = UserInvestmentProfile(
            user_id="default",
            config=json.dumps({"Growth": 100}),
            is_active=True,
        )
        db_session.add(profile)
        account = _seed_active_account(db_session, "Missing Previous Close Account")

        holding = Holding(
            user_id="default",
            ticker="NEW",
            category=StockCategory.GROWTH,
            quantity=10.0,
            cost_basis=50.0,
            currency="USD",
            is_cash=False,
            account_id=account.id,
        )
        db_session.add(holding)
        db_session.commit()

        # Mock signals with no previous_close (newly added stock)
        mock_signals.return_value = {
            "price": 55.0,
            "previous_close": None,
            "change_pct": None,
        }
        mock_fx.return_value = {"USD": 1.0}

        # Act
        result = calculate_rebalance(db_session, "USD")

        # Assert — no previous_close: holding change_pct is None (N/A in UI)
        # Portfolio-level totals still balance (prev_mv falls back to mv)
        holding_detail = result["holdings_detail"][0]
        assert result["total_value"] == pytest.approx(550.0, rel=0.01)
        assert result["previous_total_value"] == pytest.approx(550.0, rel=0.01)
        assert holding_detail["change_pct"] is None
        assert holding_detail["change_value"] is None
        assert holding_detail["total_gain_value"] == pytest.approx(50.0, rel=0.01)
        assert holding_detail["total_gain_pct"] == pytest.approx(10.0, rel=0.01)

    @patch("application.portfolio.rebalance_service.get_exchange_rates")
    def test_calculate_rebalance_should_handle_zero_previous_total_value(
        self, mock_fx, db_session: Session
    ):
        # Arrange: Portfolio with cash only (no price change)
        profile = UserInvestmentProfile(
            user_id="default",
            config=json.dumps({"Cash": 100}),
            is_active=True,
        )
        db_session.add(profile)
        account = _seed_active_account(db_session, "Cash Only Account")

        holding = Holding(
            user_id="default",
            ticker="USD",
            category=StockCategory.CASH,
            quantity=1000.0,
            currency="USD",
            is_cash=True,
            account_id=account.id,
        )
        db_session.add(holding)
        db_session.commit()

        mock_fx.return_value = {"USD": 1.0}

        # Act
        result = calculate_rebalance(db_session, "USD")

        # Assert
        # Cash has no change (same current and previous)
        assert result["total_value"] == pytest.approx(1000.0, rel=0.01)
        assert result["previous_total_value"] == pytest.approx(1000.0, rel=0.01)
        assert result["total_value_change"] == pytest.approx(0.0, rel=0.01)
        assert result["total_value_change_pct"] == pytest.approx(0.0, rel=0.01)

    @patch("application.portfolio.rebalance_service.get_technical_signals")
    @patch("application.portfolio.rebalance_service.get_exchange_rates")
    @patch("application.portfolio.rebalance_service.prewarm_signals_batch")
    @patch("application.portfolio.rebalance_service.prewarm_etf_holdings_batch")
    @patch("application.portfolio.rebalance_service.prewarm_etf_sector_weights_batch")
    @patch(
        "application.portfolio.rebalance_service.get_etf_top_holdings",
        return_value=None,
    )
    @patch(
        "application.portfolio.rebalance_service.get_etf_sector_weights",
        return_value=None,
    )
    def test_calculate_rebalance_should_aggregate_multiple_holdings_change(
        self,
        _mock_etf_weights,
        _mock_etf,
        _mock_etf_sector_prewarm,
        _mock_etf_prewarm,
        mock_prewarm,
        mock_fx,
        mock_signals,
        db_session: Session,
    ):
        # Arrange: Multiple holdings with different changes
        profile = UserInvestmentProfile(
            user_id="default",
            config=json.dumps({"Growth": 100}),
            is_active=True,
        )
        db_session.add(profile)
        account = _seed_active_account(db_session, "Aggregate Change Account")

        holding1 = Holding(
            user_id="default",
            ticker="NVDA",
            category=StockCategory.GROWTH,
            quantity=10.0,
            cost_basis=100.0,
            currency="USD",
            is_cash=False,
            account_id=account.id,
        )
        db_session.add(holding1)

        holding2 = Holding(
            user_id="default",
            ticker="AAPL",
            category=StockCategory.GROWTH,
            quantity=5.0,
            cost_basis=150.0,
            currency="USD",
            is_cash=False,
            account_id=account.id,
        )
        db_session.add(holding2)
        db_session.commit()

        # Mock signals for both holdings
        def mock_signals_side_effect(ticker):
            if ticker == "NVDA":
                return {
                    "price": 120.0,
                    "previous_close": 110.0,
                    "change_pct": 9.09,
                }
            if ticker == "AAPL":
                return {
                    "price": 170.0,
                    "previous_close": 180.0,
                    "change_pct": -5.56,
                }
            return None

        mock_signals.side_effect = mock_signals_side_effect
        mock_fx.return_value = {"USD": 1.0}

        # Act
        result = calculate_rebalance(db_session, "USD")

        # Assert
        # NVDA: current = 10 * 120 = 1200, previous = 10 * 110 = 1100
        # AAPL: current = 5 * 170 = 850, previous = 5 * 180 = 900
        # Total: current = 2050, previous = 2000
        # Change: (2050 - 2000) / 2000 * 100 = 2.5%
        assert result["total_value"] == pytest.approx(2050.0, rel=0.01)
        assert result["previous_total_value"] == pytest.approx(2000.0, rel=0.01)
        assert result["total_value_change"] == pytest.approx(50.0, rel=0.01)
        assert result["total_value_change_pct"] == pytest.approx(2.5, rel=0.01)

        # Check individual holdings
        holdings = result["holdings_detail"]
        nvda_holding = next(h for h in holdings if h["ticker"] == "NVDA")
        aapl_holding = next(h for h in holdings if h["ticker"] == "AAPL")

        assert nvda_holding["change_pct"] == pytest.approx(9.09, rel=0.01)
        assert aapl_holding["change_pct"] == pytest.approx(-5.56, rel=0.01)
        assert nvda_holding["change_value"] == pytest.approx(100.0, rel=0.01)
        assert aapl_holding["change_value"] == pytest.approx(-50.0, rel=0.01)
        assert nvda_holding["total_gain_value"] == pytest.approx(200.0, rel=0.01)
        assert aapl_holding["total_gain_value"] == pytest.approx(100.0, rel=0.01)
        assert nvda_holding["total_gain_pct"] == pytest.approx(20.0, rel=0.01)
        assert aapl_holding["total_gain_pct"] == pytest.approx(13.33, rel=0.01)

    @patch("application.portfolio.rebalance_service.get_technical_signals")
    @patch("application.portfolio.rebalance_service.get_exchange_rates")
    @patch("application.portfolio.rebalance_service.prewarm_signals_batch")
    @patch("application.portfolio.rebalance_service.are_all_signals_in_l1")
    @patch("application.portfolio.rebalance_service.prewarm_etf_holdings_batch")
    @patch("application.portfolio.rebalance_service.prewarm_etf_sector_weights_batch")
    @patch(
        "application.portfolio.rebalance_service.get_etf_top_holdings",
        return_value=None,
    )
    @patch(
        "application.portfolio.rebalance_service.get_etf_sector_weights",
        return_value=None,
    )
    def test_calculate_rebalance_should_skip_prewarm_when_signals_already_warm(
        self,
        _mock_etf_weights,
        _mock_etf,
        _mock_etf_sector_prewarm,
        _mock_etf_prewarm,
        mock_l1_all_warm,
        mock_prewarm,
        mock_fx,
        mock_signals,
        db_session: Session,
    ):
        profile = UserInvestmentProfile(
            user_id="default",
            config=json.dumps({"Growth": 100}),
            is_active=True,
        )
        db_session.add(profile)
        account = _seed_active_account(db_session, "Warm Signals Account")
        db_session.add(
            Holding(
                user_id="default",
                ticker="NVDA",
                category=StockCategory.GROWTH,
                quantity=10.0,
                cost_basis=100.0,
                currency="USD",
                is_cash=False,
                account_id=account.id,
            )
        )
        db_session.commit()

        mock_l1_all_warm.return_value = True
        mock_fx.return_value = {"USD": 1.0}
        mock_signals.return_value = {
            "price": 110.0,
            "previous_close": 108.0,
            "change_pct": 1.85,
        }

        calculate_rebalance(db_session, "USD")

        mock_l1_all_warm.assert_called_once_with(["NVDA"])
        mock_prewarm.assert_not_called()

    @patch("application.portfolio.rebalance_service.get_technical_signals")
    @patch("application.portfolio.rebalance_service.get_exchange_rates")
    @patch("application.portfolio.rebalance_service.prewarm_signals_batch")
    @patch("application.portfolio.rebalance_service.prewarm_etf_holdings_batch")
    @patch("application.portfolio.rebalance_service.prewarm_etf_sector_weights_batch")
    @patch(
        "application.portfolio.rebalance_service.get_etf_top_holdings",
        return_value=None,
    )
    @patch(
        "application.portfolio.rebalance_service.get_etf_sector_weights",
        return_value=None,
    )
    def test_calculate_rebalance_should_fallback_to_zero_when_price_and_cost_are_missing(
        self,
        _mock_etf_weights,
        _mock_etf,
        _mock_etf_sector_prewarm,
        _mock_etf_prewarm,
        _mock_prewarm,
        mock_fx,
        mock_signals,
        db_session: Session,
    ):
        profile = UserInvestmentProfile(
            user_id="default",
            config=json.dumps({"Growth": 100}),
            is_active=True,
        )
        db_session.add(profile)
        account = _seed_active_account(db_session, "Missing Price Account")
        db_session.add(
            Holding(
                user_id="default",
                ticker="NO_PRICE",
                category=StockCategory.GROWTH,
                quantity=5.0,
                cost_basis=None,
                currency="USD",
                is_cash=False,
                account_id=account.id,
            )
        )
        db_session.commit()

        mock_fx.return_value = {"USD": 1.0}
        mock_signals.return_value = {"price": None, "previous_close": None}

        result = calculate_rebalance(db_session, "USD")

        assert result["total_value"] == pytest.approx(0.0, rel=0.01)
        assert result["previous_total_value"] == pytest.approx(0.0, rel=0.01)
        assert result["total_value_change"] == pytest.approx(0.0, rel=0.01)
        assert result["total_value_change_pct"] is None

    @patch("application.portfolio.rebalance_service.get_technical_signals")
    @patch("application.portfolio.rebalance_service.get_exchange_rates")
    @patch("application.portfolio.rebalance_service.prewarm_signals_batch")
    @patch("application.portfolio.rebalance_service.prewarm_etf_holdings_batch")
    @patch("application.portfolio.rebalance_service.prewarm_etf_sector_weights_batch")
    @patch(
        "application.portfolio.rebalance_service.get_etf_top_holdings",
        return_value=None,
    )
    @patch(
        "application.portfolio.rebalance_service.get_etf_sector_weights",
        return_value=None,
    )
    def test_calculate_rebalance_should_exclude_inactive_and_unlinked_holdings(
        self,
        _mock_etf_weights,
        _mock_etf,
        _mock_etf_sector_prewarm,
        _mock_etf_prewarm,
        _mock_prewarm,
        mock_fx,
        mock_signals,
        db_session: Session,
    ):
        profile = UserInvestmentProfile(
            user_id="default",
            config=json.dumps({"Growth": 100}),
            is_active=True,
        )
        db_session.add(profile)

        active_account = Account(
            user_id=DEFAULT_USER_ID,
            name="Active Account",
            broker="Active Broker",
            account_type="brokerage",
            currency="USD",
            is_active=True,
        )
        inactive_account = Account(
            user_id=DEFAULT_USER_ID,
            name="Inactive Account",
            broker="Inactive Broker",
            account_type="brokerage",
            currency="USD",
            is_active=False,
        )
        db_session.add(active_account)
        db_session.add(inactive_account)
        db_session.commit()
        db_session.refresh(active_account)
        db_session.refresh(inactive_account)

        db_session.add(
            Holding(
                user_id="default",
                ticker="AAPL",
                category=StockCategory.GROWTH,
                quantity=2.0,
                cost_basis=100.0,
                currency="USD",
                is_cash=False,
                account_id=active_account.id,
            )
        )
        db_session.add(
            Holding(
                user_id="default",
                ticker="MSFT",
                category=StockCategory.GROWTH,
                quantity=5.0,
                cost_basis=100.0,
                currency="USD",
                is_cash=False,
                account_id=inactive_account.id,
            )
        )
        db_session.add(
            Holding(
                user_id="default",
                ticker="ORPHAN",
                category=StockCategory.GROWTH,
                quantity=10.0,
                cost_basis=100.0,
                currency="USD",
                is_cash=False,
                account_id=None,
            )
        )
        db_session.commit()

        mock_signals.return_value = {
            "price": 100.0,
            "previous_close": 100.0,
            "change_pct": 0.0,
        }
        mock_fx.return_value = {"USD": 1.0}

        result = calculate_rebalance(db_session, "USD")

        assert result["total_value"] == pytest.approx(200.0, rel=0.01)
        assert len(result["holdings_detail"]) == 1
        assert result["holdings_detail"][0]["ticker"] == "AAPL"


class TestRebalanceAdviceTranslation:
    """Application-layer step 5.5: advice must be list[str], not list[dict]."""

    @patch("application.portfolio.rebalance_service.get_technical_signals")
    @patch("application.portfolio.rebalance_service.get_exchange_rates")
    @patch("application.portfolio.rebalance_service.prewarm_signals_batch")
    @patch("application.portfolio.rebalance_service.prewarm_etf_holdings_batch")
    @patch("application.portfolio.rebalance_service.prewarm_etf_sector_weights_batch")
    @patch(
        "application.portfolio.rebalance_service.get_etf_top_holdings",
        return_value=None,
    )
    @patch(
        "application.portfolio.rebalance_service.get_etf_sector_weights",
        return_value=None,
    )
    def test_advice_is_list_of_strings_when_balanced(
        self,
        _mock_etf_weights,
        _mock_etf,
        _mock_etf_sector_prewarm,
        _mock_etf_prewarm,
        mock_prewarm,
        mock_fx,
        mock_signals,
        db_session: Session,
    ):
        # Arrange — perfectly balanced portfolio: Growth 50% / Bond 50%
        db_session.add(UserPreferences(user_id="default", language="en"))
        profile = UserInvestmentProfile(
            user_id="default",
            config=json.dumps({"Growth": 50, "Bond": 50}),
            is_active=True,
        )
        db_session.add(profile)
        account = _seed_active_account(db_session, "Balanced Advice Account")
        for ticker, category in [
            ("NVDA", StockCategory.GROWTH),
            ("BND", StockCategory.BOND),
        ]:
            db_session.add(
                Holding(
                    user_id="default",
                    ticker=ticker,
                    category=category,
                    quantity=10.0,
                    cost_basis=100.0,
                    currency="USD",
                    is_cash=False,
                    account_id=account.id,
                )
            )
        db_session.commit()

        mock_signals.return_value = {
            "price": 100.0,
            "previous_close": 100.0,
            "change_pct": 0.0,
        }
        mock_fx.return_value = {"USD": 1.0}

        # Act
        result = calculate_rebalance(db_session, "USD")

        # Assert — translated strings, not raw dicts
        advice = result["advice"]
        assert isinstance(advice, list)
        assert len(advice) >= 1
        assert all(isinstance(a, str) for a in advice), (
            f"Expected list[str], got: {advice}"
        )
        assert any("No rebalancing needed" in a for a in advice)

    @patch("application.portfolio.rebalance_service.get_technical_signals")
    @patch("application.portfolio.rebalance_service.get_exchange_rates")
    @patch("application.portfolio.rebalance_service.prewarm_signals_batch")
    @patch("application.portfolio.rebalance_service.prewarm_etf_holdings_batch")
    @patch("application.portfolio.rebalance_service.prewarm_etf_sector_weights_batch")
    @patch(
        "application.portfolio.rebalance_service.get_etf_top_holdings",
        return_value=None,
    )
    @patch(
        "application.portfolio.rebalance_service.get_etf_sector_weights",
        return_value=None,
    )
    def test_advice_is_list_of_strings_when_overweight(
        self,
        _mock_etf_weights,
        _mock_etf,
        _mock_etf_sector_prewarm,
        _mock_etf_prewarm,
        mock_prewarm,
        mock_fx,
        mock_signals,
        db_session: Session,
    ):
        # Arrange — Growth 80% vs target 50%: clear overweight drift
        db_session.add(UserPreferences(user_id="default", language="en"))
        profile = UserInvestmentProfile(
            user_id="default",
            config=json.dumps({"Growth": 50, "Bond": 50}),
            is_active=True,
        )
        db_session.add(profile)
        account = _seed_active_account(db_session, "Overweight Advice Account")
        db_session.add(
            Holding(
                user_id="default",
                ticker="NVDA",
                category=StockCategory.GROWTH,
                quantity=80.0,
                cost_basis=1.0,
                currency="USD",
                is_cash=False,
                account_id=account.id,
            )
        )
        db_session.add(
            Holding(
                user_id="default",
                ticker="BND",
                category=StockCategory.BOND,
                quantity=20.0,
                cost_basis=1.0,
                currency="USD",
                is_cash=False,
                account_id=account.id,
            )
        )
        db_session.commit()

        mock_signals.return_value = {
            "price": 1.0,
            "previous_close": 1.0,
            "change_pct": 0.0,
        }
        mock_fx.return_value = {"USD": 1.0}

        # Act
        result = calculate_rebalance(db_session, "USD")

        # Assert — translated strings, not raw dicts
        advice = result["advice"]
        assert isinstance(advice, list)
        assert len(advice) >= 1
        assert all(isinstance(a, str) for a in advice), (
            f"Expected list[str], got: {advice}"
        )
        assert any("overweight" in a.lower() for a in advice)


class TestRebalanceCacheRefresh:
    @patch("application.portfolio.rebalance_service.get_technical_signals")
    @patch("application.portfolio.rebalance_service.get_exchange_rates")
    @patch("application.portfolio.rebalance_service.prewarm_signals_batch")
    @patch("application.portfolio.rebalance_service.prewarm_etf_holdings_batch")
    @patch("application.portfolio.rebalance_service.prewarm_etf_sector_weights_batch")
    @patch(
        "application.portfolio.rebalance_service.get_etf_top_holdings",
        return_value=None,
    )
    @patch(
        "application.portfolio.rebalance_service.get_etf_sector_weights",
        return_value=None,
    )
    def test_force_refresh_should_recompute_cached_rebalance(
        self,
        _mock_etf_weights,
        _mock_etf,
        _mock_etf_sector_prewarm,
        _mock_etf_prewarm,
        _mock_prewarm,
        mock_fx,
        mock_signals,
        db_session: Session,
    ):
        profile = UserInvestmentProfile(
            user_id="default",
            config=json.dumps({"Growth": 100}),
            is_active=True,
        )
        db_session.add(profile)
        account = _seed_active_account(db_session, "Cache Refresh Account")
        db_session.add(
            Holding(
                user_id="default",
                ticker="NVDA",
                category=StockCategory.GROWTH,
                quantity=10.0,
                cost_basis=100.0,
                currency="USD",
                is_cash=False,
                account_id=account.id,
            )
        )
        db_session.commit()

        mock_fx.return_value = {"USD": 1.0}
        mock_signals.side_effect = [
            {"price": 120.0, "previous_close": 110.0, "change_pct": 9.09},
            {"price": 130.0, "previous_close": 120.0, "change_pct": 8.33},
        ]

        first = calculate_rebalance(db_session, "USD")
        refreshed = calculate_rebalance(db_session, "USD", force_refresh=True)

        assert first["total_value"] == pytest.approx(1200.0, rel=0.01)
        assert refreshed["total_value"] == pytest.approx(1300.0, rel=0.01)
