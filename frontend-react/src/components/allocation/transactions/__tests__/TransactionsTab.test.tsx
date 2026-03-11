import { fireEvent, render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { TransactionsTab } from "../TransactionsTab"

const mockUseTransactions = vi.fn()

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}))

vi.mock("@/api/hooks/useTransactions", () => ({
  useTransactions: (params: unknown) => mockUseTransactions(params),
}))

vi.mock("@/api/hooks/useDashboard", () => ({
  useHoldings: () => ({
    data: [{ ticker: "AAPL" }, { ticker: "MSFT" }],
  }),
}))

vi.mock("@/api/hooks/useAccounts", () => ({
  useAccounts: () => ({
    data: [{ id: 1, name: "IB Main" }],
  }),
}))

vi.mock("../TransactionList", () => ({
  TransactionList: () => <div>transaction-list</div>,
}))

describe("TransactionsTab", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseTransactions.mockReturnValue({ data: [], isLoading: false })
  })

  it("passes ticker filter to useTransactions", () => {
    render(<TransactionsTab enabled onRecordTransaction={vi.fn()} />)

    expect(mockUseTransactions).toHaveBeenLastCalledWith({
      ticker: undefined,
      accountId: undefined,
      enabled: true,
      limit: 500,
    })

    fireEvent.change(screen.getByLabelText("transactions.filter.ticker"), {
      target: { value: "AAPL" },
    })

    expect(mockUseTransactions).toHaveBeenLastCalledWith({
      ticker: "AAPL",
      accountId: undefined,
      enabled: true,
      limit: 500,
    })
  })

  it("passes account filter to useTransactions", () => {
    render(<TransactionsTab enabled onRecordTransaction={vi.fn()} />)

    fireEvent.change(screen.getByLabelText("transactions.filter.account"), {
      target: { value: "1" },
    })

    expect(mockUseTransactions).toHaveBeenLastCalledWith({
      ticker: undefined,
      accountId: 1,
      enabled: true,
      limit: 500,
    })
  })
})
