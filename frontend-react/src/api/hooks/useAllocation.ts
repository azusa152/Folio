import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import client from "@/api/client"
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
  UpdateProfileRequest,
  SaveTelegramRequest,
  SavePreferencesRequest,
  ProfileResponse,
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
      return data as unknown as PersonaTemplate[]
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
      return data as unknown as AllocRebalanceResponse
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
      return data as unknown as CurrencyExposureResponse
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
      return data as unknown as StressTestResponse
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
      return data as unknown as TelegramSettings
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
      return data as unknown as AllocPreferencesResponse
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
      return data as unknown as ProfileResponse
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
      return data as unknown as ProfileResponse
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
      return data as unknown as WithdrawResponse
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
      return data as unknown as TelegramSettings
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
      return data as unknown as AllocPreferencesResponse
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings", "preferences"] })
    },
  })
}
