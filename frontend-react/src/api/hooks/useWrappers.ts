import { useQuery } from "@tanstack/react-query"
import client from "@/api/client"
import type {
  AllQuotasResponse,
  DeTaxResponse,
  EligibilityCheckResponse,
  EligibleAssetsResponse,
  RoutingSuggestResponse,
  RestorationForecastResponse,
} from "@/api/types/wrapper"

export function useWrapperQuota(enabled = true) {
  return useQuery<AllQuotasResponse>({
    queryKey: ["wrapper-quota"],
    queryFn: async () => {
      const { data, error } = await client.GET("/wrappers/quota")
      if (error) throw error
      return data as AllQuotasResponse
    },
    enabled,
    staleTime: 30 * 1000,
  })
}

export function useRestorationForecast(enabled = true) {
  return useQuery<RestorationForecastResponse>({
    queryKey: ["wrapper-restoration"],
    queryFn: async () => {
      const { data, error } = await client.GET("/wrappers/restoration-forecast")
      if (error) throw error
      return data as RestorationForecastResponse
    },
    enabled,
    staleTime: 30 * 1000,
  })
}

export function useWrapperEligibility(
  wrapper: string | null | undefined,
  ticker: string | null | undefined,
  broker?: string,
  enabled = true,
) {
  const normalizedWrapper = (wrapper ?? "").trim().toLowerCase()
  const normalizedTicker = (ticker ?? "").trim().toUpperCase()
  return useQuery<EligibilityCheckResponse>({
    queryKey: ["wrapper-eligibility", normalizedWrapper, normalizedTicker, broker ?? ""],
    queryFn: async () => {
      const { data, error } = await client.GET("/wrappers/{wrapper}/check-eligibility", {
        params: {
          path: { wrapper: normalizedWrapper },
          query: {
            ticker: normalizedTicker,
            broker: broker || undefined,
          },
        },
      })
      if (error) throw error
      return data as EligibilityCheckResponse
    },
    enabled: enabled && !!normalizedWrapper && !!normalizedTicker,
    staleTime: 30 * 1000,
  })
}

export function useEligibleAssets(
  wrapper: string | null | undefined,
  options?: {
    broker?: string
    search?: string
    limit?: number
    enabled?: boolean
  },
) {
  const normalizedWrapper = (wrapper ?? "").trim().toLowerCase()
  const normalizedSearch = (options?.search ?? "").trim()
  const limit = options?.limit ?? 50
  return useQuery<EligibleAssetsResponse>({
    queryKey: [
      "wrapper-eligible-assets",
      normalizedWrapper,
      options?.broker ?? "",
      normalizedSearch,
      limit,
    ],
    queryFn: async () => {
      const { data, error } = await client.GET("/wrappers/{wrapper}/eligible-assets", {
        params: {
          path: { wrapper: normalizedWrapper },
          query: {
            broker: options?.broker || undefined,
            search: normalizedSearch || undefined,
            limit,
          },
        },
      })
      if (error) throw error
      return data as EligibleAssetsResponse
    },
    enabled: (options?.enabled ?? true) && !!normalizedWrapper,
    staleTime: 30 * 1000,
  })
}

export function useSuggestRouting(
  ticker: string | null | undefined,
  totalAmount: number | null | undefined,
  enabled = true,
) {
  const normalizedTicker = (ticker ?? "").trim().toUpperCase()
  const normalizedAmount =
    typeof totalAmount === "number" && Number.isFinite(totalAmount)
      ? totalAmount
      : 0
  return useQuery<RoutingSuggestResponse>({
    queryKey: ["wrapper-suggest-routing", normalizedTicker, normalizedAmount],
    queryFn: async () => {
      const { data, error } = await client.POST("/wrappers/suggest-routing", {
        body: {
          ticker: normalizedTicker,
          total_amount: normalizedAmount,
        },
      })
      if (error) throw error
      return data as RoutingSuggestResponse
    },
    enabled: enabled && !!normalizedTicker && normalizedAmount > 0,
    staleTime: 15 * 1000,
  })
}

export function useDeTaxSuggestions(enabled = true) {
  return useQuery<DeTaxResponse>({
    queryKey: ["detax"],
    queryFn: async () => {
      const { data, error } = await client.GET("/wrappers/detax")
      if (error) throw error
      return data as DeTaxResponse
    },
    enabled,
    staleTime: 30 * 1000,
  })
}
