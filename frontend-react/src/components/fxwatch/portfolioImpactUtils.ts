import { FINANCE_BADGE, FINANCE_TEXT } from "@/lib/colors"

export interface BreakdownItem {
  name: string
  value: number
}

export interface AttributionRow {
  pair: string
  holdingsValue: number
  rateChangePct: number
  impactHomeValue: number
  cashImpactHomeValue: number
  investmentImpactHomeValue: number
}

export const ALERT_TEXT_CLASSES: Record<string, string> = {
  daily_spike: FINANCE_TEXT.loss,
  short_term_swing: FINANCE_TEXT.warning,
  long_term_trend: "text-blue-600 dark:text-blue-400",
}

export const RISK_BADGE_CLASSES: Record<string, string> = {
  low: FINANCE_BADGE.gain,
  medium: FINANCE_BADGE.warning,
  high: FINANCE_BADGE.loss,
}

export function formatAmount(value: number, currency: string, signed = true): string {
  const sign = value >= 0 ? "+" : "-"
  const absValue = Math.abs(value)
  const amount = new Intl.NumberFormat(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(absValue)
  return signed ? `${sign}${amount} ${currency}` : `${amount} ${currency}`
}

export function riskLabelKey(riskLevel: string): string {
  if (riskLevel === "low") return "fx_watch.overview.risk_low"
  if (riskLevel === "high") return "fx_watch.overview.risk_high"
  return "fx_watch.overview.risk_medium"
}

export function periodToLabel(period: string, t: (key: string) => string): string {
  if (period === "5d") return t("fx_watch.overview.period_5d")
  if (period === "1mo") return t("fx_watch.overview.period_1mo")
  if (period === "3mo") return t("fx_watch.overview.period_3mo")
  return t("fx_watch.overview.period_recent")
}
