import { createElement } from "react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { act, renderHook, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import client from "@/api/client"
import { useAccountPositions, useAccountTransactions, useDeactivateAccount } from "../useAccounts"

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
  DELETE: ReturnType<typeof vi.fn>
}

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return ({ children }: { children: React.ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children)
}

describe("useAccounts extra hooks", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("calls account positions endpoint", async () => {
    mockClient.GET.mockResolvedValueOnce({ data: [], error: undefined })

    const { result } = renderHook(() => useAccountPositions(7), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockClient.GET).toHaveBeenCalledWith("/accounts/{account_id}/positions", {
      params: { path: { account_id: 7 } },
    })
  })

  it("calls account transactions endpoint with pagination", async () => {
    mockClient.GET.mockResolvedValueOnce({ data: [], error: undefined })

    const { result } = renderHook(() => useAccountTransactions(7, true, 50, 10), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(mockClient.GET).toHaveBeenCalledWith(
      "/accounts/{account_id}/transactions",
      {
        params: {
          path: { account_id: 7 },
          query: { limit: 50, offset: 10 },
        },
      },
    )
  })

  it("invalidates holdings and rebalance after account deactivation", async () => {
    mockClient.DELETE.mockResolvedValueOnce({ error: undefined })

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    const invalidateSpy = vi
      .spyOn(queryClient, "invalidateQueries")
      .mockResolvedValue(undefined)

    const wrapper = ({ children }: { children: React.ReactNode }) =>
      createElement(QueryClientProvider, { client: queryClient }, children)

    const { result } = renderHook(() => useDeactivateAccount(), { wrapper })

    await act(async () => {
      await result.current.mutateAsync(7)
    })

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["accounts"] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["account-summary"] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["holdings"] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["rebalance"] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["currency-exposure"] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["stress-test"] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["net-worth"] })
  })
})
