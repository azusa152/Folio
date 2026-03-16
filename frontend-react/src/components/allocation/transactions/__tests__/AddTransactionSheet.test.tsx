import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { AddTransactionSheet } from "../AddTransactionSheet"

const { mockMutate, toastSuccessMock, toastErrorMock, toastInfoMock, radarState, wrapperState } = vi.hoisted(() => ({
  mockMutate: vi.fn(),
  toastSuccessMock: vi.fn(),
  toastErrorMock: vi.fn(),
  toastInfoMock: vi.fn(),
  radarState: {
    stocks: [] as Array<{ ticker: string }>,
    isLoading: false,
  },
  wrapperState: {
    eligibleItems: [] as Array<{ ticker: string; fund_name: string; trust_fee_pct?: number }>,
  },
}))

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}))

vi.mock("sonner", () => ({
  toast: { success: toastSuccessMock, error: toastErrorMock, info: toastInfoMock },
}))

vi.mock("@/api/hooks/useTransactions", () => ({
  useAddTransaction: () => ({ mutate: mockMutate, isPending: false }),
}))

vi.mock("@/api/hooks/useDashboard", () => ({
  useHoldings: () => ({
    data: [{ id: 1, ticker: "AAPL" }],
  }),
}))

vi.mock("@/api/hooks/useRadar", () => ({
  useRadarStocks: () => ({
    data: radarState.stocks,
    isLoading: radarState.isLoading,
  }),
}))

vi.mock("@/api/hooks/useAccounts", () => ({
  useAccounts: () => ({
    data: [{ id: 7, name: "IB Main", broker: "Interactive Brokers" }],
  }),
  useAccountCashBalances: () => ({
    data: [{ currency: "USD", balance: 500 }],
  }),
}))

vi.mock("@/api/hooks/useWrappers", () => ({
  useWrapperEligibility: () => ({ data: undefined, isLoading: false }),
  useSuggestRouting: () => ({ data: undefined, isLoading: false }),
  useEligibleAssets: () => ({
    data: { items: wrapperState.eligibleItems },
    isLoading: false,
  }),
}))

describe("AddTransactionSheet", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    radarState.stocks = []
    radarState.isLoading = false
    wrapperState.eligibleItems = []
    Object.defineProperty(Element.prototype, "scrollIntoView", {
      value: vi.fn(),
      writable: true,
    })
  })

  it("validates fx rate and fee before submit", () => {
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultTicker="AAPL" />
      </QueryClientProvider>,
    )

    fireEvent.change(screen.getByLabelText("transactions.form.account"), { target: { value: "7" } })
    fireEvent.change(screen.getByLabelText("transactions.form.quantity"), { target: { value: "2" } })
    fireEvent.change(screen.getByLabelText("transactions.form.price"), { target: { value: "10" } })
    fireEvent.change(screen.getByLabelText("transactions.form.total_amount"), { target: { value: "20" } })

    fireEvent.click(screen.getByRole("button", { name: "transactions.form.show_more" }))
    fireEvent.change(screen.getByLabelText("transactions.form.fx_rate"), { target: { value: "0" } })
    fireEvent.change(screen.getByLabelText("transactions.form.fee"), { target: { value: "-1" } })
    fireEvent.click(screen.getByRole("button", { name: "transactions.form.submit" }))

    expect(screen.getByText("transactions.form.error_fx_rate")).toBeInTheDocument()
    expect(screen.getByText("transactions.form.error_fee")).toBeInTheDocument()
    expect(mockMutate).not.toHaveBeenCalled()
  })

  it("can switch back to auto total", () => {
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultTicker="AAPL" />
      </QueryClientProvider>,
    )

    fireEvent.change(screen.getByLabelText("transactions.form.quantity"), { target: { value: "2" } })
    fireEvent.change(screen.getByLabelText("transactions.form.price"), { target: { value: "3" } })
    expect(screen.getByDisplayValue("6")).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText("transactions.form.total_amount"), { target: { value: "8" } })
    fireEvent.change(screen.getByLabelText("transactions.form.quantity"), { target: { value: "4" } })
    expect(screen.getByDisplayValue("8")).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: "transactions.form.use_auto_total" }))
    expect(screen.getByDisplayValue("12")).toBeInTheDocument()
  })

  it("prefills holding selection from default ticker", () => {
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultTicker="AAPL" />
      </QueryClientProvider>,
    )

    fireEvent.click(screen.getByRole("button", { name: "transactions.form.show_more" }))
    const holdingSelect = screen.getByLabelText("transactions.form.holding_link") as HTMLSelectElement
    expect(holdingSelect.value).toBe("1")
  })

  it("renders account selector and cash balance", () => {
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultTicker="AAPL" />
      </QueryClientProvider>,
    )

    expect(screen.getByLabelText("transactions.form.account")).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText("transactions.form.account"), { target: { value: "7" } })
    expect(screen.getByText("transactions.form.available_cash")).toBeInTheDocument()
  })

  it("shows required account placeholder for buy", () => {
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultTicker="AAPL" />
      </QueryClientProvider>,
    )

    expect(screen.getByRole("option", { name: "transactions.form.account_required" })).toBeInTheDocument()
  })

  it("shows insufficient balance helper and can switch to deposit", () => {
    mockMutate.mockImplementationOnce((_payload, opts) => {
      opts?.onError?.({
        detail: {
          error_code: "INSUFFICIENT_BALANCE",
          available: 10,
          required: 20,
        },
      })
    })

    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultTicker="AAPL" defaultAccountId={7} />
      </QueryClientProvider>,
    )

    fireEvent.change(screen.getByLabelText("transactions.form.quantity"), { target: { value: "1" } })
    fireEvent.change(screen.getByLabelText("transactions.form.price"), { target: { value: "20" } })
    fireEvent.change(screen.getByLabelText("transactions.form.total_amount"), { target: { value: "20" } })
    fireEvent.click(screen.getByRole("button", { name: "transactions.form.submit" }))

    expect(screen.getByText("transactions.form.insufficient_balance")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "transactions.form.deposit_cash" }))
    expect(screen.getByDisplayValue("10")).toBeInTheDocument()
  })

  it("simplifies fields for deposit transactions", () => {
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultTicker="AAPL" defaultAccountId={7} />
      </QueryClientProvider>,
    )

    fireEvent.click(screen.getByRole("button", { name: "transactions.type.deposit" }))

    expect(screen.queryByLabelText("transactions.form.ticker")).not.toBeInTheDocument()
    expect(screen.queryByLabelText("transactions.form.quantity")).not.toBeInTheDocument()
    expect(screen.queryByLabelText("transactions.form.price")).not.toBeInTheDocument()
    expect(screen.getByText("transactions.form.deposit_amount")).toBeInTheDocument()
    expect(screen.getByLabelText("transactions.form.currency")).toBeInTheDocument()
  })

  it("prevents submit and shows warning when buy balance is insufficient", () => {
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultTicker="AAPL" defaultAccountId={7} />
      </QueryClientProvider>,
    )

    fireEvent.change(screen.getByLabelText("transactions.form.quantity"), { target: { value: "1" } })
    fireEvent.change(screen.getByLabelText("transactions.form.price"), { target: { value: "600" } })
    fireEvent.change(screen.getByLabelText("transactions.form.total_amount"), { target: { value: "600" } })
    fireEvent.click(screen.getByRole("button", { name: "transactions.form.submit" }))

    expect(screen.getByText("transactions.form.insufficient_balance")).toBeInTheDocument()
    expect(mockMutate).not.toHaveBeenCalled()
  })

  it("clears insufficient warning when switching to deposit", () => {
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultTicker="AAPL" defaultAccountId={7} />
      </QueryClientProvider>,
    )

    fireEvent.change(screen.getByLabelText("transactions.form.quantity"), { target: { value: "1" } })
    fireEvent.change(screen.getByLabelText("transactions.form.price"), { target: { value: "600" } })
    fireEvent.change(screen.getByLabelText("transactions.form.total_amount"), { target: { value: "600" } })
    fireEvent.click(screen.getByRole("button", { name: "transactions.form.submit" }))

    expect(screen.getByText("transactions.form.insufficient_balance")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "transactions.type.deposit" }))
    expect(screen.queryByText("transactions.form.insufficient_balance")).not.toBeInTheDocument()
  })

  it("treats missing currency cash balance as zero in buy precheck", () => {
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultTicker="AAPL" defaultAccountId={7} />
      </QueryClientProvider>,
    )

    fireEvent.click(screen.getByRole("button", { name: "transactions.form.show_more" }))
    fireEvent.change(screen.getByLabelText("transactions.form.currency"), { target: { value: "EUR" } })
    fireEvent.change(screen.getByLabelText("transactions.form.quantity"), { target: { value: "1" } })
    fireEvent.change(screen.getByLabelText("transactions.form.price"), { target: { value: "10" } })
    fireEvent.change(screen.getByLabelText("transactions.form.total_amount"), { target: { value: "10" } })
    fireEvent.click(screen.getByRole("button", { name: "transactions.form.submit" }))

    expect(screen.getByText("transactions.form.insufficient_balance")).toBeInTheDocument()
    expect(mockMutate).not.toHaveBeenCalled()
  })

  it("does not show thesis field while radar stocks are loading", () => {
    radarState.isLoading = true
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultTicker="AAPL" />
      </QueryClientProvider>,
    )

    expect(screen.queryByLabelText("transactions.form.thesis")).not.toBeInTheDocument()
  })

  it("shows thesis field only when ticker is new to radar", () => {
    radarState.stocks = [{ ticker: "NVDA" }]
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultTicker="AAPL" />
      </QueryClientProvider>,
    )

    expect(screen.getByLabelText("transactions.form.thesis")).toBeInTheDocument()
    expect(screen.getByLabelText("transactions.form.category")).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText("transactions.form.ticker"), { target: { value: "NVDA" } })
    expect(screen.queryByLabelText("transactions.form.thesis")).not.toBeInTheDocument()
    expect(screen.queryByLabelText("transactions.form.category")).not.toBeInTheDocument()
  })


  it("submits default category for new-to-radar ticker", () => {
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultTicker="AAPL" defaultAccountId={7} />
      </QueryClientProvider>,
    )

    fireEvent.change(screen.getByLabelText("transactions.form.quantity"), { target: { value: "1" } })
    fireEvent.change(screen.getByLabelText("transactions.form.price"), { target: { value: "10" } })
    fireEvent.change(screen.getByLabelText("transactions.form.total_amount"), { target: { value: "10" } })
    fireEvent.click(screen.getByRole("button", { name: "transactions.form.submit" }))

    expect(mockMutate).toHaveBeenCalled()
    const [payload] = mockMutate.mock.calls[0]
    expect(payload.category).toBe("Growth")
  })

  it("submits selected category for new-to-radar ticker", () => {
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultTicker="AAPL" defaultAccountId={7} />
      </QueryClientProvider>,
    )

    fireEvent.click(screen.getByLabelText("transactions.form.category"))
    fireEvent.click(screen.getByText("🏰 config.category.moat"))

    fireEvent.change(screen.getByLabelText("transactions.form.quantity"), { target: { value: "1" } })
    fireEvent.change(screen.getByLabelText("transactions.form.price"), { target: { value: "10" } })
    fireEvent.change(screen.getByLabelText("transactions.form.total_amount"), { target: { value: "10" } })
    fireEvent.click(screen.getByRole("button", { name: "transactions.form.submit" }))

    expect(mockMutate).toHaveBeenCalled()
    const [payload] = mockMutate.mock.calls[0]
    expect(payload.category).toBe("Moat")
  })

  it("shows auto-radar toast when mutation returns auto_radar true", () => {
    mockMutate.mockImplementationOnce((_payload, opts) => {
      opts?.onSuccess?.({ auto_radar: true })
    })
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultTicker="AAPL" defaultAccountId={7} />
      </QueryClientProvider>,
    )

    fireEvent.change(screen.getByLabelText("transactions.form.quantity"), { target: { value: "1" } })
    fireEvent.change(screen.getByLabelText("transactions.form.price"), { target: { value: "10" } })
    fireEvent.change(screen.getByLabelText("transactions.form.total_amount"), { target: { value: "10" } })
    fireEvent.click(screen.getByRole("button", { name: "transactions.form.submit" }))

    expect(toastInfoMock).toHaveBeenCalledWith("holding.auto_radar")
  })
})
