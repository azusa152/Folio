import type { RadarEnrichedStock, RadarStock } from "@/api/types/radar"

/**
 * Typed factory for RadarEnrichedStock test data.
 * Only `ticker` is required; all other fields are optional in the type.
 * The single `as` cast handles string literals for `computed_signal` /
 * `last_scan_signal` that don't match the `ScanSignal` union exactly.
 */
export function makeRadarEnrichedStock(
  overrides: Partial<RadarEnrichedStock> & Record<string, unknown> = {},
): RadarEnrichedStock {
  return { ticker: "TEST", ...overrides } as RadarEnrichedStock
}

/**
 * Typed factory for RadarStock (= StockResponse) test data.
 * The single `as` cast handles string-literal `category` / `last_scan_signal`
 * values that don't narrow to the generated enum types without a cast.
 */
export function makeRadarStock(
  overrides: Partial<RadarStock> & Record<string, unknown> = {},
): RadarStock {
  return {
    ticker: "TEST",
    category: "Growth",
    current_thesis: null,
    current_tags: [],
    display_order: 0,
    last_scan_signal: null,
    is_active: true,
    is_etf: false,
    ...overrides,
  } as RadarStock
}
