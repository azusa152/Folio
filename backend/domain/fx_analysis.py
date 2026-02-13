"""
Domain — 匯率變動分析純函式。
不依賴任何外部服務、資料庫或框架。
"""

from __future__ import annotations

from dataclasses import dataclass

from domain.constants import (
    FX_DAILY_SPIKE_PCT,
    FX_LONG_TERM_TREND_PCT,
    FX_SHORT_TERM_SWING_PCT,
)
from domain.enums import FXAlertType


@dataclass(frozen=True)
class FXRateAlert:
    """單一匯率變動警報。"""

    pair: str  # e.g. "USD/TWD"
    alert_type: FXAlertType
    change_pct: float  # signed percentage change
    direction: str  # "up" / "down"
    current_rate: float
    period_label: str  # "1 日" / "5 日" / "3 個月"


def _compute_change_pct(
    history: list[dict],
    start_idx: int = 0,
    end_idx: int = -1,
) -> float | None:
    """
    從 history[start_idx] 到 history[end_idx] 計算百分比變動。
    history 格式: [{"date": "...", "close": float}, ...]
    回傳 signed percentage; 若資料不足回傳 None。
    """
    if not history or len(history) < 2:
        return None
    first = history[start_idx]["close"]
    last = history[end_idx]["close"]
    if first <= 0:
        return None
    return round(((last - first) / first) * 100, 2)


def _direction(pct: float) -> str:
    return "up" if pct > 0 else ("down" if pct < 0 else "flat")


def analyze_fx_rate_changes(
    pair: str,
    current_rate: float,
    short_history: list[dict],
    long_history: list[dict],
) -> list[FXRateAlert]:
    """
    分析單一貨幣對的匯率變動，偵測三種警報：

    1. Daily spike: 最近一日 vs 前一日 > FX_DAILY_SPIKE_PCT
    2. Short-term swing: 5 日首尾 > FX_SHORT_TERM_SWING_PCT
    3. Long-term trend: 3 月首尾 > FX_LONG_TERM_TREND_PCT

    純函式，不依賴外部狀態。
    """
    alerts: list[FXRateAlert] = []

    # 1) Daily spike: last two data points in short_history
    if len(short_history) >= 2:
        daily_pct = _compute_change_pct(short_history, -2, -1)
        if daily_pct is not None and abs(daily_pct) >= FX_DAILY_SPIKE_PCT:
            alerts.append(
                FXRateAlert(
                    pair=pair,
                    alert_type=FXAlertType.DAILY_SPIKE,
                    change_pct=daily_pct,
                    direction=_direction(daily_pct),
                    current_rate=current_rate,
                    period_label="1 日",
                )
            )

    # 2) Short-term swing: first to last in short_history
    if len(short_history) >= 2:
        swing_pct = _compute_change_pct(short_history, 0, -1)
        if swing_pct is not None and abs(swing_pct) >= FX_SHORT_TERM_SWING_PCT:
            alerts.append(
                FXRateAlert(
                    pair=pair,
                    alert_type=FXAlertType.SHORT_TERM_SWING,
                    change_pct=swing_pct,
                    direction=_direction(swing_pct),
                    current_rate=current_rate,
                    period_label="5 日",
                )
            )

    # 3) Long-term trend: first to last in long_history
    if len(long_history) >= 2:
        trend_pct = _compute_change_pct(long_history, 0, -1)
        if trend_pct is not None and abs(trend_pct) >= FX_LONG_TERM_TREND_PCT:
            alerts.append(
                FXRateAlert(
                    pair=pair,
                    alert_type=FXAlertType.LONG_TERM_TREND,
                    change_pct=trend_pct,
                    direction=_direction(trend_pct),
                    current_rate=current_rate,
                    period_label="3 個月",
                )
            )

    return alerts


def determine_fx_risk_level(all_alerts: list[FXRateAlert]) -> str:
    """
    根據觸發的警報類型決定整體匯率風險等級。

    - 含 daily_spike => "high"
    - 含 short_term_swing => "medium"
    - 其他 => "low"
    """
    alert_types = {a.alert_type for a in all_alerts}
    if FXAlertType.DAILY_SPIKE in alert_types:
        return "high"
    if FXAlertType.SHORT_TERM_SWING in alert_types:
        return "medium"
    return "low"
