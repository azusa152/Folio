import { createElement } from "react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { renderHook, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import client from "@/api/client"
import { useTransactions } from "../useTransactions"

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

describe("useTransactions", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("calls /transactions with filter params", async () => {
    mockClient.GET.mockResolvedValueOnce({ data: [], error: undefined })

    const { result } = renderHook(
      () => useTransactions({ ticker: "AAPL", holdingId: 1, limit: 20 }),
      { wrapper: createWrapper() },
    )

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(mockClient.GET).toHaveBeenCalledWith("/transactions", {
      params: {
        query: {
          ticker: "AAPL",
          holding_id: 1,
          limit: 20,
        },
      },
    })
  })
})
