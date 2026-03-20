import { keepPreviousData, useQuery } from "@tanstack/react-query"
import client from "@/api/client"
import { fromApiData } from "@/api/lib/fromApi"
import { assertEnrichedStocks } from "@/api/lib/guards"
import type {
  Stock,
  RebalanceResponse,
  FearGreedResponse,
  Snapshot,
  TwrResponse,
  GreatMindsResponse,
  LastScanResponse,
  InsightResponse,
  Holding,
  ProfileResponse,
  SignalActivityItem,
} from "@/api/types/dashboard"

export function useStocks() {
  return useQuery({
    queryKey: ["stocks"],
    queryFn: async () => {
      const { data, error } = await client.GET("/stocks")
      if (error) throw error
      return fromApiData<Stock[]>(data)
    },
    staleTime: 5 * 60 * 1000,
    placeholderData: keepPreviousData,
  })
}

export function useEnrichedStocks({ enabled = true }: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: ["stocks", "enriched"],
    queryFn: async () => {
      const { data, error } = await client.GET("/stocks/enriched")
      if (error) throw error
      return assertEnrichedStocks(data)
    },
    staleTime: 5 * 60 * 1000,
    enabled,
    placeholderData: keepPreviousData,
  })
}

export function useLastScan() {
  return useQuery({
    queryKey: ["scan", "last"],
    queryFn: async () => {
      const { data, error } = await client.GET("/scan/last")
      if (error) throw error
      return fromApiData<LastScanResponse>(data)
    },
    staleTime: 120 * 1000,
    refetchInterval: 120 * 1000,
    placeholderData: keepPreviousData,
  })
}

export function useHoldings() {
  return useQuery({
    queryKey: ["holdings"],
    queryFn: async () => {
      const { data, error } = await client.GET("/holdings")
      if (error) throw error
      return fromApiData<Holding[]>(data)
    },
    staleTime: 5 * 60 * 1000,
    placeholderData: keepPreviousData,
  })
}

export function useRebalance(displayCurrency: string) {
  return useQuery({
    queryKey: ["rebalance", displayCurrency],
    queryFn: async () => {
      const { data, error } = await client.GET("/rebalance", {
        params: { query: { display_currency: displayCurrency } },
      })
      if (error) throw error
      return fromApiData<RebalanceResponse>(data)
    },
    staleTime: 60 * 1000,
    // Keep previous currency's data visible while switching display currency
    placeholderData: keepPreviousData,
  })
}

export function useProfile() {
  return useQuery({
    queryKey: ["profile"],
    queryFn: async () => {
      const { data, error } = await client.GET("/profiles")
      if (error) throw error
      return fromApiData<ProfileResponse>(data)
    },
    staleTime: 5 * 60 * 1000,
    placeholderData: keepPreviousData,
  })
}

export function useFearGreed({ enabled = true }: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: ["market", "fear-greed"],
    queryFn: async () => {
      const { data, error } = await client.GET("/market/fear-greed")
      if (error) throw error
      return fromApiData<FearGreedResponse>(data)
    },
    staleTime: 5 * 60 * 1000,
    enabled,
    placeholderData: keepPreviousData,
  })
}

export function useSnapshots(days = 730) {
  return useQuery({
    queryKey: ["snapshots", days],
    queryFn: async () => {
      const { data, error } = await client.GET("/snapshots", {
        params: { query: { days } },
      })
      if (error) throw error
      return fromApiData<Snapshot[]>(data)
    },
    staleTime: 5 * 60 * 1000,
    placeholderData: keepPreviousData,
  })
}

export function useTwr() {
  return useQuery({
    queryKey: ["snapshots", "twr"],
    queryFn: async () => {
      const { data, error } = await client.GET("/snapshots/twr")
      if (error) throw error
      return fromApiData<TwrResponse>(data)
    },
    staleTime: 5 * 60 * 1000,
    placeholderData: keepPreviousData,
  })
}

export function useGreatMinds({ enabled = true }: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: ["resonance", "great-minds"],
    queryFn: async () => {
      const { data, error } = await client.GET("/resonance/great-minds")
      if (error) throw error
      return fromApiData<GreatMindsResponse>(data)
    },
    staleTime: 24 * 60 * 60 * 1000,
    enabled,
    placeholderData: keepPreviousData,
  })
}

export function useSignalActivity() {
  return useQuery({
    queryKey: ["signals", "activity"],
    queryFn: async () => {
      const { data, error } = await client.GET("/signals/activity")
      if (error) throw error
      return fromApiData<SignalActivityItem[]>(data)
    },
    staleTime: 120 * 1000,
    placeholderData: keepPreviousData,
  })
}

export function useInsights(displayCurrency: string, enabled = true) {
  return useQuery({
    queryKey: ["analytics", "insights", displayCurrency],
    queryFn: async () => {
      const { data, error } = await client.GET("/analytics/insights", {
        params: { query: { display_currency: displayCurrency } },
      })
      if (error) throw error
      return fromApiData<InsightResponse[]>(data)
    },
    staleTime: 5 * 60 * 1000,
    enabled,
    placeholderData: keepPreviousData,
  })
}
