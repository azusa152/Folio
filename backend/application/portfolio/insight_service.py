"""Portfolio insight generation service.

Orchestrates data from rebalance, snapshots, and risk metrics to produce
natural-language insight objects for the frontend.
"""

import json
import threading
from datetime import UTC, datetime

from sqlmodel import Session

from application.portfolio.analytics_service import get_risk_metrics
from application.portfolio.rebalance_service import calculate_rebalance
from application.portfolio.snapshot_service import get_snapshots
from domain.analysis.analysis import compute_twr
from domain.core.constants import DRIFT_THRESHOLD_PCT
from domain.portfolio.insights import (
    Insight,
    generate_allocation_insights,
    generate_performance_insights,
)
from logging_config import get_logger

logger = get_logger(__name__)

_insight_cache: dict[str, list[dict]] = {}
_insight_cache_ts: dict[str, float] = {}
_insight_cache_lock = threading.Lock()
_INSIGHT_CACHE_TTL = 300


def invalidate_insight_cache() -> None:
    """Clear the insight cache (call after holdings or persona changes)."""
    with _insight_cache_lock:
        _insight_cache.clear()
        _insight_cache_ts.clear()


def get_portfolio_insights(
    session: Session,
    display_currency: str = "USD",
) -> list[dict]:
    """Generate portfolio insights from allocation, performance, and risk data.

    Results are cached per ``display_currency`` for 300 seconds.
    """
    now = datetime.now(UTC).timestamp()
    with _insight_cache_lock:
        cached = _insight_cache.get(display_currency)
        ts = _insight_cache_ts.get(display_currency, 0)
        if cached is not None and (now - ts) < _INSIGHT_CACHE_TTL:
            return cached

    try:
        rebalance = calculate_rebalance(session, display_currency)
        categories = rebalance.get("categories", {})
        health_score = rebalance.get("health_score", 0)
    except Exception:
        logger.warning("無法載入再平衡資料，跳過配置洞察", exc_info=True)
        categories = {}
        health_score = 0

    snapshots = get_snapshots(session, days=365)
    snapshot_dicts = (
        [
            {"snapshot_date": s.snapshot_date, "total_value": s.total_value}
            for s in snapshots
        ]
        if snapshots
        else []
    )
    twr_pct = compute_twr(snapshot_dicts) if snapshot_dicts else None
    twr = twr_pct / 100 if twr_pct is not None else None

    benchmark_return: float | None = None
    if len(snapshots) >= 2:
        first_bm = json.loads(snapshots[0].benchmark_values or "{}")
        last_bm = json.loads(snapshots[-1].benchmark_values or "{}")
        sp_first = first_bm.get("^GSPC")
        sp_last = last_bm.get("^GSPC")
        if sp_first and sp_last and sp_first > 0:
            benchmark_return = (sp_last - sp_first) / sp_first

    risk = get_risk_metrics(session)
    max_dd = risk.get("max_drawdown_pct", 0)
    sharpe = risk.get("sharpe_ratio")

    insights: list[Insight] = []
    insights.extend(
        generate_allocation_insights(categories, DRIFT_THRESHOLD_PCT, health_score)
    )
    insights.extend(
        generate_performance_insights(twr, benchmark_return, max_dd, sharpe)
    )

    logger.info("產生 %d 條投資組合洞察 (幣別=%s)", len(insights), display_currency)

    result = [
        {
            "key": i.key,
            "severity": i.severity,
            "vars": i.vars,
            "category": i.category,
        }
        for i in insights
    ]

    with _insight_cache_lock:
        _insight_cache[display_currency] = result
        _insight_cache_ts[display_currency] = now

    return result
