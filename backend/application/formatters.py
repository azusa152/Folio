"""
Application — 表示層格式化函式。
將原始數值資料轉換為使用者可讀的狀態文字。
"""

from typing import Optional

from domain.constants import (
    BIAS_OVERHEATED_THRESHOLD,
    BIAS_OVERSOLD_THRESHOLD,
    MA200_WINDOW,
    RSI_OVERBOUGHT,
    RSI_OVERSOLD,
)


def build_signal_status(signals: dict) -> list[str]:
    """
    根據原始技術訊號數值，產生使用者可讀的狀態描述列表。
    """
    status_parts: list[str] = []

    rsi = signals.get("rsi")
    price = signals.get("price")
    ma200 = signals.get("ma200")
    ma60 = signals.get("ma60")
    bias = signals.get("bias")

    if rsi is not None:
        if rsi < RSI_OVERSOLD:
            status_parts.append(f"🟢 RSI={rsi} 超賣區間（可能是機會）")
        elif rsi > RSI_OVERBOUGHT:
            status_parts.append(f"🔴 RSI={rsi} 超買區間（留意回檔）")
        else:
            status_parts.append(f"⚪ RSI={rsi} 中性")

    if ma200 is not None:
        if price is not None and price < ma200:
            status_parts.append(f"🔴 股價 {price} 跌破 200MA ({ma200})")
        else:
            status_parts.append(f"🟢 股價 {price} 站穩 200MA ({ma200})")
    else:
        status_parts.append(f"⚠️ 資料不足 {MA200_WINDOW} 天，無法計算 200MA")

    if ma60 is not None:
        if price is not None and price < ma60:
            status_parts.append(f"🔴 股價 {price} 跌破 60MA ({ma60})")
        else:
            status_parts.append(f"🟢 股價 {price} 站穩 60MA ({ma60})")

    if bias is not None:
        if bias > BIAS_OVERHEATED_THRESHOLD:
            status_parts.append(f"🔴 乖離率 {bias}% 過熱")
        elif bias < BIAS_OVERSOLD_THRESHOLD:
            status_parts.append(f"🟢 乖離率 {bias}% 超跌")

    return status_parts


def build_moat_details(
    moat_status_value: str,
    current_margin: Optional[float],
    previous_margin: Optional[float],
    change: float,
) -> str:
    """
    根據護城河判定結果，產生使用者可讀的詳情文字。
    """
    from domain.enums import MoatStatus

    if moat_status_value == MoatStatus.DETERIORATING.value:
        return (
            f"毛利率衰退！{current_margin}% → 去年同期 {previous_margin}%"
            f"（下降 {abs(change)} 個百分點）— 護城河鬆動！"
        )
    return (
        f"毛利率穩健：{current_margin}% vs 去年同期 {previous_margin}%"
        f"（{'+' if change >= 0 else ''}{change} 個百分點）"
    )
