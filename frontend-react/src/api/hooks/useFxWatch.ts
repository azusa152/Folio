import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import client from "@/api/client"
import { fromApiData } from "@/api/lib/fromApi"
import type {
  FxWatch,
  FxAnalysis,
  FxAnalysisMap,
  FxAnalysisState,
  FxCheckResponse,
  FxHistoryPoint,
  CreateFxWatchRequest,
  UpdateFxWatchRequest,
} from "@/api/types/fxWatch"

// ---------------------------------------------------------------------------
// Query hooks
// ---------------------------------------------------------------------------

export function useFxWatches() {
  return useQuery<FxWatch[]>({
    queryKey: ["fxWatches"],
    queryFn: async () => {
      const { data, error } = await client.GET("/fx-watch")
      if (error) throw error
      return fromApiData<FxWatch[]>(data)
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function useFxHistory(base: string, quote: string, enabled = true) {
  return useQuery<FxHistoryPoint[]>({
    queryKey: ["fxHistory", base, quote],
    queryFn: async () => {
      const { data, error } = await client.GET("/forex/{base}/{quote}/history-long", {
        params: { path: { base, quote } },
      })
      if (error) throw error
      return fromApiData<FxHistoryPoint[]>(data)
    },
    staleTime: 5 * 60 * 1000,
    enabled,
  })
}

/** Eagerly fetches history for a list of currency pairs for sparklines. */
export function useFxHistoryMap(pairs: Array<{ base: string; quote: string }>) {
  return useQuery<Record<string, FxHistoryPoint[]>>({
    queryKey: ["fxHistoryMap", pairs.map((p) => `${p.base}/${p.quote}`).join(",")],
    queryFn: async () => {
      const entries = await Promise.all(
        pairs.map(async ({ base, quote }) => {
          try {
            const { data, error } = await client.GET("/forex/{base}/{quote}/history-long", {
              params: { path: { base, quote } },
            })
            if (error) return [`${base}/${quote}`, []] as const
            return [`${base}/${quote}`, fromApiData<FxHistoryPoint[]>(data)] as const
          } catch {
            return [`${base}/${quote}`, []] as const
          }
        }),
      )
      return Object.fromEntries(entries)
    },
    staleTime: 5 * 60 * 1000,
    enabled: pairs.length > 0,
  })
}

// ---------------------------------------------------------------------------
// Mutation hooks
// ---------------------------------------------------------------------------

export function useCreateFxWatch() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: CreateFxWatchRequest) => {
      const { data, error } = await client.POST("/fx-watch", { body: payload })
      if (error) throw error
      return fromApiData<FxWatch>(data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fxWatches"] })
    },
  })
}

export function useUpdateFxWatch() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: UpdateFxWatchRequest }) => {
      const { data, error } = await client.PATCH("/fx-watch/{watch_id}", {
        params: { path: { watch_id: id } },
        body: payload,
      })
      if (error) throw error
      return fromApiData<FxWatch>(data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fxWatches"] })
    },
  })
}

export function useDeleteFxWatch() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: number) => {
      const { error } = await client.DELETE("/fx-watch/{watch_id}", {
        params: { path: { watch_id: id } },
      })
      if (error) throw error
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fxWatches"] })
    },
  })
}

export function useToggleFxWatch() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, isActive }: { id: number; isActive: boolean }) => {
      const { data, error } = await client.PATCH("/fx-watch/{watch_id}", {
        params: { path: { watch_id: id } },
        body: { is_active: !isActive },
      })
      if (error) throw error
      return fromApiData<FxWatch>(data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fxWatches"] })
    },
  })
}

async function fetchFxAnalysis(forceRefresh = false): Promise<FxAnalysisState> {
  const { data, error } = await client.POST("/fx-watch/check", {
    params: { query: { force_refresh: forceRefresh } },
  })
  if (error) throw error
  const response = fromApiData<FxCheckResponse>(data)
  const map: FxAnalysisMap = {}
  for (const r of response.results) {
    const entry: FxAnalysis = {
      current_rate: r.result.current_rate,
      should_alert: r.result.should_alert,
      scenario: r.result.scenario,
      recommendation: r.result.recommendation,
      reasoning: r.result.reasoning,
      is_recent_high: r.result.is_recent_high,
      lookback_high: r.result.lookback_high,
      lookback_days: r.result.lookback_days,
      high_days_ago: r.result.high_days_ago,
      distance_from_high_pct: r.result.distance_from_high_pct,
      consecutive_increases: r.result.consecutive_increases,
      consecutive_threshold: r.result.consecutive_threshold,
      trend_direction: r.result.trend_direction,
      trend_strength_pct: r.result.trend_strength_pct,
      signal_strength: r.result.signal_strength,
      target_rate: r.result.target_rate ?? null,
      target_direction: r.result.target_direction ?? null,
      target_hit: r.result.target_hit ?? false,
      target_distance_pct: r.result.target_distance_pct ?? null,
    }
    map[r.watch_id] = entry
  }
  return { checked_at: response.checked_at, by_watch_id: map }
}

/** Auto-fetches analysis for all active FX watches. Enabled only when watches exist. */
export function useFxAnalysis(hasWatches: boolean) {
  return useQuery<FxAnalysisState>({
    queryKey: ["fxAnalysis"],
    queryFn: () => fetchFxAnalysis(false),
    enabled: hasWatches,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  })
}

export function useCheckFxWatches() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => fetchFxAnalysis(false),
    onSuccess: (data) => {
      queryClient.setQueryData(["fxAnalysis"], data)
      queryClient.invalidateQueries({ queryKey: ["fxWatches"] })
    },
  })
}

export function useAlertFxWatches() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const { data, error } = await client.POST("/fx-watch/alert")
      if (error) throw error
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["fxWatches"] })
    },
  })
}

export function useRefreshFxRates() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => fetchFxAnalysis(true),
    onSuccess: (data) => {
      queryClient.setQueryData(["fxAnalysis"], data)
      queryClient.invalidateQueries({ queryKey: ["fxWatches"] })
      queryClient.invalidateQueries({ queryKey: ["fxHistoryMap"] })
      queryClient.invalidateQueries({ queryKey: ["fxHistory"] })
    },
  })
}
