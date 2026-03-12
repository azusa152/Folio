import { createElement } from "react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { renderHook, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import client from "@/api/client"
import { useAccountPositions, useAccountTransactions } from "../useAccounts"

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

const mockClient = client as unknown as { GET: ReturnType<typeof vi.fn> }

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
})
