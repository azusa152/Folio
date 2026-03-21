import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { AccountsTab } from "../AccountsTab"

const mockCreateMutate = vi.fn()
const mockUpdateMutate = vi.fn()
const mockDeactivateMutate = vi.fn()

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) => {
      if (options?.balances) return `${key}:${String(options.balances)}`
      if (typeof options?.count === "number") return `${key}:${String(options.count)}`
      return key
    },
  }),
}))

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

const mockDeleteTransactionMutate = vi.fn()
const mockImportTransactionsMutate = vi.fn()
let mockAllTransactionsData = [
  {
    id: 501,
    user_id: "default",
    account_id: 999,
    holding_id: null,
    ticker: "SPY",
    transaction_type: "BUY",
    quantity: 1,
    price: 500,
    total_amount: 500,
    currency: "USD",
    fx_rate: null,
    fee: 0,
    note: "",
    transaction_date: "2026-03-12",
    created_at: "2026-03-12T10:00:00",
  },
]

vi.mock("@/api/hooks/useTransactions", () => ({
  useTransactions: () => ({
    data: mockAllTransactionsData,
    isLoading: false,
  }),
  useDeleteTransaction: () => ({
    mutate: mockDeleteTransactionMutate,
    isPending: false,
  }),
  useImportTransactions: () => ({
    mutate: mockImportTransactionsMutate,
    isPending: false,
  }),
}))

let mockAccountsData = [
  {
    id: 1,
    name: "IB Main",
    broker: "Interactive Brokers",
    account_type: "brokerage",
    currency: "USD",
  },
]
let mockAccountTransactionsData = [
  {
    id: 99,
    user_id: "default",
    account_id: 1,
    holding_id: null,
    ticker: "MSFT",
    transaction_type: "BUY",
    quantity: 1,
    price: 300,
    total_amount: 300,
    currency: "USD",
    fx_rate: null,
    fee: 0,
    note: "",
    transaction_date: "2026-03-12",
    created_at: "2026-03-12T10:00:00",
  },
]

vi.mock("@/api/hooks/useAccounts", () => ({
  useAccounts: () => ({
    data: mockAccountsData,
    isLoading: false,
  }),
  useAccountSummary: () => ({
    data: [
      {
        account: { id: 1 },
        holdings_count: 2,
        tickers: ["AAPL"],
        cash_balances: [{ currency: "USD", balance: 1200 }],
      },
    ],
  }),
  useAccountPositions: () => ({
    data: [
      {
        id: 11,
        ticker: "AAPL",
        category: "Growth",
        quantity: 2,
        cost_basis: 190,
        is_cash: false,
        currency: "USD",
      },
    ],
    isLoading: false,
  }),
  useAccountTransactions: () => ({
    data: mockAccountTransactionsData,
    isLoading: false,
  }),
  useCreateAccount: () => ({
    mutate: mockCreateMutate,
    isPending: false,
  }),
  useUpdateAccount: () => ({
    mutate: mockUpdateMutate,
    isPending: false,
  }),
  useDeactivateAccount: () => ({
    mutate: mockDeactivateMutate,
    isPending: false,
  }),
}))

describe("AccountsTab", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.unstubAllGlobals()
    mockAccountsData = [
      {
        id: 1,
        name: "IB Main",
        broker: "Interactive Brokers",
        account_type: "brokerage",
        currency: "USD",
      },
    ]
    mockAccountTransactionsData = [
      {
        id: 99,
        user_id: "default",
        account_id: 1,
        holding_id: null,
        ticker: "MSFT",
        transaction_type: "BUY",
        quantity: 1,
        price: 300,
        total_amount: 300,
        currency: "USD",
        fx_rate: null,
        fee: 0,
        note: "",
        transaction_date: "2026-03-12",
        created_at: "2026-03-12T10:00:00",
      },
    ]
    mockAllTransactionsData = [
      {
        id: 501,
        user_id: "default",
        account_id: 999,
        holding_id: null,
        ticker: "SPY",
        transaction_type: "BUY",
        quantity: 1,
        price: 500,
        total_amount: 500,
        currency: "USD",
        fx_rate: null,
        fee: 0,
        note: "",
        transaction_date: "2026-03-12",
        created_at: "2026-03-12T10:00:00",
      },
    ]
  })

  it("renders account summary with cash balances", () => {
    render(<AccountsTab enabled />)
    expect(screen.getByText("accounts.summary.positions:2")).toBeInTheDocument()
    expect(screen.getByText("accounts.summary.cash:USD 1,200")).toBeInTheDocument()
  })

  it("shows selected account detail positions", () => {
    render(<AccountsTab enabled />)
    fireEvent.click(screen.getByRole("button", { name: /IB Main/i }))
    expect(screen.getAllByText("AAPL").length).toBeGreaterThan(0)
  })

  it("renders positions detail columns", () => {
    render(<AccountsTab enabled />)
    expect(screen.getByText("accounts.detail.category")).toBeInTheDocument()
    expect(screen.getByText("accounts.detail.cost_basis")).toBeInTheDocument()
    expect(screen.getByText("config.category.growth")).toBeInTheDocument()
  })

  it("renders transactions sub-tab content", async () => {
    render(<AccountsTab enabled />)
    const transactionsTab = screen.getByRole("tab", { name: "accounts.detail.transactions" })
    fireEvent.mouseDown(transactionsTab)
    fireEvent.click(transactionsTab)

    await waitFor(() => {
      expect(transactionsTab).toHaveAttribute("data-state", "active")
      expect(screen.getByText("transactions.table.date")).toBeInTheDocument()
      expect(screen.getByText("MSFT")).toBeInTheDocument()
    })
  })

  it("shows import/export actions in accounts header", () => {
    render(<AccountsTab enabled />)
    expect(screen.getByRole("button", { name: "transactions.import_button" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "transactions.export_button" })).toBeInTheDocument()
  })

  it("disables export button when selected account has no transactions", () => {
    mockAccountTransactionsData = []
    render(<AccountsTab enabled />)
    expect(screen.getByRole("button", { name: "transactions.export_button" })).toBeDisabled()
  })

  it("exports all transactions when scope is all accounts", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      blob: async () =>
        new Blob(["transaction_date,ticker\n2026-03-12,SPY\n"], { type: "text/csv" }),
      headers: {
        get: () => 'attachment; filename="transactions_20260312.csv"',
      },
    })
    vi.stubGlobal("fetch", fetchMock)

    render(<AccountsTab enabled />)
    fireEvent.change(screen.getByLabelText("transactions.filter.account"), {
      target: { value: "all" },
    })
    fireEvent.click(screen.getByRole("button", { name: "transactions.export_button" }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/transactions/export-csv",
        expect.objectContaining({ headers: expect.any(Object) }),
      )
    })
  })

  it("calls export endpoint for selected account", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      blob: async () =>
        new Blob(["transaction_date,ticker\n2026-03-12,MSFT\n"], { type: "text/csv" }),
      headers: {
        get: () => 'attachment; filename="transactions_20260312.csv"',
      },
    })
    vi.stubGlobal("fetch", fetchMock)

    render(<AccountsTab enabled />)
    fireEvent.click(screen.getByRole("button", { name: "transactions.export_button" }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/transactions/export-csv?account_id=1",
        expect.objectContaining({ headers: expect.any(Object) }),
      )
    })
  })

  it("renders summary sub-tab content", () => {
    render(<AccountsTab enabled />)
    fireEvent.click(screen.getByRole("tab", { name: "accounts.detail.summary" }))
    expect(screen.getAllByText("accounts.summary.positions:2").length).toBeGreaterThan(0)
    expect(screen.getAllByText("accounts.summary.cash:USD 1,200").length).toBeGreaterThan(0)
  })

  it("shows no-accounts empty description", () => {
    mockAccountsData = []
    render(<AccountsTab enabled />)
    expect(screen.getByText("accounts.empty.description")).toBeInTheDocument()
  })

  it("highlights fallback account when selected account is removed", () => {
    mockAccountsData = [
      {
        id: 1,
        name: "IB Main",
        broker: "Interactive Brokers",
        account_type: "brokerage",
        currency: "USD",
      },
      { id: 2, name: "SBI Sub", broker: "SBI", account_type: "brokerage", currency: "JPY" },
    ]
    const { rerender } = render(<AccountsTab enabled />)

    fireEvent.click(screen.getByRole("button", { name: /SBI Sub/i }))

    mockAccountsData = [
      {
        id: 1,
        name: "IB Main",
        broker: "Interactive Brokers",
        account_type: "brokerage",
        currency: "USD",
      },
    ]
    rerender(<AccountsTab enabled />)

    const ibButton = screen.getByRole("button", { name: /IB Main/i })
    const ibCard = ibButton.closest("div.rounded-md.border")
    expect(ibCard).toHaveClass("border-primary")
  })

  it("creates account with required payload", () => {
    render(<AccountsTab enabled />)

    fireEvent.click(screen.getByRole("button", { name: "accounts.add" }))
    fireEvent.change(screen.getByLabelText("accounts.form.name"), {
      target: { value: "Japan Account" },
    })
    fireEvent.change(screen.getByLabelText("accounts.form.broker"), { target: { value: "SBI" } })
    fireEvent.change(screen.getByLabelText("accounts.form.currency"), { target: { value: "jpy" } })
    fireEvent.click(screen.getByRole("button", { name: "accounts.form.save" }))

    expect(mockCreateMutate).toHaveBeenCalledWith(
      expect.objectContaining({
        name: "Japan Account",
        broker: "SBI",
        currency: "JPY",
      }),
      expect.any(Object),
    )
  })
})
