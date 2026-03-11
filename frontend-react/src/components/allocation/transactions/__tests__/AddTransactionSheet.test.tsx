import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { AddTransactionSheet } from "../AddTransactionSheet"

const mockMutate = vi.fn()

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}))

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

vi.mock("@/api/hooks/useTransactions", () => ({
  useAddTransaction: () => ({ mutate: mockMutate, isPending: false }),
}))

vi.mock("@/api/hooks/useDashboard", () => ({
  useHoldings: () => ({
    data: [{ id: 1, ticker: "AAPL" }],
  }),
}))

describe("AddTransactionSheet", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("validates fx rate and fee before submit", () => {
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AddTransactionSheet open onClose={vi.fn()} defaultTicker="AAPL" />
      </QueryClientProvider>,
    )

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
})
