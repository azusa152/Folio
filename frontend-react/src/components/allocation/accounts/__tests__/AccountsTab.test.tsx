import { fireEvent, render, screen } from "@testing-library/react"
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

vi.mock("@/api/hooks/useAccounts", () => ({
  useAccounts: () => ({
    data: [{ id: 1, name: "IB Main", broker: "Interactive Brokers", account_type: "brokerage", currency: "USD" }],
    isLoading: false,
  }),
  useAccountSummary: () => ({
    data: [{ account: { id: 1 }, holdings_count: 2, tickers: ["AAPL"], cash_balances: [{ currency: "USD", balance: 1200 }] }],
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
  })

  it("renders account summary with cash balances", () => {
    render(<AccountsTab enabled />)
    expect(screen.getByText("accounts.summary.positions:2")).toBeInTheDocument()
    expect(screen.getByText("accounts.summary.cash:USD 1,200")).toBeInTheDocument()
  })

  it("creates account with required payload", () => {
    render(<AccountsTab enabled />)

    fireEvent.click(screen.getByRole("button", { name: "accounts.add" }))
    fireEvent.change(screen.getByLabelText("accounts.form.name"), { target: { value: "Japan Account" } })
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
