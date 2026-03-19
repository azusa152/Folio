"""
Application — 表示層格式化函式。
將原始數值資料轉換為使用者可讀的狀態文字。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domain.withdrawal import WithdrawalPlan

from i18n import t

# ---------------------------------------------------------------------------
# 恐懼與貪婪指數格式化
# ---------------------------------------------------------------------------

_FEAR_GREED_ICON: dict[str, str] = {
    "EXTREME_FEAR": "😱",
    "FEAR": "😨",
    "NEUTRAL": "😐",
    "GREED": "🤑",
    "EXTREME_GREED": "🤯",
    "N/A": "⏳",
}


def format_fear_greed_label(level: str, score: int, lang: str = "zh-TW") -> str:
    """
    格式化恐懼與貪婪等級為標籤（含 icon 與分數）。
    例如：「😱 極度恐慌（15）」
    """
    label_key = f"formatter.fear_greed_{level.lower()}"
    label = t(label_key, score=score, lang=lang)
    return label


def format_fear_greed_short(level: str, lang: str = "zh-TW") -> str:
    """
    格式化恐懼與貪婪等級為精簡標籤（icon + 文字）。
    例如：「😱 極度恐懼」
    """
    icon = _FEAR_GREED_ICON.get(level, "⏳")
    label_key = f"formatter.fear_greed_{level.lower()}"
    label = t(label_key, lang=lang)
    return f"{icon} {label}"


# ---------------------------------------------------------------------------
# 聰明提款格式化
# ---------------------------------------------------------------------------


def format_withdrawal_telegram(
    plan: WithdrawalPlan, display_currency: str = "USD", lang: str = "zh-TW"
) -> str:
    """
    將 WithdrawalPlan 格式化為 Telegram HTML 訊息。

    Args:
        plan: domain.withdrawal.WithdrawalPlan 實例
        display_currency: 顯示幣別
        lang: 語言代碼

    Returns:
        Telegram HTML 格式訊息字串
    """
    from domain.constants import CATEGORY_ICON

    parts: list[str] = [
        t(
            "formatter.withdrawal_header",
            lang=lang,
            amount=f"{plan.target_amount:,.2f}",
            currency=display_currency,
        ),
    ]

    if not plan.recommendations:
        parts.append(t("formatter.withdrawal_no_holdings", lang=lang))
        return "\n".join(parts)

    parts.append(t("formatter.withdrawal_recommendations", lang=lang))
    for i, rec in enumerate(plan.recommendations, 1):
        icon = CATEGORY_ICON.get(rec.category, "📊")
        pl_text = ""
        if rec.unrealized_pl is not None:
            pl_sign = "+" if rec.unrealized_pl >= 0 else ""
            pl_text = t(
                "formatter.withdrawal_pl",
                lang=lang,
                sign=pl_sign,
                amount=f"{rec.unrealized_pl:,.2f}",
                currency=display_currency,
            )
        priority_label = t(
            f"formatter.priority_{['rebalance', 'tax', 'liquidity'][rec.priority - 1]}",
            lang=lang,
        )
        parts.append(
            f"\n{i}. {icon} <b>{rec.ticker}</b> ({rec.category})"
            f" — {t('formatter.sell', lang=lang)} {rec.quantity_to_sell:,.4g} "
            f"{t('formatter.shares', lang=lang)}"
            f"（{rec.sell_value:,.2f} {display_currency}）"
            f"\n   {t('formatter.reason', lang=lang)}：{t(rec.reason_key, lang=lang, **rec.reason_vars)}"
            f"\n   {t('formatter.priority', lang=lang)}：{priority_label}"
            f"{pl_text}"
        )

    parts.append(
        t(
            "formatter.withdrawal_total",
            lang=lang,
            amount=f"{plan.total_sell_value:,.2f}",
            currency=display_currency,
        )
    )

    if plan.shortfall > 0:
        parts.append(
            t(
                "formatter.withdrawal_shortfall",
                lang=lang,
                amount=f"{plan.shortfall:,.2f}",
                currency=display_currency,
            )
        )

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Smart Money (大師足跡) 格式化
# ---------------------------------------------------------------------------


_HOLDING_ACTION_ICON: dict[str, str] = {
    "NEW_POSITION": "🟢",
    "SOLD_OUT": "🔴",
    "INCREASED": "📈",
    "DECREASED": "📉",
    "UNCHANGED": "⚪",
}


def format_guru_filing_digest(summaries: list[dict], lang: str = "zh-TW") -> str:
    """
    將多位大師的 13F 季報摘要格式化為 Telegram HTML 訊息。

    Args:
        summaries: list of filing summary dicts（來自 filing_service，需包含
                   guru_display_name, report_date, new_positions, sold_out,
                   increased, decreased, top_holdings）
        lang: 語言代碼

    Returns:
        Telegram HTML 格式字串
    """
    if not summaries:
        return t("guru.digest_no_updates", lang=lang)

    report_date = summaries[0].get("report_date", "")
    parts: list[str] = [
        t("guru.filing_digest_title", lang=lang, report_date=report_date),
        "",
    ]

    for summary in summaries:
        name = summary.get("guru_display_name", "")
        new_pos = summary.get("new_positions", 0)
        sold = summary.get("sold_out", 0)
        increased = summary.get("increased", 0)
        decreased = summary.get("decreased", 0)

        parts.append(f"<b>{name}</b>")
        if new_pos or sold or increased or decreased:
            parts.append(
                t(
                    "guru.digest_changes",
                    lang=lang,
                    new=new_pos,
                    sold=sold,
                    inc=increased,
                    dec=decreased,
                )
            )
        else:
            parts.append(t("guru.digest_no_changes", lang=lang))

        # Top 3 holdings for brevity
        for h in summary.get("top_holdings", [])[:3]:
            icon = _HOLDING_ACTION_ICON.get(h.get("action", ""), "⚪")
            ticker = h.get("ticker") or h.get("cusip", "")
            weight = h.get("weight_pct") or 0.0
            parts.append(f"  {icon} {ticker} ({weight:.1f}%)")
        parts.append("")

    parts.append(t("guru.lagging_disclaimer_short", lang=lang))
    return "\n".join(parts)


def format_weekly_digest_html(
    *,
    lang: str,
    title: str,
    portfolio_value_line: str | None,
    health_line: str,
    fear_greed_line: str,
    top_movers_lines: list[str],
    non_normal: list[dict],
    signal_changes: dict[str, int],
    signal_transitions: dict[str, tuple[str, str]] | None = None,
    drift_lines: list[str],
    all_normal_line: str,
) -> str:
    """
    Assemble the full weekly digest Telegram HTML message from pre-built sections.

    All section strings are already translated by the caller; this function is
    responsible only for ordering, grouping, and HTML structure.

    Args:
        lang: language code passed to t() for section header translations
        title: report title line
        portfolio_value_line: portfolio value + WoW line, or None if no data
        health_line: health-score line
        fear_greed_line: fear & greed line
        top_movers_lines: list of individual mover lines (may be empty)
        non_normal: list of dicts with keys ticker, cat_label, signal, duration_days, is_new
        signal_changes: mapping of ticker → change count for the period
        signal_transitions: mapping of ticker → (from_signal, to_signal) for the period
        drift_lines: list of formatted drift lines (may be empty)
        all_normal_line: translated "all positions normal" string

    Returns:
        Telegram HTML formatted string (uses <b> tags for section headers)
    """
    parts: list[str] = [f"<b>{title}</b>", ""]

    # --- Portfolio value ---
    if portfolio_value_line:
        parts.append(portfolio_value_line)
        parts.append("")

    # --- Health + Fear & Greed ---
    parts.append(health_line)
    parts.append(fear_greed_line)
    parts.append("")

    # --- Top movers ---
    if top_movers_lines:
        parts.append(f"<b>{t('notification.top_movers_title', lang=lang)}</b>")
        parts.extend(top_movers_lines)
        parts.append("")

    # --- Active signals (with duration badges) ---
    if non_normal:
        parts.append(f"<b>{t('notification.abnormal_stocks', lang=lang)}</b>")
        for item in non_normal:
            duration_days = item.get("duration_days")
            is_new = item.get("is_new", False)
            if is_new:
                badge = t("notification.signal_new_badge", lang=lang)
            elif duration_days is not None:
                badge = t("notification.signal_duration", lang=lang, days=duration_days)
            else:
                badge = ""
            badge_suffix = f" {badge}" if badge else ""
            parts.append(
                f"  • {item['ticker']}（{item['cat_label']}）→ {item['signal']}{badge_suffix}"
            )
        parts.append("")

    # --- Signal changes (with transition direction) ---
    if signal_changes:
        parts.append(f"<b>{t('notification.signal_changes', lang=lang)}</b>")
        transitions = signal_transitions or {}
        for tk, count in sorted(signal_changes.items(), key=lambda x: -x[1]):
            if tk in transitions:
                from_sig, to_sig = transitions[tk]
                parts.append(
                    t(
                        "notification.signal_change_detail",
                        lang=lang,
                        ticker=tk,
                        from_signal=from_sig,
                        to_signal=to_sig,
                        count=count,
                    )
                )
            else:
                change_label = t("notification.change_label", lang=lang)
                times_label = t("notification.times_label", lang=lang)
                parts.append(f"  • {tk}：{change_label} {count} {times_label}")
        parts.append("")

    # --- Allocation drift ---
    if drift_lines:
        parts.append(f"<b>{t('notification.drift_title', lang=lang)}</b>")
        parts.extend(drift_lines)
        parts.append("")

    # --- All normal (only when no signals and no changes) ---
    if not non_normal and not signal_changes:
        parts.append(all_normal_line)

    # Strip trailing blank lines
    while parts and parts[-1] == "":
        parts.pop()

    return "\n".join(parts)


def format_resonance_alert(
    ticker: str, guru_name: str, action: str, lang: str = "zh-TW"
) -> str:
    """
    格式化單一共鳴警報：大師對使用者關注清單中的股票進行了操作。

    Args:
        ticker: 股票代號
        guru_name: 大師顯示名稱
        action: HoldingAction value（e.g. "NEW_POSITION"）
        lang: 語言代碼

    Returns:
        Telegram HTML 格式字串
    """
    icon = _HOLDING_ACTION_ICON.get(action, "⚪")
    action_label = t(f"guru.action_{action.lower()}", lang=lang)
    return t(
        "guru.resonance_alert",
        lang=lang,
        icon=icon,
        guru_name=guru_name,
        action=action_label,
        ticker=ticker,
    )
