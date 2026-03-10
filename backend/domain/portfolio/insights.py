"""Portfolio insight definitions and generation rules.

Pure domain logic — no external dependencies. Generates structured insight
objects from allocation, performance, and risk data.
"""

from dataclasses import dataclass, field
from enum import StrEnum

from domain.core.constants import (
    INSIGHT_CONCENTRATION_THRESHOLD,
    INSIGHT_EXCELLENT_HEALTH_SCORE,
    INSIGHT_MODERATE_DRAWDOWN_THRESHOLD,
    INSIGHT_OUTPERFORMANCE_THRESHOLD,
    INSIGHT_POOR_HEALTH_SCORE,
    INSIGHT_SEVERE_DRAWDOWN_THRESHOLD,
    INSIGHT_STRONG_SHARPE,
    INSIGHT_UNDERPERFORMANCE_THRESHOLD,
)


class InsightSeverity(StrEnum):
    INFO = "info"
    POSITIVE = "positive"
    WARNING = "warning"
    ACTION = "action"


@dataclass(frozen=True)
class Insight:
    """A single natural-language insight about the portfolio."""

    key: str
    severity: str
    vars: dict = field(default_factory=dict)
    category: str = "general"


def generate_allocation_insights(
    categories: dict[str, dict],
    drift_threshold: float,
    health_score: float,
) -> list[Insight]:
    """Generate insights from allocation data.

    Args:
        categories: Mapping of category name to dict with ``market_value``
            and optional ``drift_pct`` (percentage points off target).
        drift_threshold: Maximum acceptable drift in percentage points.
        health_score: Portfolio health score (0–100).
    """
    insights: list[Insight] = []

    total = sum((info.get("market_value") or 0) for info in categories.values())
    if total > 0:
        for cat, info in categories.items():
            weight = (info.get("market_value") or 0) / total
            if weight > INSIGHT_CONCENTRATION_THRESHOLD:
                insights.append(
                    Insight(
                        key="insight.high_concentration",
                        severity=InsightSeverity.WARNING,
                        vars={"category": cat, "weight_pct": round(weight * 100, 1)},
                        category="allocation",
                    )
                )

    for cat, info in categories.items():
        drift = abs(info.get("drift_pct") or info.get("drift") or 0)
        if drift > drift_threshold:
            insights.append(
                Insight(
                    key="insight.drift_exceeds_threshold",
                    severity=InsightSeverity.ACTION,
                    vars={"category": cat, "drift_pct": round(drift, 1)},
                    category="allocation",
                )
            )

    if health_score >= INSIGHT_EXCELLENT_HEALTH_SCORE:
        insights.append(
            Insight(
                key="insight.health_excellent",
                severity=InsightSeverity.POSITIVE,
                vars={"score": round(health_score)},
                category="general",
            )
        )
    elif health_score < INSIGHT_POOR_HEALTH_SCORE:
        insights.append(
            Insight(
                key="insight.health_needs_attention",
                severity=InsightSeverity.WARNING,
                vars={"score": round(health_score)},
                category="general",
            )
        )

    return insights


def generate_performance_insights(
    twr: float | None,
    benchmark_return: float | None,
    max_drawdown_pct: float,
    sharpe: float | None,
) -> list[Insight]:
    """Generate insights from performance and risk data.

    All return/drawdown values are decimal fractions (e.g. 0.12 = 12%).
    """
    insights: list[Insight] = []

    if twr is not None and benchmark_return is not None:
        alpha = twr - benchmark_return
        if alpha > INSIGHT_OUTPERFORMANCE_THRESHOLD:
            insights.append(
                Insight(
                    key="insight.outperforming_benchmark",
                    severity=InsightSeverity.POSITIVE,
                    vars={
                        "return_pct": round(twr * 100, 1),
                        "alpha_pct": round(alpha * 100, 1),
                    },
                    category="performance",
                )
            )
        elif alpha < INSIGHT_UNDERPERFORMANCE_THRESHOLD:
            insights.append(
                Insight(
                    key="insight.underperforming_benchmark",
                    severity=InsightSeverity.WARNING,
                    vars={
                        "return_pct": round(twr * 100, 1),
                        "lag_pct": round(abs(alpha) * 100, 1),
                    },
                    category="performance",
                )
            )

    if max_drawdown_pct < INSIGHT_SEVERE_DRAWDOWN_THRESHOLD:
        insights.append(
            Insight(
                key="insight.severe_drawdown",
                severity=InsightSeverity.WARNING,
                vars={"drawdown_pct": round(abs(max_drawdown_pct) * 100, 1)},
                category="risk",
            )
        )
    elif max_drawdown_pct < INSIGHT_MODERATE_DRAWDOWN_THRESHOLD:
        insights.append(
            Insight(
                key="insight.moderate_drawdown",
                severity=InsightSeverity.INFO,
                vars={"drawdown_pct": round(abs(max_drawdown_pct) * 100, 1)},
                category="risk",
            )
        )

    if sharpe is not None:
        if sharpe > INSIGHT_STRONG_SHARPE:
            insights.append(
                Insight(
                    key="insight.strong_risk_adjusted",
                    severity=InsightSeverity.POSITIVE,
                    vars={"sharpe": sharpe},
                    category="risk",
                )
            )
        elif sharpe < 0:
            insights.append(
                Insight(
                    key="insight.negative_risk_adjusted",
                    severity=InsightSeverity.WARNING,
                    vars={"sharpe": sharpe},
                    category="risk",
                )
            )

    return insights
