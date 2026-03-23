/**
 * Runtime shape guards for hand-written types that are not backed by a Pydantic
 * response_model.  `fromApiData<T>` only asserts non-null; these guards add a
 * minimal structural check so silent shape regressions surface at runtime.
 */
import type { EnrichedStock } from "@/api/types/dashboard"
import type { RadarEnrichedStock } from "@/api/types/radar"
import type { PricePoint, MoatAnalysis } from "@/api/hooks/useRadar"

export function assertEnrichedStocks(data: unknown): EnrichedStock[] {
  if (!Array.isArray(data)) throw new Error("assertEnrichedStocks: expected array")
  if (data.length > 0) {
    const first = data[0] as Record<string, unknown>
    if (typeof first.ticker !== "string" || typeof first.current_price !== "number")
      throw new Error(
        "assertEnrichedStocks: unexpected element shape (missing ticker or current_price)",
      )
  }
  return data as EnrichedStock[]
}

export function assertRadarEnrichedStocks(data: unknown): RadarEnrichedStock[] {
  if (!Array.isArray(data)) throw new Error("assertRadarEnrichedStocks: expected array")
  if (data.length > 0) {
    const first = data[0] as Record<string, unknown>
    if (typeof first.ticker !== "string" || typeof first.category !== "string")
      throw new Error(
        "assertRadarEnrichedStocks: unexpected element shape (missing ticker or category)",
      )
  }
  return data as RadarEnrichedStock[]
}

export function assertPricePoints(data: unknown): PricePoint[] {
  if (!Array.isArray(data)) throw new Error("assertPricePoints: expected array")
  if (data.length > 0 && typeof (data[0] as Record<string, unknown>).close !== "number")
    throw new Error("assertPricePoints: unexpected shape (missing close)")
  return data as PricePoint[]
}

export function assertMoatAnalysis(data: unknown): MoatAnalysis {
  if (typeof data !== "object" || data === null || !("ticker" in data) || !("moat" in data))
    throw new Error("assertMoatAnalysis: unexpected shape")
  return data as MoatAnalysis
}
