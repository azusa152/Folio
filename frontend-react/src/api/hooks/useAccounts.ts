import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import client from "@/api/client"
import type {
  AccountCashBalanceItem,
  AccountRequest,
  AccountResponse,
  AccountSummaryItem,
  AccountUpdateRequest,
} from "@/api/types/account"
import type { Holding } from "@/api/types/dashboard"
import type { TransactionResponse } from "@/api/types/transaction"

export function useAccounts(enabled = true, includeInactive = false) {
  return useQuery<AccountResponse[]>({
    queryKey: ["accounts", includeInactive],
    queryFn: async () => {
      const { data, error } = await client.GET("/accounts", {
        params: {
          query: {
            include_inactive: includeInactive || undefined,
          },
        },
      })
      if (error) throw error
      return (data ?? []) as unknown as AccountResponse[]
    },
    staleTime: 60 * 1000,
    enabled,
  })
}

export function useAccountSummary(enabled = true) {
  return useQuery<AccountSummaryItem[]>({
    queryKey: ["account-summary"],
    queryFn: async () => {
      const { data, error } = await client.GET("/accounts/summary")
      if (error) throw error
      return (data ?? []) as unknown as AccountSummaryItem[]
    },
    enabled,
    staleTime: 30 * 1000,
  })
}

export function useAccountCashBalances(accountId: number | null, enabled = true) {
  return useQuery<AccountCashBalanceItem[]>({
    queryKey: ["account-cash-balances", accountId],
    queryFn: async () => {
      if (accountId == null) return []
      const { data, error } = await client.GET("/accounts/{account_id}/cash-balances", {
        params: { path: { account_id: accountId } },
      })
      if (error) throw error
      return (data ?? []) as unknown as AccountCashBalanceItem[]
    },
    enabled: enabled && accountId != null,
    staleTime: 30 * 1000,
  })
}

export function useAccountPositions(accountId: number | null, enabled = true) {
  return useQuery<Holding[]>({
    queryKey: ["account-positions", accountId],
    queryFn: async () => {
      if (accountId == null) return []
      const { data, error } = await client.GET("/accounts/{account_id}/positions", {
        params: { path: { account_id: accountId } },
      })
      if (error) throw error
      return (data ?? []) as unknown as Holding[]
    },
    enabled: enabled && accountId != null,
    staleTime: 30 * 1000,
  })
}

export function useAccountTransactions(
  accountId: number | null,
  enabled = true,
  limit = 100,
  offset = 0,
) {
  return useQuery<TransactionResponse[]>({
    queryKey: ["account-transactions", accountId, limit, offset],
    queryFn: async () => {
      if (accountId == null) return []
      const { data, error } = await client.GET("/accounts/{account_id}/transactions", {
        params: {
          path: { account_id: accountId },
          query: { limit, offset },
        },
      })
      if (error) throw error
      return (data ?? []) as unknown as TransactionResponse[]
    },
    enabled: enabled && accountId != null,
    staleTime: 30 * 1000,
  })
}

export function useCreateAccount() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: AccountRequest) => {
      const { data, error } = await client.POST("/accounts", { body: payload })
      if (error) throw error
      return data as unknown as AccountResponse
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounts"] })
      queryClient.invalidateQueries({ queryKey: ["account-summary"] })
    },
  })
}

export function useUpdateAccount() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      accountId,
      payload,
    }: {
      accountId: number
      payload: AccountUpdateRequest
    }) => {
      const { data, error } = await client.PUT("/accounts/{account_id}", {
        params: { path: { account_id: accountId } },
        body: payload,
      })
      if (error) throw error
      return data as unknown as AccountResponse
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounts"] })
      queryClient.invalidateQueries({ queryKey: ["account-summary"] })
    },
  })
}

export function useDeactivateAccount() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (accountId: number) => {
      const { error } = await client.DELETE("/accounts/{account_id}", {
        params: { path: { account_id: accountId } },
      })
      if (error) throw error
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["accounts"] })
      queryClient.invalidateQueries({ queryKey: ["account-summary"] })
      queryClient.invalidateQueries({ queryKey: ["holdings"] })
      queryClient.invalidateQueries({ queryKey: ["rebalance"] })
      queryClient.invalidateQueries({ queryKey: ["currency-exposure"] })
      queryClient.invalidateQueries({ queryKey: ["stress-test"] })
    },
  })
}
