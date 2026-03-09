import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { TopHoldings } from "../TopHoldings"
import { usePrivacyMode } from "@/hooks/usePrivacyMode"
import type { RebalanceResponse } from "@/api/types/dashboard"

vi.mock("@/hooks/useTerminology", () => ({
  useTerminology: () => ({
    term: (key: string, fallback?: string) => fallback ?? key,
    isSimplified: false,
  }),
}))

const rebalance: RebalanceResponse = {
  total_value: 10000,
  display_currency: "USD",
  advice: [],
  holdings_detail: [
    {
      ticker: "AAPL",
      category: "US_Stock",
      quantity: 10,
      market_value: 1500,
      cost_total: 1000,
      weight_pct: 15,
      change_pct: 2.5,
      currency: "USD",
      current_fx_rate: 1,
      purchase_fx_rate: null,
    },
  ],
} as unknown as RebalanceResponse

describe("TopHoldings privacy", () => {
  beforeEach(() => {
    usePrivacyMode.setState({ isPrivate: false })
  })

  it("shows dollar amounts when privacy mode is off", () => {
    render(
      <MemoryRouter>
        <TopHoldings rebalance={rebalance} />
      </MemoryRouter>,
    )

    expect(screen.getByText("$1,500.00")).toBeInTheDocument()
  })

  it("masks dollar amounts when privacy mode is on", () => {
    usePrivacyMode.setState({ isPrivate: true })
    render(
      <MemoryRouter>
        <TopHoldings rebalance={rebalance} />
      </MemoryRouter>,
    )

    const cells = screen.getAllByText("***")
    expect(cells.length).toBeGreaterThanOrEqual(2)
    expect(screen.queryByText("$1,500.00")).not.toBeInTheDocument()
  })

  it("does not leak gain/loss sign in privacy mode", () => {
    usePrivacyMode.setState({ isPrivate: true })
    render(
      <MemoryRouter>
        <TopHoldings rebalance={rebalance} />
      </MemoryRouter>,
    )

    expect(screen.queryByText(/\+\*\*\*/)).not.toBeInTheDocument()
    expect(screen.queryByText(/-\*\*\*/)).not.toBeInTheDocument()
  })
})
