import { useQuery } from "@tanstack/react-query"
import client from "@/api/client"
import type { components } from "@/api/types/generated"

export type DrawdownPoint = components["schemas"]["DrawdownPointResponse"]
export type RiskMetrics = components["schemas"]["RiskMetricsResponse"]
export type InsightItem = components["schemas"]["InsightResponse"]

export function useDrawdown(start?: string, end?: string, enabled = true) {
  return useQuery<DrawdownPoint[]>({
    queryKey: ["drawdown", start, end],
    queryFn: async () => {
      const { data, error } = await client.GET("/analytics/drawdown", {
        params: { query: { start, end } },
      })
      if (error) throw error
      return (data ?? []) as DrawdownPoint[]
    },
    staleTime: 5 * 60 * 1000,
    enabled,
  })
}

export function useRiskMetrics(start?: string, end?: string, enabled = true) {
  return useQuery<RiskMetrics>({
    queryKey: ["risk-metrics", start, end],
    queryFn: async () => {
      const { data, error } = await client.GET("/analytics/risk-metrics", {
        params: { query: { start, end } },
      })
      if (error) throw error
      return data as RiskMetrics
    },
    staleTime: 5 * 60 * 1000,
    enabled,
  })
}

export function useInsights(displayCurrency = "USD", enabled = true) {
  return useQuery<InsightItem[]>({
    queryKey: ["insights", displayCurrency],
    queryFn: async () => {
      const { data, error } = await client.GET("/analytics/insights", {
        params: { query: { display_currency: displayCurrency } },
      })
      if (error) throw error
      return (data ?? []) as InsightItem[]
    },
    staleTime: 5 * 60 * 1000,
    enabled,
  })
}
