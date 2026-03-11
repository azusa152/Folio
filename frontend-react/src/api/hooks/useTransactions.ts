import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import client from "@/api/client"
import type { TransactionRequest, TransactionResponse } from "@/api/types/transaction"

interface UseTransactionsOptions {
  ticker?: string
  accountId?: number
  holdingId?: number
  limit?: number
  enabled?: boolean
}

export function useTransactions({
  ticker,
  accountId,
  holdingId,
  limit = 200,
  enabled = true,
}: UseTransactionsOptions = {}) {
  return useQuery<TransactionResponse[]>({
    queryKey: ["transactions", ticker ?? "", accountId ?? null, holdingId ?? null, limit],
    queryFn: async () => {
      const { data, error } = await client.GET("/transactions", {
        params: {
          query: {
            ticker: ticker || undefined,
            account_id: accountId,
            holding_id: holdingId,
            limit,
          },
        },
      })
      if (error) throw error
      return data as unknown as TransactionResponse[]
    },
    staleTime: 60 * 1000,
    enabled,
  })
}

export function useAddTransaction() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload: TransactionRequest) => {
      const { data, error } = await client.POST("/transactions", { body: payload })
      if (error) throw error
      return data as unknown as TransactionResponse
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions"] })
      queryClient.invalidateQueries({ queryKey: ["holdings"] })
      queryClient.invalidateQueries({ queryKey: ["rebalance"] })
      queryClient.invalidateQueries({ queryKey: ["account-cash-balances"] })
      queryClient.invalidateQueries({ queryKey: ["accounts"] })
    },
  })
}

export function useDeleteTransaction() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (txnId: number) => {
      const { error } = await client.DELETE("/transactions/{txn_id}", {
        params: { path: { txn_id: txnId } },
      })
      if (error) throw error
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions"] })
      queryClient.invalidateQueries({ queryKey: ["holdings"] })
      queryClient.invalidateQueries({ queryKey: ["rebalance"] })
      queryClient.invalidateQueries({ queryKey: ["account-cash-balances"] })
      queryClient.invalidateQueries({ queryKey: ["accounts"] })
    },
  })
}
