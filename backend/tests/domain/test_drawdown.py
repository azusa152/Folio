"""Tests for drawdown analysis functions in domain/analysis/drawdown.py."""

from datetime import date

from domain.analysis.drawdown import (
    compute_drawdown_series,
    compute_max_drawdown,
    find_drawdown_periods,
)


def _snap(day: int, value: float) -> dict:
    """Create a snapshot dict with a fixed month for convenience."""
    return {"snapshot_date": date(2025, 1, day), "total_value": value}


# ---------------------------------------------------------------------------
# compute_drawdown_series
# ---------------------------------------------------------------------------


class TestComputeDrawdownSeries:
    """Tests for compute_drawdown_series()."""

    def test_should_return_empty_for_empty_input(self):
        assert compute_drawdown_series([]) == []

    def test_should_return_zero_drawdown_for_monotonically_increasing(self):
        snapshots = [_snap(1, 100), _snap(2, 110), _snap(3, 120)]
        series = compute_drawdown_series(snapshots)
        assert len(series) == 3
        assert all(p.drawdown_pct == 0.0 for p in series)

    def test_should_compute_correct_drawdown_after_decline(self):
        snapshots = [_snap(1, 100), _snap(2, 80)]
        series = compute_drawdown_series(snapshots)
        assert series[0].drawdown_pct == 0.0
        assert series[1].drawdown_pct == -0.2

    def test_should_track_peak_correctly_through_recovery(self):
        snapshots = [_snap(1, 100), _snap(2, 80), _snap(3, 90), _snap(4, 110)]
        series = compute_drawdown_series(snapshots)
        assert series[0].drawdown_pct == 0.0
        assert series[1].drawdown_pct == -0.2
        assert series[2].peak_value == 100.0
        assert series[3].drawdown_pct == 0.0  # new peak
        assert series[3].peak_value == 110.0

    def test_should_handle_string_dates(self):
        snapshots = [
            {"snapshot_date": "2025-01-01", "total_value": 100},
            {"snapshot_date": "2025-01-02", "total_value": 90},
        ]
        series = compute_drawdown_series(snapshots)
        assert series[0].snapshot_date == date(2025, 1, 1)
        assert series[1].drawdown_pct == -0.1

    def test_should_handle_zero_initial_value(self):
        snapshots = [_snap(1, 0), _snap(2, 100)]
        series = compute_drawdown_series(snapshots)
        assert series[0].drawdown_pct == 0.0
        assert series[1].drawdown_pct == 0.0

    def test_should_handle_single_snapshot(self):
        series = compute_drawdown_series([_snap(1, 100)])
        assert len(series) == 1
        assert series[0].drawdown_pct == 0.0

    def test_should_skip_none_total_value(self):
        snapshots = [
            _snap(1, 100),
            {"snapshot_date": date(2025, 1, 2), "total_value": None},
            _snap(3, 90),
        ]
        series = compute_drawdown_series(snapshots)
        assert len(series) == 2

    def test_should_skip_nan_total_value(self):
        snapshots = [
            _snap(1, 100),
            {"snapshot_date": date(2025, 1, 2), "total_value": float("nan")},
            _snap(3, 90),
        ]
        series = compute_drawdown_series(snapshots)
        assert len(series) == 2


# ---------------------------------------------------------------------------
# compute_max_drawdown
# ---------------------------------------------------------------------------


class TestComputeMaxDrawdown:
    """Tests for compute_max_drawdown()."""

    def test_should_return_zero_for_empty_input(self):
        assert compute_max_drawdown([]) == 0.0

    def test_should_return_zero_for_monotonically_increasing(self):
        snapshots = [_snap(1, 100), _snap(2, 110), _snap(3, 120)]
        assert compute_max_drawdown(snapshots) == 0.0

    def test_should_return_correct_max_drawdown(self):
        snapshots = [_snap(1, 100), _snap(2, 70), _snap(3, 90)]
        assert compute_max_drawdown(snapshots) == -0.3

    def test_should_find_worst_drawdown_across_multiple_declines(self):
        snapshots = [
            _snap(1, 100),
            _snap(2, 90),  # -10%
            _snap(3, 110),  # recovery
            _snap(4, 77),  # -30% from 110 peak
        ]
        result = compute_max_drawdown(snapshots)
        assert round(result, 2) == -0.3


# ---------------------------------------------------------------------------
# find_drawdown_periods
# ---------------------------------------------------------------------------


class TestFindDrawdownPeriods:
    """Tests for find_drawdown_periods()."""

    def test_should_return_empty_for_no_drawdowns(self):
        snapshots = [_snap(1, 100), _snap(2, 110), _snap(3, 120)]
        assert find_drawdown_periods(snapshots) == []

    def test_should_return_empty_for_empty_input(self):
        assert find_drawdown_periods([]) == []

    def test_should_identify_recovered_drawdown_period(self):
        snapshots = [
            _snap(1, 100),
            _snap(2, 85),  # -15%
            _snap(3, 90),
            _snap(4, 100),  # recovery
        ]
        periods = find_drawdown_periods(snapshots, threshold=-0.05)
        assert len(periods) == 1
        assert periods[0].recovery_date == date(2025, 1, 4)
        assert periods[0].max_drawdown_pct == -0.15

    def test_should_identify_unrecovered_drawdown(self):
        snapshots = [
            _snap(1, 100),
            _snap(2, 85),
            _snap(3, 80),
        ]
        periods = find_drawdown_periods(snapshots, threshold=-0.05)
        assert len(periods) == 1
        assert periods[0].recovery_date is None

    def test_should_filter_by_threshold(self):
        snapshots = [
            _snap(1, 100),
            _snap(2, 97),  # -3%, above -5% threshold
            _snap(3, 100),
        ]
        periods = find_drawdown_periods(snapshots, threshold=-0.05)
        assert len(periods) == 0

    def test_should_include_exact_threshold_drawdown(self):
        snapshots = [
            _snap(1, 100),
            _snap(2, 95),  # exactly -5%
            _snap(3, 100),
        ]
        periods = find_drawdown_periods(snapshots, threshold=-0.05)
        assert len(periods) == 1
        assert periods[0].max_drawdown_pct == -0.05

    def test_should_sort_by_worst_drawdown_first(self):
        snapshots = [
            _snap(1, 100),
            _snap(2, 90),  # -10%
            _snap(3, 100),
            _snap(4, 80),  # -20%
            _snap(5, 100),
        ]
        periods = find_drawdown_periods(snapshots, threshold=-0.05)
        assert len(periods) == 2
        assert periods[0].max_drawdown_pct < periods[1].max_drawdown_pct
