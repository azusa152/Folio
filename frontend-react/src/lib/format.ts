import { MARKET_HOURS } from "@/lib/constants"

const JPY_FORMATTER = new Intl.NumberFormat("ja-JP", {
  maximumFractionDigits: 0,
})

const DEFAULT_FORMATTER = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})
const COMPACT_FORMATTER = new Intl.NumberFormat("en-US", {
  notation: "compact",
  maximumFractionDigits: 1,
})

/**
 * Format a price with currency-appropriate decimals.
 * JPY: no decimals, thousands separator (1,234)
 * TWD: no decimals, thousands separator (1,234)
 * Others: 2 decimals (1,234.56)
 */
export function formatPrice(value: number, currencyCode: string): string {
  if (currencyCode === "JPY" || currencyCode === "TWD") {
    return JPY_FORMATTER.format(value)
  }
  return DEFAULT_FORMATTER.format(value)
}

/**
 * Format money with currency symbol and sensible decimals.
 * JPY/TWD default to 0 decimals, others to 2 decimals.
 */
export function formatCurrency(
  value: number,
  currencyCode: string,
  fractionDigits?: number,
): string {
  const digits =
    fractionDigits != null
      ? fractionDigits
      : currencyCode === "JPY" || currencyCode === "TWD"
        ? 0
        : 2
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: currencyCode,
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value)
}

export function formatQuantity(
  quantity: number,
  opts?: { category?: string; ticker?: string },
): string {
  if (opts?.category === "Crypto") {
    const ticker = opts.ticker ?? ""
    const max = ticker.startsWith("BTC") ? 8 : ticker.startsWith("ETH") ? 6 : 4
    return quantity.toLocaleString(undefined, {
      minimumFractionDigits: 0,
      maximumFractionDigits: max,
    })
  }

  if (opts?.category === "Cash") {
    return quantity.toLocaleString(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
  }

  if (opts?.category === "Bond") {
    return quantity.toLocaleString(undefined, {
      minimumFractionDigits: 0,
      maximumFractionDigits: 4,
    })
  }

  if (opts?.category) {
    return quantity.toLocaleString(undefined, {
      minimumFractionDigits: 0,
      maximumFractionDigits: 4,
    })
  }

  // Preserve non-zero tiny values (e.g. micro-lot crypto imports) so they never
  // appear as misleading 0.00 in generic tables where category is unavailable.
  const roundsToZeroAt2dp = quantity !== 0 && Number(quantity.toFixed(2)) === 0

  return quantity.toLocaleString(
    undefined,
    roundsToZeroAt2dp
      ? {
          minimumFractionDigits: 0,
          maximumFractionDigits: 8,
        }
      : {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        },
  )
}

export function getQuantityUnitKey(
  category?: string,
  ticker?: string,
): { key: string; params: Record<string, string> } {
  if (category === "Cash") {
    return ticker
      ? { key: "common.quantity_unit.currency", params: { ticker } }
      : { key: "common.quantity_unit.units", params: {} }
  }

  if (category === "Crypto") {
    return ticker
      ? { key: "common.quantity_unit.crypto", params: { ticker } }
      : { key: "common.quantity_unit.units", params: {} }
  }

  if (category === "Bond") {
    return { key: "common.quantity_unit.units", params: {} }
  }

  return { key: "common.quantity_unit.shares", params: {} }
}

export function getTransactionQuantityUnitKey(opts: {
  transactionType: string
  category?: string | null
  ticker?: string | null
  currency?: string | null
  isCash?: boolean | null
}): { key: string; params: Record<string, string> } {
  const type = opts.transactionType.toUpperCase()
  const cashFlowTypes = new Set([
    "DEPOSIT",
    "WITHDRAWAL",
    "TRANSFER_IN",
    "TRANSFER_OUT",
    "OPENING_BALANCE",
    "ADJUSTMENT",
    "DIVIDEND",
  ])

  if (cashFlowTypes.has(type) || opts.isCash === true) {
    return {
      key: "common.quantity_unit.currency",
      params: { ticker: opts.currency || "USD" },
    }
  }

  return getQuantityUnitKey(opts.category ?? undefined, opts.ticker ?? undefined)
}

export function formatMarketCap(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—"
  return COMPACT_FORMATTER.format(value)
}

export function formatRatio(
  value: number | null | undefined,
  decimals = 2,
): string {
  if (value == null || Number.isNaN(value)) return "—"
  return value.toFixed(decimals)
}

export function formatPercent(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—"
  const normalized = Math.abs(value) <= 1 ? value * 100 : value
  const sign = normalized > 0 ? "+" : ""
  return `${sign}${normalized.toFixed(1)}%`
}

function toMinutes(hhmm: string): number {
  const [h, m] = hhmm.split(":").map(Number)
  return h * 60 + m
}

export function isMarketOpen(marketKey: string): boolean {
  const hours = MARKET_HOURS[marketKey]
  if (!hours) return false

  const now = new Date()
  const formatter = new Intl.DateTimeFormat("en-US", {
    timeZone: hours.tz,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    weekday: "short",
  })
  const parts = formatter.formatToParts(now)
  const weekday = parts.find((p) => p.type === "weekday")?.value
  if (weekday === "Sat" || weekday === "Sun") return false

  const hhmm = parts
    .filter((p) => p.type === "hour" || p.type === "minute")
    .map((p) => p.value)
    .join(":")
  const currentMinutes = toMinutes(hhmm)
  const openMin = toMinutes(hours.open)
  const closeMin = toMinutes(hours.close)

  if (currentMinutes < openMin || currentMinutes >= closeMin) return false
  if (hours.lunch) {
    const [lunchStart, lunchEnd] = hours.lunch
    if (currentMinutes >= toMinutes(lunchStart) && currentMinutes < toMinutes(lunchEnd)) return false
  }
  return true
}
