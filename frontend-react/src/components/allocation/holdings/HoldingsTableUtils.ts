import type { HoldingDetail } from "@/api/types/allocation"
import { FINANCE_TEXT } from "@/lib/colors"
import { formatSignedPct } from "@/lib/format"

export type SortDirection = "asc" | "desc"
export type SortKey =
  | "ticker"
  | "account_name"
  | "market_value"
  | "weight_pct"
  | "cost_total"
  | "change_value"
  | "total_gain_value"

export interface GroupedHolding extends HoldingDetail {
  accounts: string[]
  row_key: string
}

export function buildNonCashGroupKey(h: HoldingDetail): string {
  return `${h.ticker}::${h.category}::${h.currency}`
}

export function formatAccountList(accounts: string[]): { shortLabel: string; fullLabel: string } {
  const sortedAccounts = [...accounts].sort((a, b) => a.localeCompare(b))
  const fullLabel = sortedAccounts.join(", ")
  if (sortedAccounts.length <= 2) {
    return { shortLabel: fullLabel, fullLabel }
  }
  return {
    shortLabel: `${sortedAccounts[0]}, ${sortedAccounts[1]} +${sortedAccounts.length - 2}`,
    fullLabel,
  }
}

export function fmtPct(v: number, showSign = true): string {
  return showSign ? formatSignedPct(v, 2) : `${v.toFixed(2)}%`
}

export function getValueClass(v: number | null | undefined): string {
  if (v == null) return FINANCE_TEXT.neutral
  if (v > 0) return FINANCE_TEXT.gain
  if (v < 0) return FINANCE_TEXT.loss
  return FINANCE_TEXT.neutral
}

export function compareNullableNumber(
  a: number | null | undefined,
  b: number | null | undefined,
  direction: SortDirection,
): number {
  const aNull = a == null
  const bNull = b == null
  if (aNull && bNull) return 0
  if (aNull) return 1
  if (bNull) return -1
  const diff = a - b
  return direction === "asc" ? diff : -diff
}

/** Compute FX return % given purchase and current FX rate */
export function computeFxReturn(
  purchaseFx: number | null | undefined,
  currentFx: number | null | undefined,
): number | null {
  if (purchaseFx == null || currentFx == null || purchaseFx === 0) return null
  return (currentFx / purchaseFx - 1) * 100
}

export function roundTo2(value: number): number {
  return Math.round(value * 100) / 100
}
