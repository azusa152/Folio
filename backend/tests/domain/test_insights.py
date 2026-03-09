"""Unit tests for domain.portfolio.insights — insight generation rules."""

import pytest

from domain.portfolio.insights import (
    Insight,
    InsightSeverity,
    generate_allocation_insights,
    generate_performance_insights,
)


class TestGenerateAllocationInsights:
    """Tests for allocation insight generation."""

    def test_should_warn_on_high_concentration(self):
        categories = {
            "Tech": {"market_value": 50000},
            "Bonds": {"market_value": 10000},
        }
        insights = generate_allocation_insights(
            categories, drift_threshold=5.0, health_score=70
        )
        conc = [i for i in insights if i.key == "insight.high_concentration"]
        assert len(conc) == 1
        assert conc[0].severity == InsightSeverity.WARNING
        assert conc[0].vars["category"] == "Tech"
        assert conc[0].vars["weight_pct"] == pytest.approx(83.3, abs=0.1)

    def test_should_not_warn_when_balanced(self):
        categories = {
            "Tech": {"market_value": 30000},
            "Bonds": {"market_value": 30000},
            "Cash": {"market_value": 30000},
        }
        insights = generate_allocation_insights(
            categories, drift_threshold=5.0, health_score=70
        )
        conc = [i for i in insights if i.key == "insight.high_concentration"]
        assert len(conc) == 0

    def test_should_flag_drift_exceeding_threshold(self):
        categories = {
            "Tech": {"market_value": 50000, "drift": 8.0},
            "Bonds": {"market_value": 50000, "drift": -2.0},
        }
        insights = generate_allocation_insights(
            categories, drift_threshold=5.0, health_score=70
        )
        drift = [i for i in insights if i.key == "insight.drift_exceeds_threshold"]
        assert len(drift) == 1
        assert drift[0].severity == InsightSeverity.ACTION
        assert drift[0].vars["category"] == "Tech"

    def test_should_praise_excellent_health(self):
        insights = generate_allocation_insights(
            {}, drift_threshold=5.0, health_score=90
        )
        health = [i for i in insights if i.key == "insight.health_excellent"]
        assert len(health) == 1
        assert health[0].severity == InsightSeverity.POSITIVE

    def test_should_warn_on_poor_health(self):
        insights = generate_allocation_insights(
            {}, drift_threshold=5.0, health_score=40
        )
        health = [i for i in insights if i.key == "insight.health_needs_attention"]
        assert len(health) == 1
        assert health[0].severity == InsightSeverity.WARNING

    def test_should_skip_health_insight_in_middle_range(self):
        insights = generate_allocation_insights(
            {}, drift_threshold=5.0, health_score=65
        )
        health = [i for i in insights if "health" in i.key]
        assert len(health) == 0

    def test_should_handle_zero_total_market_value(self):
        categories = {"Tech": {"market_value": 0}}
        insights = generate_allocation_insights(
            categories, drift_threshold=5.0, health_score=70
        )
        conc = [i for i in insights if i.key == "insight.high_concentration"]
        assert len(conc) == 0


class TestGeneratePerformanceInsights:
    """Tests for performance and risk insight generation."""

    def test_should_detect_outperformance(self):
        insights = generate_performance_insights(
            twr=0.15,
            benchmark_return=0.10,
            max_drawdown_pct=-0.05,
            sharpe=0.8,
        )
        out = [i for i in insights if i.key == "insight.outperforming_benchmark"]
        assert len(out) == 1
        assert out[0].vars["return_pct"] == 15.0
        assert out[0].vars["alpha_pct"] == 5.0

    def test_should_detect_underperformance(self):
        insights = generate_performance_insights(
            twr=0.03,
            benchmark_return=0.10,
            max_drawdown_pct=-0.05,
            sharpe=0.5,
        )
        under = [i for i in insights if i.key == "insight.underperforming_benchmark"]
        assert len(under) == 1
        assert under[0].vars["lag_pct"] == 7.0

    def test_should_not_generate_benchmark_insight_for_small_alpha(self):
        insights = generate_performance_insights(
            twr=0.10,
            benchmark_return=0.095,
            max_drawdown_pct=-0.05,
            sharpe=0.8,
        )
        bench = [i for i in insights if "benchmark" in i.key]
        assert len(bench) == 0

    def test_should_warn_on_severe_drawdown(self):
        insights = generate_performance_insights(
            twr=None,
            benchmark_return=None,
            max_drawdown_pct=-0.25,
            sharpe=None,
        )
        dd = [i for i in insights if i.key == "insight.severe_drawdown"]
        assert len(dd) == 1
        assert dd[0].vars["drawdown_pct"] == 25.0

    def test_should_note_moderate_drawdown(self):
        insights = generate_performance_insights(
            twr=None,
            benchmark_return=None,
            max_drawdown_pct=-0.15,
            sharpe=None,
        )
        dd = [i for i in insights if i.key == "insight.moderate_drawdown"]
        assert len(dd) == 1
        assert dd[0].severity == InsightSeverity.INFO

    def test_should_not_flag_small_drawdown(self):
        insights = generate_performance_insights(
            twr=None,
            benchmark_return=None,
            max_drawdown_pct=-0.05,
            sharpe=None,
        )
        dd = [i for i in insights if "drawdown" in i.key]
        assert len(dd) == 0

    def test_should_praise_strong_sharpe(self):
        insights = generate_performance_insights(
            twr=None,
            benchmark_return=None,
            max_drawdown_pct=-0.05,
            sharpe=1.5,
        )
        sr = [i for i in insights if i.key == "insight.strong_risk_adjusted"]
        assert len(sr) == 1

    def test_should_warn_on_negative_sharpe(self):
        insights = generate_performance_insights(
            twr=None,
            benchmark_return=None,
            max_drawdown_pct=-0.05,
            sharpe=-0.3,
        )
        sr = [i for i in insights if i.key == "insight.negative_risk_adjusted"]
        assert len(sr) == 1

    def test_should_skip_sharpe_insight_for_middling_value(self):
        insights = generate_performance_insights(
            twr=None,
            benchmark_return=None,
            max_drawdown_pct=-0.05,
            sharpe=0.5,
        )
        sr = [i for i in insights if "risk_adjusted" in i.key]
        assert len(sr) == 0

    def test_should_handle_none_twr_and_benchmark(self):
        insights = generate_performance_insights(
            twr=None,
            benchmark_return=None,
            max_drawdown_pct=-0.05,
            sharpe=None,
        )
        assert len(insights) == 0


class TestInsightDataclass:
    """Tests for the Insight dataclass itself."""

    def test_should_be_frozen(self):
        i = Insight(key="test", severity="info")
        with pytest.raises(AttributeError):
            i.key = "changed"  # type: ignore[misc]

    def test_should_have_default_category(self):
        i = Insight(key="test", severity="info")
        assert i.category == "general"
        assert i.vars == {}
