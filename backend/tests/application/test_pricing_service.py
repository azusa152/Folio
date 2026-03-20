"""
Unit tests for pricing_service.resolve_holding_price_with_prev.

Each test covers one category branch:
  cash, crypto (with/without prev), mutual_fund (with/without nav_previous),
  skip category, equity (with/without previous_close).

No DB or network I/O — all infrastructure calls are mocked.
"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

PRICING_MODULE = "application.portfolio.pricing_service"


def _holding(category, is_cash=False, ticker="TEST", coingecko_id=None):
    """Build a minimal SimpleNamespace that satisfies the _HoldingLike protocol."""
    return SimpleNamespace(
        category=category,
        is_cash=is_cash,
        ticker=ticker,
        coingecko_id=coingecko_id,
        cost_basis=100.0,
        quantity=10.0,
    )


class TestResolveHoldingPriceWithPrev:
    def test_cash_returns_price_one_and_has_prev_true(self) -> None:
        from application.portfolio.pricing_service import (
            resolve_holding_price_with_prev,
        )
        from domain.core.enums import StockCategory

        holding = _holding(StockCategory.CASH, is_cash=True, ticker="CASH_JPY")
        price, prev, has_prev = resolve_holding_price_with_prev(holding, nav_cache={})

        assert price == 1.0
        assert prev is None
        assert has_prev is True

    def test_crypto_returns_price_and_computed_prev(self) -> None:
        from application.portfolio.pricing_service import (
            resolve_holding_price_with_prev,
        )
        from domain.core.enums import StockCategory

        holding = _holding(StockCategory.CRYPTO, ticker="BTC", coingecko_id="bitcoin")
        mock_data = {"price_usd": 100.0, "change_24h_pct": 25.0}
        with patch(f"{PRICING_MODULE}.get_crypto_price", return_value=mock_data):
            price, prev, has_prev = resolve_holding_price_with_prev(
                holding, nav_cache={}
            )

        assert price == 100.0
        # prev = 100 / (1 + 0.25) = 80.0
        assert prev == pytest.approx(80.0)
        assert has_prev is True

    def test_crypto_has_prev_false_when_change_24h_missing(self) -> None:
        from application.portfolio.pricing_service import (
            resolve_holding_price_with_prev,
        )
        from domain.core.enums import StockCategory

        holding = _holding(StockCategory.CRYPTO, ticker="BTC", coingecko_id="bitcoin")
        mock_data = {"price_usd": 50.0}  # no change_24h_pct
        with patch(f"{PRICING_MODULE}.get_crypto_price", return_value=mock_data):
            price, prev, has_prev = resolve_holding_price_with_prev(
                holding, nav_cache={}
            )

        assert price == 50.0
        assert prev is None
        assert has_prev is False

    def test_mutual_fund_returns_nav_and_nav_previous(self) -> None:
        from application.portfolio.pricing_service import (
            resolve_holding_price_with_prev,
        )
        from domain.core.enums import StockCategory

        holding = _holding(StockCategory.MUTUAL_FUND, ticker="0131310B")
        nav_cache = {"0131310B": {"nav": 12345.0, "nav_previous": 12200.0}}
        price, prev, has_prev = resolve_holding_price_with_prev(
            holding, nav_cache=nav_cache
        )

        assert price == 12345.0
        assert prev == 12200.0
        assert has_prev is True

    def test_mutual_fund_has_prev_false_when_nav_previous_absent(self) -> None:
        from application.portfolio.pricing_service import (
            resolve_holding_price_with_prev,
        )
        from domain.core.enums import StockCategory

        holding = _holding(StockCategory.MUTUAL_FUND, ticker="0131310B")
        nav_cache = {"0131310B": {"nav": 12345.0}}  # no nav_previous key
        price, prev, has_prev = resolve_holding_price_with_prev(
            holding, nav_cache=nav_cache
        )

        assert price == 12345.0
        assert prev is None
        assert has_prev is False

    def test_skip_category_returns_none_price_and_has_prev_true(self) -> None:
        from application.portfolio.pricing_service import (
            resolve_holding_price_with_prev,
        )
        from domain.core.enums import StockCategory

        # SKIP_PRICE_FETCH_CATEGORIES = ["Cash", "Mutual_Fund"].
        # Use Cash with is_cash=False to reach `cat in SKIP` branch
        # (is_cash=True is covered by test_cash_* above).
        holding = _holding(StockCategory.CASH, is_cash=False, ticker="CASH_USD")
        price, prev, has_prev = resolve_holding_price_with_prev(holding, nav_cache={})

        assert price is None
        assert prev is None
        assert has_prev is True  # cost_basis fallback is reliable

    def test_equity_returns_price_and_previous_close(self) -> None:
        from application.portfolio.pricing_service import (
            resolve_holding_price_with_prev,
        )
        from domain.core.enums import StockCategory

        holding = _holding(StockCategory.GROWTH, ticker="AAPL")
        mock_signals = {"price": 180.0, "previous_close": 175.0}
        with patch(
            f"{PRICING_MODULE}.get_technical_signals", return_value=mock_signals
        ):
            price, prev, has_prev = resolve_holding_price_with_prev(
                holding, nav_cache={}
            )

        assert price == 180.0
        assert prev == 175.0
        assert has_prev is True

    def test_equity_has_prev_false_when_previous_close_absent(self) -> None:
        from application.portfolio.pricing_service import (
            resolve_holding_price_with_prev,
        )
        from domain.core.enums import StockCategory

        holding = _holding(StockCategory.GROWTH, ticker="AAPL")
        mock_signals = {"price": 180.0}  # no previous_close
        with patch(
            f"{PRICING_MODULE}.get_technical_signals", return_value=mock_signals
        ):
            price, prev, has_prev = resolve_holding_price_with_prev(
                holding, nav_cache={}
            )

        assert price == 180.0
        assert prev is None
        assert has_prev is False

    def test_equity_returns_none_price_when_signals_unavailable(self) -> None:
        from application.portfolio.pricing_service import (
            resolve_holding_price_with_prev,
        )
        from domain.core.enums import StockCategory

        holding = _holding(StockCategory.GROWTH, ticker="AAPL")
        with patch(f"{PRICING_MODULE}.get_technical_signals", return_value=None):
            price, prev, has_prev = resolve_holding_price_with_prev(
                holding, nav_cache={}
            )

        assert price is None
        assert prev is None
        assert has_prev is False
