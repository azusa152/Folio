import { createElement } from "react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { act, renderHook, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import client from "@/api/client"
import type { TransactionRequest } from "@/api/types/transaction"
import {
  useAddTransaction,
  useDeleteTransaction,
  useImportTransactions,
  useTransactions,
} from "../useTransactions"

vi.mock("@/api/client", () => ({
  default: {
    GET: vi.fn(),
    POST: vi.fn(),
    PUT: vi.fn(),
    PATCH: vi.fn(),
    DELETE: vi.fn(),
    use: vi.fn(),
  },
}))

const mockClient = client as unknown as {
  GET: ReturnType<typeof vi.fn>
  POST: ReturnType<typeof vi.fn>
  DELETE: ReturnType<typeof vi.fn>
}

const EXPECTED_INVALIDATION_KEYS = [
  ["transactions"],
  ["holdings"],
  ["rebalance"],
  ["drawdown"],
  ["risk-metrics"],
  ["currency-exposure"],
  ["stress-test"],
  ["snapshots"],
  ["account-cash-balances"],
  ["accounts"],
  ["account-summary"],
  ["account-positions"],
  ["account-transactions"],
  ["stocks"],
]

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  const wrapper = ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children)
  return { queryClient, wrapper }
}

function expectAllInvalidationKeys(invalidateSpy: unknown) {
  EXPECTED_INVALIDATION_KEYS.forEach((queryKey) => {
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey, refetchType: "all" })
  })
}

describe("useTransactions", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("calls /transactions with filter params", async () => {
    mockClient.GET.mockResolvedValueOnce({ data: [], error: undefined })

    const { result } = renderHook(
      () => useTransactions({ ticker: "AAPL", holdingId: 1, limit: 20 }),
      { wrapper: createWrapper().wrapper },
    )

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(mockClient.GET).toHaveBeenCalledWith("/transactions", {
      params: {
        query: {
          ticker: "AAPL",
          account_id: undefined,
          holding_id: 1,
          limit: 20,
        },
      },
    })
  })

  it("invalidates all derived queries on add transaction success", async () => {
    mockClient.POST.mockResolvedValueOnce({
      data: { id: 1, auto_radar: false },
      error: undefined,
    })
    const { queryClient, wrapper } = createWrapper()
    const invalidateSpy = vi
      .spyOn(queryClient, "invalidateQueries")
      .mockResolvedValue(undefined)

    const { result } = renderHook(() => useAddTransaction(), { wrapper })

    await act(async () => {
      await result.current.mutateAsync({
        ticker: "AAPL",
        transaction_type: "BUY",
      } as unknown as TransactionRequest)
    })

    expectAllInvalidationKeys(invalidateSpy)
  })

  it("invalidates all derived queries on delete transaction success", async () => {
    mockClient.DELETE.mockResolvedValueOnce({ error: undefined })
    const { queryClient, wrapper } = createWrapper()
    const invalidateSpy = vi
      .spyOn(queryClient, "invalidateQueries")
      .mockResolvedValue(undefined)

    const { result } = renderHook(() => useDeleteTransaction(), { wrapper })

    await act(async () => {
      await result.current.mutateAsync(1)
    })

    expectAllInvalidationKeys(invalidateSpy)
  })

  it("invalidates all derived queries on import transactions success", async () => {
    mockClient.POST.mockResolvedValueOnce({
      data: { success_count: 1, failed: [] },
      error: undefined,
    })
    const { queryClient, wrapper } = createWrapper()
    const invalidateSpy = vi
      .spyOn(queryClient, "invalidateQueries")
      .mockResolvedValue(undefined)

    const { result } = renderHook(() => useImportTransactions(), { wrapper })

    await act(async () => {
      await result.current.mutateAsync({
        mode: "append",
        items: [],
      })
    })

    expectAllInvalidationKeys(invalidateSpy)
  })
})
