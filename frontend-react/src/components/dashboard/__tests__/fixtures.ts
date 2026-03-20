import type { AccountSummaryItem } from "@/api/types/account"
import type { RebalanceResponse } from "@/api/types/dashboard"

/**
 * Typed factory for AccountSummaryItem test data.
 * `account` and `cash_balances` accept partial shapes; the single `as` cast is
 * justified: the API schema has many required sub-fields that are irrelevant to
 * the test assertions here.
 */
export function makeAccountSummaryItem(
  overrides: {
    account?: { id?: number; name?: string; broker?: string; account_type?: string } | null
    holdings_count?: number
    tickers?: string[]
    cash_balances?: Array<{ currency: string; balance: number }>
  } = {},
): AccountSummaryItem {
  return {
    holdings_count: 0,
    tickers: [],
    ...overrides,
  } as AccountSummaryItem
}

/**
 * Typed factory for RebalanceResponse test data.
 * `holdings_detail` accepts partial holding shapes; the single `as` cast is
 * justified: only `holdings_detail` and `display_currency` are exercised by
 * most tests, but the type has ~15 required fields.
 */
export function makeRebalanceResponse(
  overrides: {
    holdings_detail?: Array<Record<string, unknown>>
    display_currency?: string
    total_value?: number
  } = {},
): RebalanceResponse {
  return {
    total_value: 0,
    display_currency: "USD",
    categories: {},
    advice: [],
    holdings_detail: [],
    ...overrides,
  } as RebalanceResponse
}
