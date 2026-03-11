"""Service-level tests for application.portfolio.insight_service."""

import json
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import Session

from application.portfolio.insight_service import (
    get_portfolio_insights,
    invalidate_insight_cache,
)
from domain.entities import PortfolioSnapshot


def _make_snapshot(
    day: int,
    total_value: float,
    benchmark_gspc: float | None = None,
) -> PortfolioSnapshot:
    bm = json.dumps({"^GSPC": benchmark_gspc}) if benchmark_gspc else "{}"
    return PortfolioSnapshot(
        id=day,
        snapshot_date=date(2025, 1, day),
        total_value=total_value,
        benchmark_values=bm,
    )


_MOCK_REBALANCE = {
    "categories": {
        "Tech": {"market_value": 70000, "drift_pct": 8.0},
        "Bonds": {"market_value": 30000, "drift_pct": -2.0},
    },
    "health_score": 85,
}

_MOCK_RISK = {
    "annualized_return": 0.12,
    "annualized_volatility": 0.15,
    "sharpe_ratio": 1.2,
    "sortino_ratio": 1.5,
    "max_drawdown_pct": -0.18,
    "calmar_ratio": 0.67,
    "trading_days": 252,
}


class TestGetPortfolioInsights:
    """Tests for the insight orchestration service."""

    @patch("application.portfolio.insight_service.get_risk_metrics")
    @patch("application.portfolio.insight_service.get_snapshots")
    @patch("application.portfolio.insight_service.calculate_rebalance")
    def test_should_produce_allocation_and_performance_insights(
        self,
        mock_rebalance,
        mock_snapshots,
        mock_risk,
    ):
        invalidate_insight_cache()
        mock_rebalance.return_value = _MOCK_REBALANCE
        mock_snapshots.return_value = [
            _make_snapshot(1, 10000, 4500),
            _make_snapshot(30, 11500, 5000),
        ]
        mock_risk.return_value = _MOCK_RISK

        result = get_portfolio_insights(MagicMock(spec=Session), "USD")

        keys = [i["key"] for i in result]
        assert "insight.high_concentration" in keys
        assert "insight.drift_exceeds_threshold" in keys
        assert "insight.health_excellent" in keys

    @patch("application.portfolio.insight_service.get_risk_metrics")
    @patch("application.portfolio.insight_service.get_snapshots")
    @patch("application.portfolio.insight_service.calculate_rebalance")
    def test_should_convert_twr_from_percent_to_decimal(
        self,
        mock_rebalance,
        mock_snapshots,
        mock_risk,
    ):
        """compute_twr returns percent (e.g. 15.0); service must divide by 100."""
        invalidate_insight_cache()
        mock_rebalance.return_value = {"categories": {}, "health_score": 70}
        # benchmark return = (5000 - 4500) / 4500 ≈ 11.1%, TWR = 15% → alpha ≈ 3.9%
        mock_snapshots.return_value = [
            _make_snapshot(1, 10000, 4500),
            _make_snapshot(30, 11500, 5000),
        ]
        mock_risk.return_value = {**_MOCK_RISK, "max_drawdown_pct": -0.05}

        with patch(
            "application.portfolio.insight_service.compute_twr",
            return_value=15.0,
        ):
            result = get_portfolio_insights(MagicMock(spec=Session), "USD")

        outperf = [i for i in result if i["key"] == "insight.outperforming_benchmark"]
        assert len(outperf) == 1
        assert outperf[0]["vars"]["return_pct"] == 15.0

    @patch("application.portfolio.insight_service.get_risk_metrics")
    @patch("application.portfolio.insight_service.get_snapshots")
    @patch("application.portfolio.insight_service.calculate_rebalance")
    def test_should_compute_benchmark_return_from_snapshots(
        self,
        mock_rebalance,
        mock_snapshots,
        mock_risk,
    ):
        invalidate_insight_cache()
        mock_rebalance.return_value = {"categories": {}, "health_score": 70}
        mock_snapshots.return_value = [
            _make_snapshot(1, 10000, 4000),
            _make_snapshot(30, 10100, 4800),
        ]
        mock_risk.return_value = {
            **_MOCK_RISK,
            "max_drawdown_pct": -0.05,
            "sharpe_ratio": 0.5,
        }

        with patch(
            "application.portfolio.insight_service.compute_twr",
            return_value=1.0,
        ):
            result = get_portfolio_insights(MagicMock(spec=Session), "USD")

        underperf = [
            i for i in result if i["key"] == "insight.underperforming_benchmark"
        ]
        assert len(underperf) == 1
        assert underperf[0]["vars"]["lag_pct"] == pytest.approx(19.0, abs=0.1)

    @patch("application.portfolio.insight_service.get_risk_metrics")
    @patch("application.portfolio.insight_service.get_snapshots")
    @patch("application.portfolio.insight_service.calculate_rebalance")
    def test_should_gracefully_handle_rebalance_error(
        self,
        mock_rebalance,
        mock_snapshots,
        mock_risk,
    ):
        invalidate_insight_cache()
        mock_rebalance.side_effect = RuntimeError("No persona configured")
        mock_snapshots.return_value = []
        mock_risk.return_value = {
            **_MOCK_RISK,
            "max_drawdown_pct": 0,
            "sharpe_ratio": 0.5,
        }

        result = get_portfolio_insights(MagicMock(spec=Session), "USD")

        assert isinstance(result, list)
        alloc_keys = [i for i in result if i["category"] == "allocation"]
        assert len(alloc_keys) == 0

    @patch("application.portfolio.insight_service.get_risk_metrics")
    @patch("application.portfolio.insight_service.get_snapshots")
    @patch("application.portfolio.insight_service.calculate_rebalance")
    def test_cache_should_key_by_display_currency(
        self,
        mock_rebalance,
        mock_snapshots,
        mock_risk,
    ):
        invalidate_insight_cache()
        mock_rebalance.return_value = {"categories": {}, "health_score": 90}
        mock_snapshots.return_value = []
        mock_risk.return_value = {
            **_MOCK_RISK,
            "max_drawdown_pct": 0,
            "sharpe_ratio": 0.5,
        }

        session = MagicMock(spec=Session)
        get_portfolio_insights(session, "USD")
        get_portfolio_insights(session, "JPY")

        assert mock_rebalance.call_count == 2
        assert mock_rebalance.call_args_list[0][0][1] == "USD"
        assert mock_rebalance.call_args_list[1][0][1] == "JPY"

    @patch("application.portfolio.insight_service.get_risk_metrics")
    @patch("application.portfolio.insight_service.get_snapshots")
    @patch("application.portfolio.insight_service.calculate_rebalance")
    def test_cache_should_return_cached_result_within_ttl(
        self,
        mock_rebalance,
        mock_snapshots,
        mock_risk,
    ):
        invalidate_insight_cache()
        mock_rebalance.return_value = {"categories": {}, "health_score": 90}
        mock_snapshots.return_value = []
        mock_risk.return_value = {
            **_MOCK_RISK,
            "max_drawdown_pct": 0,
            "sharpe_ratio": 0.5,
        }

        session = MagicMock(spec=Session)
        get_portfolio_insights(session, "USD")
        get_portfolio_insights(session, "USD")

        assert mock_rebalance.call_count == 1

    @patch("application.portfolio.insight_service.get_risk_metrics")
    @patch("application.portfolio.insight_service.get_snapshots")
    @patch("application.portfolio.insight_service.calculate_rebalance")
    def test_should_handle_malformed_benchmark_json(
        self,
        mock_rebalance,
        mock_snapshots,
        mock_risk,
    ):
        """Malformed benchmark_values must not crash the insights endpoint."""
        invalidate_insight_cache()
        mock_rebalance.return_value = {"categories": {}, "health_score": 70}
        bad_snap = PortfolioSnapshot(
            id=1,
            snapshot_date=date(2025, 1, 1),
            total_value=10000,
            benchmark_values="NOT VALID JSON",
        )
        good_snap = _make_snapshot(30, 11500, 5000)
        mock_snapshots.return_value = [bad_snap, good_snap]
        mock_risk.return_value = {
            **_MOCK_RISK,
            "max_drawdown_pct": 0,
            "sharpe_ratio": 0.5,
        }

        result = get_portfolio_insights(MagicMock(spec=Session), "USD")

        assert isinstance(result, list)
        bench = [i for i in result if "benchmark" in i["key"]]
        assert len(bench) == 0


class TestInvalidateInsightCache:
    """Tests for cache invalidation."""

    @patch("application.portfolio.insight_service.get_risk_metrics")
    @patch("application.portfolio.insight_service.get_snapshots")
    @patch("application.portfolio.insight_service.calculate_rebalance")
    def test_invalidate_should_force_recomputation(
        self,
        mock_rebalance,
        mock_snapshots,
        mock_risk,
    ):
        invalidate_insight_cache()
        mock_rebalance.return_value = {"categories": {}, "health_score": 90}
        mock_snapshots.return_value = []
        mock_risk.return_value = {
            **_MOCK_RISK,
            "max_drawdown_pct": 0,
            "sharpe_ratio": 0.5,
        }

        session = MagicMock(spec=Session)
        get_portfolio_insights(session, "USD")
        invalidate_insight_cache()
        get_portfolio_insights(session, "USD")

        assert mock_rebalance.call_count == 2
