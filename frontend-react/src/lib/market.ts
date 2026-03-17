/**
 * Shared market inference utilities.
 *
 * Japanese mutual fund codes are 8-character alphanumeric strings (e.g.
 * "01312179", "0131310B") without the `.T` suffix used by TSE equities.
 */

const JP_MUTUAL_FUND_PATTERN = /^[0-9A-Z]{8}$/i

function isJpMutualFund(ticker: string, category?: string): boolean {
  return category === "Mutual_Fund" && JP_MUTUAL_FUND_PATTERN.test(ticker)
}

export function inferMarket(ticker: string, category?: string): string {
  if (ticker.endsWith(".T")) return "JP"
  if (ticker.endsWith(".TW")) return "TW"
  if (ticker.endsWith(".HK")) return "HK"
  if (isJpMutualFund(ticker, category)) return "JP"
  return "US"
}

export function inferMarketLabel(ticker: string, category?: string): string {
  const m = inferMarket(ticker, category)
  if (m === "JP") return "🇯🇵 JP"
  if (m === "TW") return "🇹🇼 TW"
  if (m === "HK") return "🇭🇰 HK"
  return "🇺🇸 US"
}

export function inferCurrency(ticker: string, category?: string): { symbol: string; code: string } {
  const m = inferMarket(ticker, category)
  if (m === "JP") return { symbol: "¥", code: "JPY" }
  if (m === "TW") return { symbol: "NT$", code: "TWD" }
  if (m === "HK") return { symbol: "HK$", code: "HKD" }
  return { symbol: "$", code: "USD" }
}

export function inferCurrencySymbol(ticker: string, category?: string): string {
  return inferCurrency(ticker, category).symbol
}
