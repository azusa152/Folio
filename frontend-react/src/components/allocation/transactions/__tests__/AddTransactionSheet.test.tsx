import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { AddTransactionSheet } from "../AddTransactionSheet"

const { mockMutate, toastSuccessMock, toastErrorMock, toastInfoMock, radarState, wrapperState, accountState } = vi.hoisted(() => ({
  mockMutate: vi.fn(),
  toastSuccessMock: vi.fn(),
  toastErrorMock: vi.fn(),
  toastInfoMock: vi.fn(),
  radarState: {
    stocks: [] as Array<{ ticker: string }>,
    isLoading: false,
  },
  wrapperState: {
    eligibleItems: [] as Array<{ ticker: string; fund_name: string; asset_type?: string; trust_fee_pct?: number }>,
    eligibility: undefined as
      | {
          ticker: string
          wrapper: string
          eligible: boolean
          reasons: string[]
          suggested_wrapper?: string
          asset_type?: string
        }
      | undefined,
    quota: undefined as
      | {
          year: number
          as_of: string
          restoration_policy: string
          quotas: Record<
            string,
            {
              wrapper_annual_remaining: number
              wrapper_annual_used: number
            }
          >
        }
      | undefined,
  },
  accountState: {
    accounts: [{ id: 7, name: "IB Main", broker: "Interactive Brokers", tax_wrapper: "tokutei" }],
    balances: [{ currency: "USD", balance: 500 }],
    sellablePositionsError: false,
    sellablePositions: [] as Array<{
      ticker: string
      fund_name: string
      quantity: number
      cost_basis?: number | null
      current_price?: number | null
      market_value?: number | null
      currency: string
      value_source?: "live_price" | "cost_basis" | "unavailable"
    }>,
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
    data: accountState.accounts,
  }),
  useAccountCashBalances: () => ({
    data: accountState.balances,
  }),
  useAccountSellablePositions: () => ({
    data: accountState.sellablePositions,
    isLoading: false,
    isError: accountState.sellablePositionsError,
  }),
}))

vi.mock("@/api/hooks/useWrappers", () => ({
  useWrapperEligibility: () => ({ data: wrapperState.eligibility, isLoading: false }),
  useSuggestRouting: () => ({ data: undefined, isLoading: false }),
  useEligibleAssets: (_wrapper: string | null | undefined, options?: { assetType?: string; enabled?: boolean }) => {
    const enabled = options?.enabled !== false
    const items = enabled
      ? options?.assetType
        ? wrapperState.eligibleItems.filter((item) => item.asset_type === options.assetType)
        : wrapperState.eligibleItems
      : []
    return {
      data: { items },
      isLoading: false,
      isFetched: enabled,
    }
  },
  useWrapperQuota: () => ({ data: wrapperState.quota, isLoading: false }),
}))

vi.mock("@/hooks/use-mobile", () => ({
  useIsMobile: () => false,
}))

describe("AddTransactionSheet", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    radarState.stocks = []
    radarState.isLoading = false
    wrapperState.eligibleItems = []
    wrapperState.eligibility = undefined
    wrapperState.quota = undefined
    accountState.accounts = [{ id: 7, name: "IB Main", broker: "Interactive Brokers", tax_wrapper: "tokutei" }]
    accountState.balances = [{ currency: "USD", balance: 500 }]
    accountState.sellablePositionsError = false
    accountState.sellablePositions = []
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

  it("forces category to Mutual_Fund for tsumitate accounts", () => {
    accountState.accounts = [{ id: 7, name: "IB NISA", broker: "SBI", tax_wrapper: "nisa_tsumitate" }]
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultTicker="01312179" defaultAccountId={7} />
      </QueryClientProvider>,
    )

    const categorySelect = screen.getByLabelText("transactions.form.category")
    expect(categorySelect).toBeDisabled()
    expect(screen.getByText("transactions.form.mutual_fund_category_hint")).toBeInTheDocument()
  })

  it("forces category to Mutual_Fund for growth mutual fund eligibility", () => {
    accountState.accounts = [{ id: 7, name: "IB NISA", broker: "SBI", tax_wrapper: "nisa_growth" }]
    wrapperState.eligibility = {
      ticker: "01312179",
      wrapper: "nisa_growth",
      eligible: true,
      reasons: [],
      asset_type: "mutual_fund",
    }

    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultTicker="01312179" defaultAccountId={7} />
      </QueryClientProvider>,
    )

    fireEvent.change(screen.getByLabelText("transactions.form.quantity"), { target: { value: "1" } })
    fireEvent.change(screen.getByLabelText("transactions.form.price"), { target: { value: "10" } })
    fireEvent.change(screen.getByLabelText("transactions.form.total_amount"), { target: { value: "10" } })
    fireEvent.click(screen.getByRole("button", { name: "transactions.form.submit" }))

    expect(mockMutate).toHaveBeenCalled()
    const [payload] = mockMutate.mock.calls[0]
    expect(payload.category).toBe("Mutual_Fund")
  })

  it("shows NISA quota summary during buy flow", () => {
    accountState.accounts = [{ id: 7, name: "IB NISA", broker: "SBI", tax_wrapper: "nisa_growth" }]
    wrapperState.quota = {
      year: 2026,
      as_of: "2026-03-18",
      restoration_policy: "next_year",
      quotas: {
        nisa_growth: {
          wrapper_annual_remaining: 1_800_000,
          wrapper_annual_used: 600_000,
        },
      },
    }
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultTicker="AAPL" defaultAccountId={7} />
      </QueryClientProvider>,
    )

    expect(screen.getByText("transactions.form.nisa_quota_summary")).toBeInTheDocument()
  })

  it("keeps displaying selected tsumitate fund name and ticker in the trigger", () => {
    accountState.accounts = [{ id: 7, name: "Tsumitate", broker: "SBI", tax_wrapper: "nisa_tsumitate" }]
    accountState.balances = [{ currency: "JPY", balance: 500_000 }]
    wrapperState.eligibleItems = [
      {
        ticker: "01311143",
        fund_name: "野村インデックスファンド・JPX日経400",
        trust_fee_pct: 0.198,
      },
    ]

    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultAccountId={7} />
      </QueryClientProvider>,
    )

    const [, nisaPickerTrigger] = screen.getAllByRole("combobox")
    fireEvent.click(nisaPickerTrigger)
    fireEvent.click(screen.getByText("野村インデックスファンド・JPX日経400"))

    expect(screen.getByText("野村インデックスファンド・JPX日経400")).toBeInTheDocument()
    expect(screen.getByText("01311143 · eligibility.nisa_trust_fee_label: 0.198%")).toBeInTheDocument()
    expect(screen.queryByText("eligibility.nisa_picker_placeholder")).not.toBeInTheDocument()
  })

  it("shows NISA picker for growth account buy", () => {
    accountState.accounts = [{ id: 7, name: "Growth", broker: "SBI", tax_wrapper: "nisa_growth" }]
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultAccountId={7} />
      </QueryClientProvider>,
    )

    expect(screen.queryByLabelText("transactions.form.ticker")).not.toBeInTheDocument()
    expect(screen.getAllByRole("combobox").length).toBeGreaterThan(1)
  })

  it("shows asset type chips for growth nisa before opening picker", () => {
    accountState.accounts = [{ id: 7, name: "Growth", broker: "SBI", tax_wrapper: "nisa_growth" }]
    wrapperState.eligibleItems = [
      { ticker: "2558.T", fund_name: "MAXIS 米国株式", asset_type: "etf" },
      { ticker: "03311187", fund_name: "eMAXIS Slim 米国株式", asset_type: "mutual_fund", trust_fee_pct: 0.0814 },
    ]
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultAccountId={7} />
      </QueryClientProvider>,
    )

    expect(screen.getByRole("button", { name: "nisa.eligible.asset_type.etf" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "nisa.eligible.asset_type.mutual_fund" })).toBeInTheDocument()
  })

  it("narrows growth nisa picker results after selecting asset type", () => {
    accountState.accounts = [{ id: 7, name: "Growth", broker: "SBI", tax_wrapper: "nisa_growth" }]
    wrapperState.eligibleItems = [
      { ticker: "2558.T", fund_name: "MAXIS 米国株式", asset_type: "etf" },
      { ticker: "03311187", fund_name: "eMAXIS Slim 米国株式", asset_type: "mutual_fund", trust_fee_pct: 0.0814 },
    ]
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultAccountId={7} />
      </QueryClientProvider>,
    )

    fireEvent.click(screen.getByRole("button", { name: "nisa.eligible.asset_type.etf" }))
    const [, nisaPickerTrigger] = screen.getAllByRole("combobox")
    fireEvent.click(nisaPickerTrigger)
    expect(screen.getByText("MAXIS 米国株式")).toBeInTheDocument()
    expect(screen.queryByText("eMAXIS Slim 米国株式")).not.toBeInTheDocument()
  })

  it("falls back to ticker input when growth nisa listed filter is selected (stock)", () => {
    accountState.accounts = [{ id: 7, name: "Growth", broker: "SBI", tax_wrapper: "nisa_growth" }]
    wrapperState.eligibleItems = [{ ticker: "2558.T", fund_name: "MAXIS 米国株式", asset_type: "etf" }]
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultAccountId={7} />
      </QueryClientProvider>,
    )

    fireEvent.click(screen.getByRole("button", { name: "nisa.eligible.asset_type.stock" }))
    const tickerInput = screen.getByLabelText("transactions.form.ticker") as HTMLInputElement
    fireEvent.change(tickerInput, { target: { value: "7203.t" } })

    expect(tickerInput.value).toBe("7203.T")
    expect(screen.getByText("nisa.eligible.listed_input_hint")).toBeInTheDocument()
    expect(screen.queryByText("eligibility.nisa_picker_placeholder")).not.toBeInTheDocument()
  })

  it("auto-appends .T on blur when user types a bare 4-digit jp code in listed mode", () => {
    accountState.accounts = [{ id: 7, name: "Growth", broker: "SBI", tax_wrapper: "nisa_growth" }]
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultAccountId={7} />
      </QueryClientProvider>,
    )

    fireEvent.click(screen.getByRole("button", { name: "nisa.eligible.asset_type.stock" }))
    const tickerInput = screen.getByLabelText("transactions.form.ticker") as HTMLInputElement

    fireEvent.change(tickerInput, { target: { value: "7203" } })
    expect(tickerInput.value).toBe("7203")

    fireEvent.blur(tickerInput)
    expect(tickerInput.value).toBe("7203.T")
  })

  it("does not append .T on blur when input is not a bare 4-digit code", () => {
    accountState.accounts = [{ id: 7, name: "Growth", broker: "SBI", tax_wrapper: "nisa_growth" }]
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultAccountId={7} />
      </QueryClientProvider>,
    )

    fireEvent.click(screen.getByRole("button", { name: "nisa.eligible.asset_type.stock" }))
    const tickerInput = screen.getByLabelText("transactions.form.ticker") as HTMLInputElement

    fireEvent.change(tickerInput, { target: { value: "7203.T" } })
    fireEvent.blur(tickerInput)
    expect(tickerInput.value).toBe("7203.T")
  })

  it("shows eligibility disclaimer and suppresses generic growth hint in listed mode", () => {
    accountState.accounts = [{ id: 7, name: "Growth", broker: "SBI", tax_wrapper: "nisa_growth" }]
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultAccountId={7} />
      </QueryClientProvider>,
    )

    fireEvent.click(screen.getByRole("button", { name: "nisa.eligible.asset_type.stock" }))

    expect(screen.getByText("nisa.eligible.listed_eligibility_disclaimer")).toBeInTheDocument()
    expect(screen.queryByText("eligibility.nisa_picker_hint_growth")).not.toBeInTheDocument()
  })

  it("falls back to ticker input when growth nisa listed filter is selected (reit)", () => {
    accountState.accounts = [{ id: 7, name: "Growth", broker: "SBI", tax_wrapper: "nisa_growth" }]
    wrapperState.eligibleItems = [{ ticker: "2558.T", fund_name: "MAXIS 米国株式", asset_type: "etf" }]
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultAccountId={7} />
      </QueryClientProvider>,
    )

    fireEvent.click(screen.getByRole("button", { name: "nisa.eligible.asset_type.reit" }))
    const tickerInput = screen.getByLabelText("transactions.form.ticker") as HTMLInputElement
    fireEvent.change(tickerInput, { target: { value: "8951" } })
    fireEvent.blur(tickerInput)

    expect(tickerInput.value).toBe("8951.T")
    expect(screen.getByText("nisa.eligible.listed_input_hint")).toBeInTheDocument()
    expect(screen.getByText("nisa.eligible.listed_eligibility_disclaimer")).toBeInTheDocument()
    expect(screen.queryByText("eligibility.nisa_picker_hint_growth")).not.toBeInTheDocument()
  })

  it("shows picker for reit when curated reit data exists", () => {
    accountState.accounts = [{ id: 7, name: "Growth", broker: "SBI", tax_wrapper: "nisa_growth" }]
    wrapperState.eligibleItems = [
      { ticker: "2556.T", fund_name: "One ETF 東証REIT指数", asset_type: "reit" },
      { ticker: "2558.T", fund_name: "MAXIS 米国株式", asset_type: "etf" },
    ]
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultAccountId={7} />
      </QueryClientProvider>,
    )

    fireEvent.click(screen.getByRole("button", { name: "nisa.eligible.asset_type.reit" }))

    // The picker combobox should be visible (not the free-text fallback)
    expect(screen.queryByLabelText("transactions.form.ticker")).not.toBeInTheDocument()
    expect(screen.queryByText("nisa.eligible.listed_input_hint")).not.toBeInTheDocument()
  })

  it("falls back to free-text for reit when no curated reit data exists", () => {
    accountState.accounts = [{ id: 7, name: "Growth", broker: "SBI", tax_wrapper: "nisa_growth" }]
    // Only ETF data — no REIT entries
    wrapperState.eligibleItems = [{ ticker: "2558.T", fund_name: "MAXIS 米国株式", asset_type: "etf" }]
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultAccountId={7} />
      </QueryClientProvider>,
    )

    fireEvent.click(screen.getByRole("button", { name: "nisa.eligible.asset_type.reit" }))

    // Query is fetched and returns 0 REIT items → free-text fallback
    const tickerInput = screen.getByLabelText("transactions.form.ticker") as HTMLInputElement
    expect(tickerInput).toBeInTheDocument()
    expect(screen.getByText("nisa.eligible.listed_input_hint")).toBeInTheDocument()
    expect(screen.getByText("nisa.eligible.listed_eligibility_disclaimer")).toBeInTheDocument()
  })

  it("nfkc-normalizes full-width jp digits to ascii on change", () => {
    accountState.accounts = [{ id: 7, name: "Growth", broker: "SBI", tax_wrapper: "nisa_growth" }]
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultAccountId={7} />
      </QueryClientProvider>,
    )

    fireEvent.click(screen.getByRole("button", { name: "nisa.eligible.asset_type.stock" }))
    const tickerInput = screen.getByLabelText("transactions.form.ticker") as HTMLInputElement

    // Simulate IME full-width digit input
    fireEvent.change(tickerInput, { target: { value: "８９５１" } })

    // NFKC + toUpperCase should produce ASCII
    expect(tickerInput.value).toBe("8951")

    fireEvent.blur(tickerInput)
    expect(tickerInput.value).toBe("8951.T")
  })

  it("shows selected growth asset type badge in picker trigger", () => {
    accountState.accounts = [{ id: 7, name: "Growth", broker: "SBI", tax_wrapper: "nisa_growth" }]
    wrapperState.eligibleItems = [
      { ticker: "2558.T", fund_name: "MAXIS 米国株式", asset_type: "etf" },
    ]
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultAccountId={7} />
      </QueryClientProvider>,
    )

    const [, nisaPickerTrigger] = screen.getAllByRole("combobox")
    fireEvent.click(nisaPickerTrigger)
    fireEvent.click(screen.getByText("MAXIS 米国株式"))

    expect(screen.getAllByText("nisa.eligible.asset_type.etf").length).toBeGreaterThan(0)
  })

  it("shows holding picker for sell when account selected", () => {
    accountState.sellablePositions = [
      {
        ticker: "AAPL",
        fund_name: "Apple Inc.",
        quantity: 12,
        current_price: 200,
        market_value: 2400,
        currency: "USD",
      },
    ]
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultAccountId={7} />
      </QueryClientProvider>,
    )

    fireEvent.click(screen.getByRole("button", { name: "transactions.type.sell" }))
    expect(screen.queryByLabelText("transactions.form.ticker")).not.toBeInTheDocument()
    expect(screen.getByText("transactions.sell_picker.placeholder")).toBeInTheDocument()
  })

  it("shows holding picker for dividend when account selected", () => {
    accountState.sellablePositions = [
      {
        ticker: "AAPL",
        fund_name: "Apple Inc.",
        quantity: 8,
        current_price: 200,
        market_value: 1600,
        currency: "USD",
      },
    ]
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultAccountId={7} />
      </QueryClientProvider>,
    )

    fireEvent.click(screen.getByRole("button", { name: "transactions.type.dividend" }))
    expect(screen.queryByLabelText("transactions.form.ticker")).not.toBeInTheDocument()
    expect(screen.getByText("transactions.sell_picker.placeholder_dividend")).toBeInTheDocument()
  })

  it("auto-fills ticker on sell holding selection", () => {
    accountState.sellablePositions = [
      {
        ticker: "MSFT",
        fund_name: "Microsoft Corp.",
        quantity: 3,
        current_price: 300,
        market_value: 900,
        currency: "USD",
      },
    ]
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultAccountId={7} />
      </QueryClientProvider>,
    )

    fireEvent.click(screen.getByRole("button", { name: "transactions.type.sell" }))
    const [, sellPickerTrigger] = screen.getAllByRole("combobox")
    fireEvent.click(sellPickerTrigger)
    fireEvent.click(screen.getByText("Microsoft Corp."))

    expect(screen.getByText("Microsoft Corp.")).toBeInTheDocument()
    expect(screen.getByText("MSFT · 3")).toBeInTheDocument()
  })

  it("shows empty state when no sellable holdings", () => {
    accountState.sellablePositions = []
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultAccountId={7} />
      </QueryClientProvider>,
    )

    fireEvent.click(screen.getByRole("button", { name: "transactions.type.sell" }))
    const [, sellPickerTrigger] = screen.getAllByRole("combobox")
    fireEvent.click(sellPickerTrigger)
    expect(screen.getByText("transactions.sell_picker.empty")).toBeInTheDocument()
  })

  it("shows load error state when sellable positions query fails", () => {
    accountState.sellablePositionsError = true
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultAccountId={7} />
      </QueryClientProvider>,
    )

    fireEvent.click(screen.getByRole("button", { name: "transactions.type.sell" }))
    const [, sellPickerTrigger] = screen.getAllByRole("combobox")
    fireEvent.click(sellPickerTrigger)
    expect(screen.getByText("transactions.sell_picker.load_error")).toBeInTheDocument()
  })

  it("falls back to plain ticker input for sell when account is not selected", () => {
    accountState.sellablePositions = [
      {
        ticker: "AAPL",
        fund_name: "Apple Inc.",
        quantity: 1,
        current_price: 200,
        market_value: 200,
        currency: "USD",
      },
    ]
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} />
      </QueryClientProvider>,
    )

    fireEvent.click(screen.getByRole("button", { name: "transactions.type.sell" }))
    expect(screen.getByLabelText("transactions.form.ticker")).toBeInTheDocument()
  })

  it("applies max quantity from selected sell position", () => {
    accountState.sellablePositions = [
      {
        ticker: "AAPL",
        fund_name: "Apple Inc.",
        quantity: 5,
        current_price: 200,
        market_value: 1000,
        currency: "USD",
      },
    ]
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultAccountId={7} />
      </QueryClientProvider>,
    )

    fireEvent.click(screen.getByRole("button", { name: "transactions.type.sell" }))
    const [, sellPickerTrigger] = screen.getAllByRole("combobox")
    fireEvent.click(sellPickerTrigger)
    fireEvent.click(screen.getByText("Apple Inc."))
    fireEvent.click(screen.getByRole("button", { name: "transactions.sell_picker.max" }))
    expect((screen.getByLabelText("transactions.form.quantity") as HTMLInputElement).value).toBe("5")
  })

  it("shows cost_basis value source label when price is based on cost", () => {
    accountState.sellablePositions = [
      {
        ticker: "AAPL",
        fund_name: "Apple Inc.",
        quantity: 2,
        cost_basis: 150,
        current_price: null,
        market_value: 300,
        currency: "USD",
        value_source: "cost_basis",
      },
    ]
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultAccountId={7} />
      </QueryClientProvider>,
    )

    fireEvent.click(screen.getByRole("button", { name: "transactions.type.sell" }))
    const [, sellPickerTrigger] = screen.getAllByRole("combobox")
    fireEvent.click(sellPickerTrigger)
    expect(screen.getByText("transactions.sell_picker.value_source_cost_basis")).toBeInTheDocument()
  })

  it("shows cost_basis value source on selected trigger", () => {
    accountState.sellablePositions = [
      {
        ticker: "AAPL",
        fund_name: "Apple Inc.",
        quantity: 2,
        cost_basis: 150,
        current_price: null,
        market_value: 300,
        currency: "USD",
        value_source: "cost_basis",
      },
    ]
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultAccountId={7} />
      </QueryClientProvider>,
    )

    fireEvent.click(screen.getByRole("button", { name: "transactions.type.sell" }))
    const [, sellPickerTrigger] = screen.getAllByRole("combobox")
    fireEvent.click(sellPickerTrigger)
    fireEvent.click(screen.getByText("Apple Inc."))
    expect(screen.getByText("transactions.sell_picker.value_source_cost_basis")).toBeInTheDocument()
  })

  it("shows live_price value source without extra label", () => {
    accountState.sellablePositions = [
      {
        ticker: "MSFT",
        fund_name: "Microsoft Corp.",
        quantity: 1,
        cost_basis: 200,
        current_price: 310,
        market_value: 310,
        currency: "USD",
        value_source: "live_price",
      },
    ]
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultAccountId={7} />
      </QueryClientProvider>,
    )

    fireEvent.click(screen.getByRole("button", { name: "transactions.type.sell" }))
    const [, sellPickerTrigger] = screen.getAllByRole("combobox")
    fireEvent.click(sellPickerTrigger)
    // live_price items should NOT show any value source label
    expect(screen.queryByText("transactions.sell_picker.value_source_live")).not.toBeInTheDocument()
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
    fireEvent.click(screen.getByText("config.category.moat"))

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
