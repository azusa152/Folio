/**
 * Shared market inference utilities.
 *
 * Japanese mutual fund codes are 8-character alphanumeric strings (e.g.
 * "01312179", "0131310B") without the `.T` suffix used by TSE equities.
 */

const JP_MUTUAL_FUND_PATTERN = /^[0-9A-Z]{8}$/i
const EXCHANGE_LABEL_MAP: Record<string, string> = {
  NMS: "NASDAQ",
  NAS: "NASDAQ",
  NASDAQ: "NASDAQ",
  NGM: "NASDAQ Global Market",
  NCM: "NASDAQ Capital Market",
  BATS: "Cboe BZX",
  PCX: "NYSE Arca",
  NYQ: "NYSE",
  NYSE: "NYSE",
  ASE: "NYSE American",
  JPX: "TSE",
  TSE: "TSE",
  OSA: "OSE",
  TWO: "TPEx",
  TAI: "TWSE",
  TPE: "TPEx",
  HKG: "HKEX",
  HKE: "HKEX",
}

function isJpMutualFund(ticker: string, category?: string): boolean {
  return category === "Mutual_Fund" && JP_MUTUAL_FUND_PATTERN.test(ticker)
}

export function inferMarket(ticker: string, category?: string): string {
  if (ticker.endsWith(".T")) return "JP"
  if (ticker.endsWith(".TW")) return "TW"
  if (ticker.endsWith(".TWO")) return "TW"
  if (ticker.endsWith(".HK")) return "HK"
  if (isJpMutualFund(ticker, category)) return "JP"
  return "US"
}

export function inferMarketLabel(
  ticker: string,
  category?: string,
  exchange?: string | null,
): string {
  const market = inferMarket(ticker, category)
  const exchangeCode = exchange?.trim().toUpperCase()
  const exchangeLabel = exchangeCode ? EXCHANGE_LABEL_MAP[exchangeCode] : undefined
  if (exchangeLabel) {
    if (market === "JP") return `🇯🇵 ${exchangeLabel}`
    if (market === "TW") return `🇹🇼 ${exchangeLabel}`
    if (market === "HK") return `🇭🇰 ${exchangeLabel}`
    return `🇺🇸 ${exchangeLabel}`
  }
  if (market === "JP") return "🇯🇵 JP"
  if (market === "TW") return "🇹🇼 TW"
  if (market === "HK") return "🇭🇰 HK"
  return "🇺🇸 US"
}

export function inferCurrency(ticker: string, category?: string): { symbol: string; code: string } {
  const market = inferMarket(ticker, category)
  if (market === "JP") return { symbol: "¥", code: "JPY" }
  if (market === "TW") return { symbol: "NT$", code: "TWD" }
  if (market === "HK") return { symbol: "HK$", code: "HKD" }
  return { symbol: "$", code: "USD" }
}

export function inferCurrencySymbol(ticker: string, category?: string): string {
  return inferCurrency(ticker, category).symbol
}
