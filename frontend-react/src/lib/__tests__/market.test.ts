import { describe, it, expect } from "vitest";
import {
  inferMarket,
  inferMarketLabel,
  inferCurrency,
  inferCurrencySymbol,
} from "../market";

describe("inferMarket", () => {
  it("returns JP for .T suffix", () => {
    expect(inferMarket("7203.T")).toBe("JP");
  });

  it("returns TW for .TW suffix", () => {
    expect(inferMarket("2330.TW")).toBe("TW");
  });

  it("returns HK for .HK suffix", () => {
    expect(inferMarket("0700.HK")).toBe("HK");
  });

  it("returns US for plain ticker", () => {
    expect(inferMarket("AAPL")).toBe("US");
  });

  it("returns JP for 8-char alphanumeric Mutual_Fund ticker", () => {
    expect(inferMarket("01312179", "Mutual_Fund")).toBe("JP");
  });

  it("returns JP for 8-char ticker with trailing letter and Mutual_Fund category", () => {
    expect(inferMarket("0131217A", "Mutual_Fund")).toBe("JP");
  });

  it("returns US for 8-char ticker without Mutual_Fund category (no false positive)", () => {
    expect(inferMarket("01312179", "Growth")).toBe("US");
    expect(inferMarket("01312179")).toBe("US");
  });

  it("returns US for non-8-char Mutual_Fund ticker", () => {
    expect(inferMarket("VFIAX", "Mutual_Fund")).toBe("US");
  });
});

describe("inferMarketLabel", () => {
  it("returns flag + code for each market", () => {
    expect(inferMarketLabel("7203.T")).toBe("🇯🇵 JP");
    expect(inferMarketLabel("2330.TW")).toBe("🇹🇼 TW");
    expect(inferMarketLabel("0700.HK")).toBe("🇭🇰 HK");
    expect(inferMarketLabel("AAPL")).toBe("🇺🇸 US");
  });

  it("returns JP label for Japanese mutual fund", () => {
    expect(inferMarketLabel("01312179", "Mutual_Fund")).toBe("🇯🇵 JP");
  });
});

describe("inferCurrency", () => {
  it("returns JPY for JP market", () => {
    expect(inferCurrency("7203.T")).toEqual({ symbol: "¥", code: "JPY" });
  });

  it("returns TWD for TW market", () => {
    expect(inferCurrency("2330.TW")).toEqual({ symbol: "NT$", code: "TWD" });
  });

  it("returns HKD for HK market", () => {
    expect(inferCurrency("0700.HK")).toEqual({ symbol: "HK$", code: "HKD" });
  });

  it("returns USD for US market", () => {
    expect(inferCurrency("AAPL")).toEqual({ symbol: "$", code: "USD" });
  });

  it("returns JPY for Japanese mutual fund", () => {
    expect(inferCurrency("01312179", "Mutual_Fund")).toEqual({ symbol: "¥", code: "JPY" });
  });
});

describe("inferCurrencySymbol", () => {
  it("returns symbol string only", () => {
    expect(inferCurrencySymbol("AAPL")).toBe("$");
    expect(inferCurrencySymbol("7203.T")).toBe("¥");
    expect(inferCurrencySymbol("01312179", "Mutual_Fund")).toBe("¥");
  });
});
