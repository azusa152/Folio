import { describe, it, expect, beforeEach, afterEach, vi } from "vitest"
import {
  formatCurrency,
  formatMarketCap,
  formatPercent,
  formatPrice,
  getQuantityUnitKey,
  getTransactionQuantityUnitKey,
  formatQuantity,
  formatRatio,
  isMarketOpen,
} from "../format"

describe("formatPrice", () => {
  it("formats JPY as integer with thousands separator", () => {
    expect(formatPrice(1234.56, "JPY")).toBe("1,235")
  })

  it("formats TWD as integer with thousands separator", () => {
    expect(formatPrice(1234.56, "TWD")).toBe("1,235")
  })

  it("formats USD with 2 decimal places", () => {
    expect(formatPrice(1234.5, "USD")).toBe("1,234.50")
  })

  it("formats HKD with 2 decimal places", () => {
    expect(formatPrice(1234.56, "HKD")).toBe("1,234.56")
  })

  it("rounds JPY 0.5 up to 1", () => {
    expect(formatPrice(0.5, "JPY")).toBe("1")
  })

  it("formats large JPY value with thousands separator", () => {
    expect(formatPrice(12345678, "JPY")).toBe("12,345,678")
  })
})

describe("isMarketOpen", () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it("returns false for an unknown market key", () => {
    vi.setSystemTime(new Date("2025-02-25T14:00:00Z")) // Tuesday UTC
    expect(isMarketOpen("UNKNOWN")).toBe(false)
  })

  it("returns false on a Saturday (US market)", () => {
    // 2025-02-22 is a Saturday; 15:00 UTC = 10:00 EST (would be inside US hours on a weekday)
    vi.setSystemTime(new Date("2025-02-22T15:00:00Z"))
    expect(isMarketOpen("US")).toBe(false)
  })

  it("returns false on a Sunday (US market)", () => {
    // 2025-02-23 is a Sunday
    vi.setSystemTime(new Date("2025-02-23T15:00:00Z"))
    expect(isMarketOpen("US")).toBe(false)
  })

  it("returns false before US market opens (09:29 EST on a Tuesday)", () => {
    // 2025-02-25 (Tuesday) 14:29 UTC = 09:29 EST
    vi.setSystemTime(new Date("2025-02-25T14:29:00Z"))
    expect(isMarketOpen("US")).toBe(false)
  })

  it("returns true during US market hours (10:00 EST on a Tuesday)", () => {
    // 2025-02-25 (Tuesday) 15:00 UTC = 10:00 EST
    vi.setSystemTime(new Date("2025-02-25T15:00:00Z"))
    expect(isMarketOpen("US")).toBe(true)
  })

  it("returns false after US market closes (16:01 EST on a Tuesday)", () => {
    // 2025-02-25 (Tuesday) 21:01 UTC = 16:01 EST
    vi.setSystemTime(new Date("2025-02-25T21:01:00Z"))
    expect(isMarketOpen("US")).toBe(false)
  })

  it("returns false during JP lunch break (12:00 JST on a Tuesday)", () => {
    // JP lunch: 11:30–12:30 JST. 2025-02-25 (Tuesday) 03:00 UTC = 12:00 JST
    vi.setSystemTime(new Date("2025-02-25T03:00:00Z"))
    expect(isMarketOpen("JP")).toBe(false)
  })

  it("returns true during JP morning session (10:00 JST on a Tuesday)", () => {
    // 2025-02-25 (Tuesday) 01:00 UTC = 10:00 JST
    vi.setSystemTime(new Date("2025-02-25T01:00:00Z"))
    expect(isMarketOpen("JP")).toBe(true)
  })

  it("returns true during JP afternoon session (13:00 JST on a Tuesday)", () => {
    // 2025-02-25 (Tuesday) 04:00 UTC = 13:00 JST
    vi.setSystemTime(new Date("2025-02-25T04:00:00Z"))
    expect(isMarketOpen("JP")).toBe(true)
  })

  it("returns false during HK lunch break (12:30 HKT on a Tuesday)", () => {
    // HK lunch: 12:00–13:00 HKT. 2025-02-25 (Tuesday) 04:30 UTC = 12:30 HKT
    vi.setSystemTime(new Date("2025-02-25T04:30:00Z"))
    expect(isMarketOpen("HK")).toBe(false)
  })

  it("returns true during HK afternoon session (14:00 HKT on a Tuesday)", () => {
    // 2025-02-25 (Tuesday) 06:00 UTC = 14:00 HKT
    vi.setSystemTime(new Date("2025-02-25T06:00:00Z"))
    expect(isMarketOpen("HK")).toBe(true)
  })

  it("returns true during TW market hours (10:00 CST on a Tuesday)", () => {
    // TW: 09:00–13:30 CST. 2025-02-25 (Tuesday) 02:00 UTC = 10:00 CST
    vi.setSystemTime(new Date("2025-02-25T02:00:00Z"))
    expect(isMarketOpen("TW")).toBe(true)
  })

  it("returns false after TW market closes (13:31 CST on a Tuesday)", () => {
    // 2025-02-25 (Tuesday) 05:31 UTC = 13:31 CST
    vi.setSystemTime(new Date("2025-02-25T05:31:00Z"))
    expect(isMarketOpen("TW")).toBe(false)
  })
})

describe("formatCurrency", () => {
  it("formats USD with dollar sign and 2 decimals", () => {
    expect(formatCurrency(1234.56, "USD")).toBe("$1,234.56")
  })

  it("formats JPY with yen sign and no decimals", () => {
    expect(formatCurrency(1234.56, "JPY")).toBe("¥1,235")
  })

  it("formats TWD with no decimals", () => {
    expect(formatCurrency(5000, "TWD")).toBe("NT$5,000")
  })

  it("respects explicit fractionDigits override", () => {
    expect(formatCurrency(1234.567, "USD", 0)).toBe("$1,235")
  })

  it("formats zero correctly", () => {
    expect(formatCurrency(0, "USD")).toBe("$0.00")
  })

  it("formats EUR with symbol", () => {
    const result = formatCurrency(1234.56, "EUR")
    expect(result).toContain("1,234.56")
  })
})

describe("fundamental format helpers", () => {
  it("formats market cap as compact notation", () => {
    expect(formatMarketCap(1234567890)).toBe("1.2B")
  })

  it("formats ratio with default decimals", () => {
    expect(formatRatio(12.3456)).toBe("12.35")
  })

  it("formats percent from decimal value", () => {
    expect(formatPercent(0.1234)).toBe("+12.3%")
  })
})

describe("getQuantityUnitKey", () => {
  it("returns shares unit for equity categories", () => {
    expect(getQuantityUnitKey("Growth", "AAPL")).toEqual({
      key: "common.quantity_unit.shares",
      params: {},
    })
  })

  it("returns currency unit for cash with ticker", () => {
    expect(getQuantityUnitKey("Cash", "USD")).toEqual({
      key: "common.quantity_unit.currency",
      params: { ticker: "USD" },
    })
  })

  it("returns crypto unit for crypto with ticker", () => {
    expect(getQuantityUnitKey("Crypto", "BTC")).toEqual({
      key: "common.quantity_unit.crypto",
      params: { ticker: "BTC" },
    })
  })

  it("returns units for bonds", () => {
    expect(getQuantityUnitKey("Bond", "TLT")).toEqual({
      key: "common.quantity_unit.units",
      params: {},
    })
  })

  it("falls back to units when ticker is missing for cash and crypto", () => {
    expect(getQuantityUnitKey("Cash")).toEqual({
      key: "common.quantity_unit.units",
      params: {},
    })
    expect(getQuantityUnitKey("Crypto")).toEqual({
      key: "common.quantity_unit.units",
      params: {},
    })
  })
})

describe("formatQuantity", () => {
  it("keeps up to 4 decimals for equity categories", () => {
    expect(formatQuantity(239.8767, { category: "Growth", ticker: "VTI" })).toBe("239.8767")
    expect(formatQuantity(3, { category: "Growth", ticker: "AAPL" })).toBe("3")
  })

  it("uses 2 decimals for cash quantities", () => {
    expect(formatQuantity(1428.3, { category: "Cash", ticker: "USD" })).toBe("1,428.30")
  })
})

describe("getTransactionQuantityUnitKey", () => {
  it("uses currency unit for dividend", () => {
    expect(
      getTransactionQuantityUnitKey({
        transactionType: "DIVIDEND",
        category: "Growth",
        ticker: "AAPL",
        currency: "USD",
      }),
    ).toEqual({
      key: "common.quantity_unit.currency",
      params: { ticker: "USD" },
    })
  })

  it("uses category-aware unit for buy/sell", () => {
    expect(
      getTransactionQuantityUnitKey({
        transactionType: "BUY",
        category: "Crypto",
        ticker: "BTC",
        currency: "USD",
      }),
    ).toEqual({
      key: "common.quantity_unit.crypto",
      params: { ticker: "BTC" },
    })
  })
})
