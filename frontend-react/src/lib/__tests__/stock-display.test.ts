import { describe, it, expect } from "vitest"
import { resolveDisplayName, getDisplayName } from "../stock-display"

describe("resolveDisplayName", () => {
  it("returns company name for equities when name is available", () => {
    expect(resolveDisplayName({ ticker: "AAPL", name: "Apple Inc.", category: "Moat" })).toBe(
      "Apple Inc.",
    )
  })

  it("returns fund_name for mutual funds when fund_name is present", () => {
    expect(
      resolveDisplayName({
        ticker: "01312179",
        name: "Some raw name",
        fund_name: "eMAXIS Slim S&P500",
        category: "Mutual_Fund",
      }),
    ).toBe("eMAXIS Slim S&P500")
  })

  it("falls back to name when fund_name is absent for mutual fund", () => {
    expect(
      resolveDisplayName({
        ticker: "01312179",
        name: "Fallback Name",
        fund_name: null,
        category: "Mutual_Fund",
      }),
    ).toBe("Fallback Name")
  })

  it("returns null when no name is available", () => {
    expect(resolveDisplayName({ ticker: "AAPL", name: null, category: "Moat" })).toBeNull()
  })

  it("returns null when name is undefined", () => {
    expect(resolveDisplayName({ ticker: "AAPL", category: "Growth" })).toBeNull()
  })

  it("returns null when name is whitespace-only", () => {
    expect(resolveDisplayName({ ticker: "AAPL", name: "   ", category: "Moat" })).toBeNull()
  })

  it("returns null when fund_name is whitespace-only for mutual fund", () => {
    expect(
      resolveDisplayName({
        ticker: "01312179",
        name: null,
        fund_name: "   ",
        category: "Mutual_Fund",
      }),
    ).toBeNull()
  })
})

describe("getDisplayName", () => {
  it("returns name when non-empty", () => {
    expect(getDisplayName("Apple Inc.")).toBe("Apple Inc.")
  })

  it("returns null when name is null", () => {
    expect(getDisplayName(null)).toBeNull()
  })

  it("returns null when name is undefined", () => {
    expect(getDisplayName(undefined)).toBeNull()
  })

  it("returns null when name is empty string", () => {
    expect(getDisplayName("")).toBeNull()
  })

  it("returns null when name is whitespace-only", () => {
    expect(getDisplayName("   ")).toBeNull()
  })
})
