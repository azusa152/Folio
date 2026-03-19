"""Portfolio analytics service — drawdown, risk metrics, contribution."""

from datetime import date

from sqlmodel import Session

from application.portfolio.snapshot_service import get_snapshot_range, get_snapshots
from domain.analysis.drawdown import compute_drawdown_series
from domain.analysis.risk_metrics import RiskMetrics, compute_risk_metrics
from domain.constants import ANALYTICS_DEFAULT_LOOKBACK_DAYS
from logging_config import get_logger

logger = get_logger(__name__)


def _load_snapshot_dicts(
    session: Session,
    start: date | None = None,
    end: date | None = None,
) -> list[dict]:
    """Load snapshots as dicts with snapshot_date, total_value, cost_basis_total."""
    if start is not None and end is not None:
        snapshots = get_snapshot_range(session, start=start, end=end)
    else:
        snapshots = get_snapshots(session, days=ANALYTICS_DEFAULT_LOOKBACK_DAYS)

    return [
        {
            "snapshot_date": snapshot.snapshot_date,
            "total_value": snapshot.total_value,
            "cost_basis_total": snapshot.cost_basis_total,
        }
        for snapshot in snapshots
    ]


def get_drawdown_series(
    session: Session,
    start: date | None = None,
    end: date | None = None,
) -> list[dict]:
    """Compute drawdown series from portfolio snapshots."""
    snapshots = _load_snapshot_dicts(session, start=start, end=end)
    logger.info("計算 drawdown 序列：%d 筆快照", len(snapshots))
    series = compute_drawdown_series(snapshots)
    return [
        {
            "date": point.snapshot_date.isoformat(),
            "drawdown_pct": point.drawdown_pct,
            "total_value": point.total_value,
            "peak_value": point.peak_value,
        }
        for point in series
    ]


def get_risk_metrics(
    session: Session,
    start: date | None = None,
    end: date | None = None,
) -> dict:
    """Compute risk-adjusted metrics from portfolio snapshots."""
    snapshots = _load_snapshot_dicts(session, start=start, end=end)
    logger.info("計算風險指標：%d 筆快照", len(snapshots))
    metrics: RiskMetrics = compute_risk_metrics(snapshots)
    return {
        "annualized_return": metrics.annualized_return,
        "annualized_volatility": metrics.annualized_volatility,
        "sharpe_ratio": metrics.sharpe_ratio,
        "sortino_ratio": metrics.sortino_ratio,
        "max_drawdown_pct": metrics.max_drawdown_pct,
        "calmar_ratio": metrics.calmar_ratio,
        "trading_days": metrics.trading_days,
    }


def get_contribution_vs_growth(
    session: Session,
    start: date | None = None,
    end: date | None = None,
) -> list[dict]:
    """Return time series of cost basis (contributions) vs market value."""
    snapshots = _load_snapshot_dicts(session, start=start, end=end)
    logger.info("計算貢獻 vs 成長序列：%d 筆快照", len(snapshots))
    return [
        {
            "date": (
                snapshot["snapshot_date"].isoformat()
                if isinstance(snapshot["snapshot_date"], date)
                else snapshot["snapshot_date"]
            ),
            "market_value": snapshot["total_value"],
            "cost_basis": snapshot.get("cost_basis_total"),
        }
        for snapshot in snapshots
    ]
