import { render, screen, within } from "@testing-library/react"
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
      category: "Trend_Setter",
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

  it("aggregates duplicate tickers and shows translated category labels", () => {
    const withDuplicateTicker = {
      ...rebalance,
      holdings_detail: [
        {
          ticker: "VTI",
          category: "Trend_Setter",
          quantity: 10,
          market_value: 1000,
          cost_total: 900,
          weight_pct: 10,
          change_pct: 1.2,
          currency: "USD",
          current_fx_rate: 1,
          purchase_fx_rate: null,
        },
        {
          ticker: "VTI",
          category: "Trend_Setter",
          quantity: 20,
          market_value: 2000,
          cost_total: 1700,
          weight_pct: 20,
          change_pct: 0.8,
          currency: "USD",
          current_fx_rate: 1,
          purchase_fx_rate: null,
        },
      ],
    } as unknown as RebalanceResponse

    render(
      <MemoryRouter>
        <TopHoldings rebalance={withDuplicateTicker} />
      </MemoryRouter>,
    )

    expect(screen.queryByText("Trend_Setter")).not.toBeInTheDocument()

    const rows = screen.getAllByRole("row")
    const vtiRow = rows.find((row) => within(row).queryByText("VTI"))
    expect(vtiRow).toBeDefined()
    expect(vtiRow?.textContent).toContain("config.category.trend_setter")
    expect(within(vtiRow!).getByText("30.0%")).toBeInTheDocument()
  })
})
