import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import client from "@/api/client"
import { fromApiData } from "@/api/lib/fromApi"
import type {
  PersonaTemplate,
  AllocRebalanceResponse,
  CurrencyExposureResponse,
  StressTestResponse,
  WithdrawResponse,
  TelegramSettings,
  AllocPreferencesResponse,
  WithdrawRequest,
  CreateProfileRequest,
  DividendApplyAllResponse,
  DividendApplyResponse,
  DividendCheckResponse,
  DividendDismissResponse,
  DividendEvent,
  UpdateProfileRequest,
  SaveTelegramRequest,
  SavePreferencesRequest,
  ProfileResponse,
  StockSplitApplyAllResponse,
  StockSplitApplyResponse,
  StockSplitCheckResponse,
  StockSplitDismissResponse,
  StockSplitEvent,
} from "@/api/types/allocation"

// ---------------------------------------------------------------------------
// Query hooks
// ---------------------------------------------------------------------------

export function useTemplates() {
  return useQuery<PersonaTemplate[]>({
    queryKey: ["personas", "templates"],
    queryFn: async () => {
      const { data, error } = await client.GET("/personas/templates")
      if (error) throw error
      return fromApiData<PersonaTemplate[]>(data)
    },
    staleTime: 24 * 60 * 60 * 1000,
  })
}

export function useAllocRebalance(displayCurrency: string, enabled = true) {
  return useQuery<AllocRebalanceResponse>({
    queryKey: ["rebalance", displayCurrency],
    queryFn: async () => {
      const { data, error } = await client.GET("/rebalance", {
        params: { query: { display_currency: displayCurrency } },
      })
      if (error) throw error
      return fromApiData<AllocRebalanceResponse>(data)
    },
    staleTime: 60 * 1000,
    enabled,
  })
}

export function useCurrencyExposure(enabled = true, homeCurrency?: string) {
  return useQuery<CurrencyExposureResponse>({
    queryKey: ["currency-exposure", homeCurrency ?? "default"],
    queryFn: async () => {
      const { data, error } = await client.GET("/currency-exposure", {
        params: { query: { home_currency: homeCurrency } },
      })
      if (error) throw error
      return fromApiData<CurrencyExposureResponse>(data)
    },
    staleTime: 60 * 1000,
    enabled,
  })
}

export function useStressTest(dropPct: number, currency: string, enabled = true) {
  return useQuery<StressTestResponse>({
    queryKey: ["stress-test", dropPct, currency],
    queryFn: async () => {
      const { data, error } = await client.GET("/stress-test", {
        params: { query: { scenario_drop_pct: dropPct, display_currency: currency } },
      })
      if (error) throw error
      return fromApiData<StressTestResponse>(data)
    },
    staleTime: 60 * 1000,
    enabled,
  })
}

export function useTelegramSettings() {
  return useQuery<TelegramSettings>({
    queryKey: ["settings", "telegram"],
    queryFn: async () => {
      const { data, error } = await client.GET("/settings/telegram")
      if (error) throw error
      return fromApiData<TelegramSettings>(data)
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function usePreferences() {
  return useQuery<AllocPreferencesResponse>({
    queryKey: ["settings", "preferences"],
    queryFn: async () => {
      const { data, error } = await client.GET("/settings/preferences")
      if (error) throw error
      return fromApiData<AllocPreferencesResponse>(data)
    },
    staleTime: 5 * 60 * 1000,
  })
}

// ---------------------------------------------------------------------------
// Mutation hooks
// ---------------------------------------------------------------------------

export function useCreateProfile() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: CreateProfileRequest) => {
      const { data, error } = await client.POST("/profiles", { body: payload })
      if (error) throw error
      return fromApiData<ProfileResponse>(data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["profile"] })
    },
  })
}

export function useUpdateProfile() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: UpdateProfileRequest }) => {
      const { data, error } = await client.PUT("/profiles/{profile_id}", {
        params: { path: { profile_id: id } },
        body: payload,
      })
      if (error) throw error
      return fromApiData<ProfileResponse>(data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["profile"] })
      queryClient.invalidateQueries({ queryKey: ["currency-exposure"] })
    },
  })
}

export function useWithdraw() {
  return useMutation({
    mutationFn: async (payload: WithdrawRequest) => {
      const { data, error } = await client.POST("/withdraw", { body: payload })
      if (error) throw error
      return fromApiData<WithdrawResponse>(data)
    },
  })
}

export function useXRayAlert() {
  return useMutation({
    mutationFn: async () => {
      const { data, error } = await client.POST("/rebalance/xray-alert")
      if (error) throw error
      return data
    },
  })
}

export function useFxExposureAlert() {
  return useMutation({
    mutationFn: async () => {
      const { data, error } = await client.POST("/currency-exposure/alert")
      if (error) throw error
      return data
    },
  })
}

export function useSaveTelegram() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: SaveTelegramRequest) => {
      const { data, error } = await client.PUT("/settings/telegram", { body: payload })
      if (error) throw error
      return fromApiData<TelegramSettings>(data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings", "telegram"] })
    },
  })
}

export function useTestTelegram() {
  return useMutation({
    mutationFn: async () => {
      const { data, error } = await client.POST("/settings/telegram/test")
      if (error) throw error
      return data
    },
  })
}

export function useTriggerDigest() {
  return useMutation({
    mutationFn: async () => {
      const { data, error } = await client.POST("/digest")
      if (error) throw error
      return data
    },
  })
}

export function useSavePreferences() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: SavePreferencesRequest) => {
      const { data, error } = await client.PUT("/settings/preferences", { body: payload })
      if (error) throw error
      return fromApiData<AllocPreferencesResponse>(data)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings", "preferences"] })
    },
  })
}

function invalidateStockSplitDerivedQueries(queryClient: ReturnType<typeof useQueryClient>) {
  ;[
    ["stock-splits", "pending"],
    ["transactions"],
    ["holdings"],
    ["rebalance"],
    ["account-transactions"],
    ["account-positions"],
  ].forEach((queryKey) => {
    queryClient.invalidateQueries({ queryKey: [...queryKey], refetchType: "all" })
  })
}

function invalidateDividendDerivedQueries(queryClient: ReturnType<typeof useQueryClient>) {
  ;[
    ["dividends", "pending"],
    ["transactions"],
    ["holdings"],
    ["rebalance"],
    ["account-transactions"],
    ["account-positions"],
  ].forEach((queryKey) => {
    queryClient.invalidateQueries({ queryKey: [...queryKey], refetchType: "all" })
  })
}

export function usePendingStockSplits(enabled = true) {
  return useQuery<StockSplitEvent[]>({
    queryKey: ["stock-splits", "pending"],
    queryFn: async () => {
      const { data, error } = await client.GET("/stock-splits/pending")
      if (error) throw error
      return fromApiData<StockSplitEvent[]>(data)
    },
    staleTime: 60 * 1000,
    enabled,
  })
}

export function useCheckStockSplits() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const { data, error } = await client.POST("/stock-splits/check")
      if (error) throw error
      return fromApiData<StockSplitCheckResponse>(data)
    },
    onSuccess: () => {
      invalidateStockSplitDerivedQueries(queryClient)
    },
  })
}

export function useApplyStockSplit() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (eventId: number) => {
      const { data, error } = await client.POST("/stock-splits/{event_id}/apply", {
        params: { path: { event_id: eventId } },
      })
      if (error) throw error
      return fromApiData<StockSplitApplyResponse>(data)
    },
    onSuccess: () => {
      invalidateStockSplitDerivedQueries(queryClient)
    },
  })
}

export function useDismissStockSplit() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (eventId: number) => {
      const { data, error } = await client.POST("/stock-splits/{event_id}/dismiss", {
        params: { path: { event_id: eventId } },
      })
      if (error) throw error
      return fromApiData<StockSplitDismissResponse>(data)
    },
    onSuccess: () => {
      invalidateStockSplitDerivedQueries(queryClient)
    },
  })
}

export function useApplyAllStockSplits() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const { data, error } = await client.POST("/stock-splits/apply-all")
      if (error) throw error
      return fromApiData<StockSplitApplyAllResponse>(data)
    },
    onSuccess: () => {
      invalidateStockSplitDerivedQueries(queryClient)
    },
  })
}

export function usePendingDividends(enabled = true) {
  return useQuery<DividendEvent[]>({
    queryKey: ["dividends", "pending"],
    queryFn: async () => {
      const { data, error } = await client.GET("/dividends/pending")
      if (error) throw error
      return fromApiData<DividendEvent[]>(data)
    },
    staleTime: 60 * 1000,
    enabled,
  })
}

export function useCheckDividends() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const { data, error } = await client.POST("/dividends/check")
      if (error) throw error
      return fromApiData<DividendCheckResponse>(data)
    },
    onSuccess: () => {
      invalidateDividendDerivedQueries(queryClient)
    },
  })
}

export function useApplyDividend() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (eventId: number) => {
      const { data, error } = await client.POST("/dividends/{event_id}/apply", {
        params: { path: { event_id: eventId } },
      })
      if (error) throw error
      return fromApiData<DividendApplyResponse>(data)
    },
    onSuccess: () => {
      invalidateDividendDerivedQueries(queryClient)
    },
  })
}

export function useDismissDividend() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (eventId: number) => {
      const { data, error } = await client.POST("/dividends/{event_id}/dismiss", {
        params: { path: { event_id: eventId } },
      })
      if (error) throw error
      return fromApiData<DividendDismissResponse>(data)
    },
    onSuccess: () => {
      invalidateDividendDerivedQueries(queryClient)
    },
  })
}

export function useApplyAllDividends() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      const { data, error } = await client.POST("/dividends/apply-all")
      if (error) throw error
      return fromApiData<DividendApplyAllResponse>(data)
    },
    onSuccess: () => {
      invalidateDividendDerivedQueries(queryClient)
    },
  })
}
