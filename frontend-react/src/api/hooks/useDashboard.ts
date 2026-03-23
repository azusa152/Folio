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

// ---------------------------------------------------------------------------
// Rebalance localStorage cache — shows last known portfolio value on cold load
// ---------------------------------------------------------------------------

const REBALANCE_LS_KEY = "folio_rebalance_last"
const REBALANCE_LS_TTL_MS = 24 * 60 * 60 * 1000 // 24 hours

type RebalanceCacheEntry = Pick<
  RebalanceResponse,
  | "total_value"
  | "display_currency"
  | "calculated_at"
  | "source"
  | "snapshot_at"
  | "health_score"
  | "health_level"
> & {
  saved_at: number // epoch ms — used for TTL eviction
}

function saveRebalanceToLS(data: RebalanceResponse): void {
  // Only persist full live data, not snapshot fallbacks, to avoid persisting stale estimates.
  if (data.source === "snapshot") return
  try {
    const entry: RebalanceCacheEntry = {
      total_value: data.total_value,
      display_currency: data.display_currency,
      calculated_at: data.calculated_at,
      source: data.source ?? "live",
      snapshot_at: data.snapshot_at ?? null,
      health_score: data.health_score,
      health_level: data.health_level,
      saved_at: Date.now(),
    }
    localStorage.setItem(REBALANCE_LS_KEY, JSON.stringify(entry))
  } catch {
    // Ignore storage errors (private browsing, quota exceeded, etc.)
  }
}

function loadRebalanceFromLS(displayCurrency: string): RebalanceResponse | undefined {
  try {
    const raw = localStorage.getItem(REBALANCE_LS_KEY)
    if (!raw) return undefined
    const entry = JSON.parse(raw) as RebalanceCacheEntry
    // Discard if older than TTL — stale data from days ago is misleading.
    if (Date.now() - (entry.saved_at ?? 0) > REBALANCE_LS_TTL_MS) return undefined
    // Only use cached value if the currency matches what the user is currently viewing.
    if (entry.display_currency !== displayCurrency) return undefined
    // Reconstruct a minimal RebalanceResponse compatible shape so the UI can render it.
    // Preserve source and health fields from the real previous fetch so the UI
    // shows the correct indicator colour without a flash on data arrival.
    return {
      ...entry,
      categories: {},
      advice: [],
      holdings_detail: [],
      xray: [],
      xray_coverage_pct: 0,
      health_score: entry.health_score ?? 100,
      health_level: entry.health_level ?? "healthy",
      sector_exposure: [],
      source: entry.source ?? "snapshot",
    } as RebalanceResponse
  } catch {
    return undefined
  }
}

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
  const cached = loadRebalanceFromLS(displayCurrency)

  return useQuery({
    queryKey: ["rebalance", displayCurrency],
    queryFn: async () => {
      const { data, error } = await client.GET("/rebalance", {
        params: { query: { display_currency: displayCurrency } },
      })
      if (error) throw error
      const result = fromApiData<RebalanceResponse>(data)
      // Persist live data to localStorage for the next cold load.
      saveRebalanceToLS(result)
      return result
    },
    staleTime: 60 * 1000,
    retry: 3,
    retryDelay: (attempt) => Math.min(5_000 * 2 ** attempt, 30_000),
    // Keep previous currency's data visible while switching display currency
    placeholderData: keepPreviousData,
    // Use localStorage as initialData so the very first render shows a number
    // instead of N/A. initialDataUpdatedAt: 0 forces it to be treated as
    // immediately stale, triggering a background fetch for fresh data.
    initialData: cached,
    initialDataUpdatedAt: cached ? 0 : undefined,
    // Poll every 5 s while the backend returned a snapshot fallback so we pick
    // up the background-computed live result as soon as it's ready, rather than
    // waiting the full 60 s staleTime window.
    refetchInterval: (query) => (query.state.data?.source === "snapshot" ? 5_000 : false),
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
