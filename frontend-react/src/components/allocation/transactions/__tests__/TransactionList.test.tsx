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
        transactions={[
          {
            id: 42,
            user_id: "default",
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
          },
        ]}
      />,
    )

    fireEvent.click(screen.getByRole("button", { name: "transactions.table.delete" }))
    fireEvent.click(screen.getByRole("button", { name: "common.confirm" }))
    expect(mockDeleteMutate).toHaveBeenCalledWith(42, expect.any(Object))
  })
})
