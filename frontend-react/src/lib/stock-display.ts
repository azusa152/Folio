/**
 * Stock display utilities.
 *
 * Provides a consistent "name + ticker" display pattern matching the Radar page UX:
 *   - Primary: company or fund name (human-readable)
 *   - Secondary: ticker symbol + optional market label (muted, smaller)
 *
 * Non-expert investors recognize company names, not ticker codes. Mutual fund
 * tickers (e.g. "01312179") are especially opaque without a display name.
 */

/** Enriched stock data needed to resolve a display name. */
export interface StockNameInfo {
  ticker: string
  name?: string | null
  fund_name?: string | null
  category?: string
  exchange?: string | null
}

/**
 * Resolve the primary display name for a stock.
 *
 * Returns the best available human-readable name, or null if none is found.
 * Rules (matching Radar page StockCardHeader):
 *  - Mutual funds → fund_name, then name, then null
 *  - Everything else → name, then null
 */
export function resolveDisplayName(info: StockNameInfo): string | null {
  if (info.category === "Mutual_Fund") {
    return info.fund_name?.trim() || info.name?.trim() || null
  }
  return info.name?.trim() || null
}

/**
 * Return the display name when available, otherwise null.
 * Accepts a plain `name` field as returned from HoldingDetail / StressTestHoldingBreakdown.
 */
export function getDisplayName(name: string | null | undefined): string | null {
  return name?.trim() || null
}
