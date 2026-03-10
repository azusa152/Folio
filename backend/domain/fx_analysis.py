"""Backward-compatibility shim — re-exports domain.analysis.fx_analysis.

Consumers using ``from domain.fx_analysis import X`` continue to work unchanged.
"""

from domain.analysis.fx_analysis import (  # noqa: F401
    FXRateAlert,
    FXRecentHighSignal,
    FXTimingResult,
    analyze_fx_rate_changes,
    analyze_recent_high,
    assess_exchange_timing,
    compute_sma,
    count_consecutive_increases,
    detect_trend_direction,
    determine_fx_risk_level,
    find_high_recency,
    is_recent_high,
)
