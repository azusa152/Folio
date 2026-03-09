"""Drawdown analysis — peak-to-trough decline computation.

All functions are pure — no external dependencies.  Snapshots are expected
to be sorted by date ascending; each dict must contain ``snapshot_date``
(``date`` or ISO-8601 ``str``) and ``total_value`` (``float``).
Snapshots with ``None`` or ``NaN`` ``total_value`` are skipped.
"""

import math
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class DrawdownPoint:
    """Single point in the drawdown series."""

    snapshot_date: date
    total_value: float
    peak_value: float
    drawdown_pct: float  # negative value, e.g. -0.15 for 15% decline


@dataclass(frozen=True)
class DrawdownPeriod:
    """A peak-to-recovery drawdown period."""

    peak_date: date
    trough_date: date
    recovery_date: date | None  # None if still in drawdown
    peak_value: float
    trough_value: float
    max_drawdown_pct: float  # negative, e.g. -0.23
    duration_days: int


def _parse_date(raw: date | str) -> date:
    return date.fromisoformat(raw) if isinstance(raw, str) else raw


def compute_drawdown_series(
    snapshots: list[dict],
) -> list[DrawdownPoint]:
    """
    Compute rolling drawdown from peak for each snapshot.

    Returns:
        List of DrawdownPoint, one per valid snapshot.
    """
    if not snapshots:
        return []

    result: list[DrawdownPoint] = []
    peak = 0.0

    for s in snapshots:
        value = s.get("total_value")
        if value is None or (isinstance(value, float) and math.isnan(value)):
            continue

        snap_date = _parse_date(s["snapshot_date"])

        if value > peak:
            peak = value

        dd_pct = (value - peak) / peak if peak > 0 else 0.0

        result.append(
            DrawdownPoint(
                snapshot_date=snap_date,
                total_value=value,
                peak_value=peak,
                drawdown_pct=round(dd_pct, 6),
            )
        )

    return result


def compute_max_drawdown(snapshots: list[dict]) -> float:
    """Return the maximum drawdown percentage (negative value)."""
    series = compute_drawdown_series(snapshots)
    if not series:
        return 0.0
    return min(p.drawdown_pct for p in series)


def find_drawdown_periods(
    snapshots: list[dict],
    threshold: float = -0.05,
) -> list[DrawdownPeriod]:
    """
    Identify distinct drawdown periods that reach or exceed *threshold*.

    Args:
        threshold: inclusive minimum drawdown to qualify (e.g. -0.05 means
                   a 5% decline is included).

    Returns:
        List of DrawdownPeriod, sorted by max_drawdown_pct ascending (worst first).
    """
    series = compute_drawdown_series(snapshots)
    if not series:
        return []

    _EPS = 1e-9
    periods: list[DrawdownPeriod] = []
    peak_date = series[0].snapshot_date
    peak_value = series[0].total_value
    trough_date = peak_date
    trough_value = peak_value
    in_drawdown = False

    for point in series:
        if abs(point.drawdown_pct) < _EPS:
            if in_drawdown and peak_value > 0:
                dd_pct = (trough_value - peak_value) / peak_value
                if dd_pct <= threshold:
                    periods.append(
                        DrawdownPeriod(
                            peak_date=peak_date,
                            trough_date=trough_date,
                            recovery_date=point.snapshot_date,
                            peak_value=peak_value,
                            trough_value=trough_value,
                            max_drawdown_pct=round(dd_pct, 6),
                            duration_days=(point.snapshot_date - peak_date).days,
                        )
                    )
            peak_date = point.snapshot_date
            peak_value = point.total_value
            trough_date = peak_date
            trough_value = peak_value
            in_drawdown = False
        else:
            in_drawdown = True
            if point.total_value < trough_value:
                trough_value = point.total_value
                trough_date = point.snapshot_date

    if in_drawdown and peak_value > 0:
        dd_pct = (trough_value - peak_value) / peak_value
        if dd_pct <= threshold:
            periods.append(
                DrawdownPeriod(
                    peak_date=peak_date,
                    trough_date=trough_date,
                    recovery_date=None,
                    peak_value=peak_value,
                    trough_value=trough_value,
                    max_drawdown_pct=round(dd_pct, 6),
                    duration_days=(series[-1].snapshot_date - peak_date).days,
                )
            )

    return sorted(periods, key=lambda p: p.max_drawdown_pct)
