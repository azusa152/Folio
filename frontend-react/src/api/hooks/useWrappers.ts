import { useQuery } from "@tanstack/react-query"
import client from "@/api/client"
import type { AllQuotasResponse, RestorationForecastResponse } from "@/api/types/wrapper"

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
