"""Tests for risk metrics functions in domain/analysis/risk_metrics.py."""

from datetime import date

from domain.analysis.risk_metrics import (
    MIN_DAYS_FOR_RATIOS,
    RiskMetrics,
    compute_daily_returns,
    compute_risk_metrics,
)


def _snap(day: int, value: float) -> dict:
    return {"snapshot_date": date(2025, 1, day), "total_value": value}


# ---------------------------------------------------------------------------
# compute_daily_returns
# ---------------------------------------------------------------------------


class TestComputeDailyReturns:
    """Tests for compute_daily_returns()."""

    def test_should_return_empty_for_single_value(self):
        assert compute_daily_returns([100.0]) == []

    def test_should_return_empty_for_empty_input(self):
        assert compute_daily_returns([]) == []

    def test_should_compute_correct_returns(self):
        returns = compute_daily_returns([100.0, 110.0, 99.0])
        assert len(returns) == 2
        assert abs(returns[0] - 0.1) < 1e-9
        assert abs(returns[1] - (-0.1)) < 1e-9

    def test_should_skip_zero_denominators(self):
        returns = compute_daily_returns([0.0, 100.0, 110.0])
        assert len(returns) == 1
        assert abs(returns[0] - 0.1) < 1e-9


# ---------------------------------------------------------------------------
# compute_risk_metrics
# ---------------------------------------------------------------------------


class TestComputeRiskMetrics:
    """Tests for compute_risk_metrics()."""

    def test_should_return_zero_metrics_for_insufficient_data(self):
        result = compute_risk_metrics([_snap(1, 100)])
        assert isinstance(result, RiskMetrics)
        assert result.annualized_return == 0.0
        assert result.sharpe_ratio is None
        assert result.sortino_ratio is None
        assert result.trading_days == 0

    def test_should_return_none_ratios_for_few_data_points(self):
        snapshots = [_snap(i, 100 + i) for i in range(1, 10)]
        result = compute_risk_metrics(snapshots)
        assert result.trading_days < MIN_DAYS_FOR_RATIOS
        assert result.sharpe_ratio is None
        assert result.sortino_ratio is None

    def test_should_compute_positive_return_for_rising_portfolio(self):
        snapshots = [_snap(i, 100 + i * 0.5) for i in range(1, 32)]
        result = compute_risk_metrics(snapshots)
        assert result.annualized_return > 0
        assert result.annualized_volatility > 0
        assert result.trading_days == 30

    def test_should_compute_sharpe_for_sufficient_data(self):
        snapshots = [_snap(i, 100 + i * 0.3) for i in range(1, 32)]
        result = compute_risk_metrics(snapshots)
        assert result.sharpe_ratio is not None

    def test_should_compute_negative_max_drawdown_for_decline(self):
        values = [100] * 16 + [90] * 16
        snapshots = [_snap(i, values[i - 1]) for i in range(1, 32)]
        result = compute_risk_metrics(snapshots)
        assert result.max_drawdown_pct < 0

    def test_should_compute_calmar_when_drawdown_exists(self):
        values = list(range(100, 131))  # rising from 100 to 130
        values[15] = 80  # create a dip
        snapshots = [_snap(i, values[i - 1]) for i in range(1, 32)]
        result = compute_risk_metrics(snapshots)
        assert result.calmar_ratio is not None

    def test_should_return_none_calmar_when_no_drawdown(self):
        snapshots = [_snap(i, 100 + i) for i in range(1, 32)]
        result = compute_risk_metrics(snapshots)
        assert result.max_drawdown_pct == 0.0
        assert result.calmar_ratio is None

    def test_should_handle_empty_snapshots(self):
        result = compute_risk_metrics([])
        assert result.trading_days == 0
        assert result.annualized_return == 0.0
