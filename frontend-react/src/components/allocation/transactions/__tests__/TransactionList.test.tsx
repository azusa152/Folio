import { fireEvent, render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { TransactionList } from "../TransactionList"

const mockDeleteMutate = vi.fn()

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}))

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

vi.mock("@/api/hooks/useTransactions", () => ({
  useDeleteTransaction: () => ({
    mutate: mockDeleteMutate,
    isPending: false,
  }),
}))

describe("TransactionList", () => {
  it("confirms delete and calls mutation", () => {
    render(
      <TransactionList
        isLoading={false}
        accounts={[{ id: 10, name: "IB Main", broker: "IB" } as never]}
        transactions={[
          {
            id: 42,
            user_id: "default",
            account_id: 10,
            ticker: "AAPL",
            transaction_type: "BUY",
            quantity: 2,
            price: 100,
            total_amount: 200,
            currency: "USD",
            fx_rate: null,
            fee: 0,
            note: "",
            transaction_date: "2026-03-10",
            created_at: "2026-03-10T00:00:00Z",
            holding_id: 1,
            auto_radar: false,
          },
        ]}
      />,
    )

    fireEvent.click(screen.getByRole("button", { name: "transactions.table.delete" }))
    fireEvent.click(screen.getByRole("button", { name: "common.confirm" }))
    expect(mockDeleteMutate).toHaveBeenCalledWith(42, expect.any(Object))
  })

  it("shows non-zero tiny quantities without collapsing to 0.00", () => {
    render(
      <TransactionList
        isLoading={false}
        accounts={[{ id: 10, name: "IB Main", broker: "IB" } as never]}
        transactions={[
          {
            id: 43,
            user_id: "default",
            account_id: 10,
            ticker: "ETH-USD",
            transaction_type: "BUY",
            quantity: 0.00012345,
            price: 2000,
            total_amount: 0.2469,
            currency: "USD",
            fx_rate: null,
            fee: 0,
            note: "",
            transaction_date: "2026-03-11",
            created_at: "2026-03-11T00:00:00Z",
            holding_id: 2,
            auto_radar: false,
          },
        ]}
      />,
    )

    expect(screen.getByText("0.00012345")).toBeInTheDocument()
    expect(screen.queryByText("0.00")).not.toBeInTheDocument()
  })

  it("renders currency symbols for price and total", () => {
    render(
      <TransactionList
        isLoading={false}
        accounts={[{ id: 10, name: "IB Main", broker: "IB" } as never]}
        transactions={[
          {
            id: 44,
            user_id: "default",
            account_id: 10,
            ticker: "7203.T",
            transaction_type: "BUY",
            quantity: 1,
            price: 1234,
            total_amount: 1234,
            currency: "JPY",
            fx_rate: null,
            fee: 0,
            note: "",
            transaction_date: "2026-03-11",
            created_at: "2026-03-11T00:00:00Z",
            holding_id: 3,
            auto_radar: false,
          },
        ]}
      />,
    )

    expect(screen.getAllByText(/¥/).length).toBeGreaterThanOrEqual(2)
  })
})
