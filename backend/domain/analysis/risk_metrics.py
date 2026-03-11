"""Risk-adjusted return metrics — Sharpe, Sortino, volatility.

Conventions
-----------
* **Sharpe** uses *sample* standard deviation (``n - 1``) for annualized
  volatility, which is the unbiased estimator for population variance.
* **Sortino** uses *population* variance (``n``) over downside returns only,
  following the Sortino & van der Meer (1991) definition where downside
  deviation is the root-mean-square of negative excess returns.
* **Annualized return** is the arithmetic-mean daily return compounded over
  252 trading days — a common approximation that is accurate for small
  daily moves.

Snapshots with ``None`` / ``NaN`` values are silently skipped.
"""

import math
from dataclasses import dataclass

from domain.analysis.drawdown import compute_max_drawdown
from domain.core.constants import (
    ANALYTICS_MIN_DAYS_FOR_RATIOS,
    ANALYTICS_MIN_DOWNSIDE_SAMPLES,
    ANALYTICS_RISK_FREE_RATE,
    ANALYTICS_TRADING_DAYS_PER_YEAR,
)


@dataclass(frozen=True)
class RiskMetrics:
    """Portfolio risk metrics computed from daily return series."""

    annualized_return: float
    annualized_volatility: float
    sharpe_ratio: float | None  # None if < 30 data points
    sortino_ratio: float | None  # None if < 30 data points
    max_drawdown_pct: float
    calmar_ratio: float | None  # annualized_return / abs(max_drawdown)
    trading_days: int


TRADING_DAYS_PER_YEAR = ANALYTICS_TRADING_DAYS_PER_YEAR
RISK_FREE_RATE = ANALYTICS_RISK_FREE_RATE
MIN_DAYS_FOR_RATIOS = ANALYTICS_MIN_DAYS_FOR_RATIOS
MIN_DOWNSIDE_SAMPLES = ANALYTICS_MIN_DOWNSIDE_SAMPLES


def compute_daily_returns(values: list[float]) -> list[float]:
    """Compute daily percentage returns from a value series.

    Periods where the prior value is zero are skipped (cannot compute a
    percentage change).
    """
    if len(values) < 2:
        return []
    return [
        (values[i] - values[i - 1]) / values[i - 1]
        for i in range(1, len(values))
        if values[i - 1] != 0
    ]


def compute_risk_metrics(
    snapshots: list[dict],
    risk_free_rate: float = RISK_FREE_RATE,
) -> RiskMetrics:
    """
    Compute risk-adjusted metrics from portfolio snapshots.

    Args:
        snapshots: sorted ascending by date, each with "total_value".
        risk_free_rate: annualized risk-free rate.
    """
    values: list[float] = []
    for s in snapshots:
        v = s.get("total_value")
        if v is not None and not (isinstance(v, float) and math.isnan(v)):
            values.append(float(v))
    daily_returns = compute_daily_returns(values)
    n = len(daily_returns)

    if n < 2:
        return RiskMetrics(
            annualized_return=0.0,
            annualized_volatility=0.0,
            sharpe_ratio=None,
            sortino_ratio=None,
            max_drawdown_pct=compute_max_drawdown(snapshots),
            calmar_ratio=None,
            trading_days=n,
        )

    mean_daily = sum(daily_returns) / n
    annualized_return = (1 + mean_daily) ** TRADING_DAYS_PER_YEAR - 1

    variance = sum((r - mean_daily) ** 2 for r in daily_returns) / (n - 1)
    daily_vol = math.sqrt(variance)
    annualized_vol = daily_vol * math.sqrt(TRADING_DAYS_PER_YEAR)

    daily_rf = (1 + risk_free_rate) ** (1 / TRADING_DAYS_PER_YEAR) - 1
    excess_returns = [r - daily_rf for r in daily_returns]

    sharpe = None
    if n >= MIN_DAYS_FOR_RATIOS and annualized_vol > 0:
        sharpe = round((annualized_return - risk_free_rate) / annualized_vol, 3)

    sortino = None
    downside_returns = [r for r in excess_returns if r < 0]
    if len(downside_returns) >= MIN_DOWNSIDE_SAMPLES and n >= MIN_DAYS_FOR_RATIOS:
        # Population variance (/n) per Sortino & van der Meer (1991) definition
        downside_var = sum(r**2 for r in downside_returns) / len(downside_returns)
        downside_vol = math.sqrt(downside_var) * math.sqrt(TRADING_DAYS_PER_YEAR)
        if downside_vol > 0:
            sortino = round((annualized_return - risk_free_rate) / downside_vol, 3)

    max_dd = compute_max_drawdown(snapshots)

    calmar = None
    if max_dd < 0:
        calmar = round(annualized_return / abs(max_dd), 3)

    return RiskMetrics(
        annualized_return=round(annualized_return, 6),
        annualized_volatility=round(annualized_vol, 6),
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        max_drawdown_pct=round(max_dd, 6),
        calmar_ratio=calmar,
        trading_days=n,
    )
