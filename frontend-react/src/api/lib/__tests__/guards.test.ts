import { describe, it, expect } from "vitest"
import {
  assertEnrichedStocks,
  assertRadarEnrichedStocks,
  assertPricePoints,
  assertMoatAnalysis,
} from "../guards"

describe("assertEnrichedStocks", () => {
  it("accepts an empty array", () => {
    expect(assertEnrichedStocks([])).toEqual([])
  })

  it("accepts an array with valid element shape", () => {
    const input = [{ ticker: "AAPL", current_price: 150 }]
    expect(assertEnrichedStocks(input)).toBe(input)
  })

  it("throws for non-array input", () => {
    expect(() => assertEnrichedStocks(null)).toThrow("expected array")
    expect(() => assertEnrichedStocks({})).toThrow("expected array")
    expect(() => assertEnrichedStocks("AAPL")).toThrow("expected array")
  })

  it("throws when first element lacks ticker", () => {
    expect(() => assertEnrichedStocks([{ current_price: 100 }])).toThrow("unexpected element shape")
  })

  it("throws when first element has non-number current_price", () => {
    expect(() => assertEnrichedStocks([{ ticker: "AAPL", current_price: "150" }])).toThrow("unexpected element shape")
  })

  it("does not inspect beyond first element", () => {
    const input = [{ ticker: "AAPL", current_price: 150 }, { invalid: true }]
    expect(() => assertEnrichedStocks(input)).not.toThrow()
  })
})

describe("assertRadarEnrichedStocks", () => {
  it("accepts an empty array", () => {
    expect(assertRadarEnrichedStocks([])).toEqual([])
  })

  it("accepts an array with valid element shape", () => {
    const input = [{ ticker: "AAPL", category: "Growth" }]
    expect(assertRadarEnrichedStocks(input)).toBe(input)
  })

  it("throws for non-array input", () => {
    expect(() => assertRadarEnrichedStocks(null)).toThrow("expected array")
  })

  it("throws when first element lacks ticker", () => {
    expect(() => assertRadarEnrichedStocks([{ category: "Growth" }])).toThrow("unexpected element shape")
  })

  it("throws when first element lacks category", () => {
    expect(() => assertRadarEnrichedStocks([{ ticker: "AAPL" }])).toThrow("unexpected element shape")
  })
})

describe("assertPricePoints", () => {
  it("accepts an empty array", () => {
    expect(assertPricePoints([])).toEqual([])
  })

  it("accepts valid price point data", () => {
    const input = [{ date: "2024-01-01", close: 150.0 }]
    expect(assertPricePoints(input)).toBe(input)
  })

  it("throws for non-array input", () => {
    expect(() => assertPricePoints(42)).toThrow("expected array")
  })

  it("throws when close is not a number", () => {
    expect(() => assertPricePoints([{ date: "2024-01-01", close: "150" }])).toThrow("unexpected shape")
  })
})

describe("assertMoatAnalysis", () => {
  it("accepts a valid MoatAnalysis shape", () => {
    const input = { ticker: "AAPL", moat: "wide" }
    expect(assertMoatAnalysis(input)).toBe(input)
  })

  it("throws for null", () => {
    expect(() => assertMoatAnalysis(null)).toThrow("unexpected shape")
  })

  it("throws for non-object", () => {
    expect(() => assertMoatAnalysis("string")).toThrow("unexpected shape")
    expect(() => assertMoatAnalysis(42)).toThrow("unexpected shape")
  })

  it("throws when ticker is missing", () => {
    expect(() => assertMoatAnalysis({ moat: "wide" })).toThrow("unexpected shape")
  })

  it("throws when moat is missing", () => {
    expect(() => assertMoatAnalysis({ ticker: "AAPL" })).toThrow("unexpected shape")
  })
})
