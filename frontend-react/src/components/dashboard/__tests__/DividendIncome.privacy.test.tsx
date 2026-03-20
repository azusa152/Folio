import { render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { DividendIncome } from "../DividendIncome"
import { usePrivacyMode } from "@/hooks/usePrivacyMode"
import type { EnrichedStock } from "@/api/types/dashboard"
import { makeRebalanceResponse } from "./fixtures"

vi.mock("../InfoPopover", () => ({
  InfoPopover: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="info-popover">{children}</div>
  ),
}))

const rebalance = makeRebalanceResponse({
  total_value: 10000,
  display_currency: "USD",
  holdings_detail: [
    {
      ticker: "AAPL",
      category: "US_Stock",
      quantity: 100,
      market_value: 15000,
      cost_total: 10000,
      weight_pct: 100,
      change_pct: 1,
      currency: "USD",
      current_fx_rate: 1,
      purchase_fx_rate: null,
    },
  ],
})

// Only `ticker` is required by EnrichedStock; all other fields are optional.
const enrichedStocks: EnrichedStock[] = [
  { ticker: "AAPL", dividend: { ytd_dividend_per_share: 2.5 } },
]

describe("DividendIncome privacy", () => {
  beforeEach(() => {
    usePrivacyMode.setState({ isPrivate: false })
  })

  it("shows dollar amount when privacy mode is off", () => {
    render(<DividendIncome rebalance={rebalance} enrichedStocks={enrichedStocks} />)

    expect(screen.getAllByText("$250.00").length).toBeGreaterThanOrEqual(1)
  })

  it("masks dollar amount when privacy mode is on", () => {
    usePrivacyMode.setState({ isPrivate: true })
    render(<DividendIncome rebalance={rebalance} enrichedStocks={enrichedStocks} />)

    const cells = screen.getAllByText("***")
    expect(cells.length).toBeGreaterThanOrEqual(1)
    expect(screen.queryByText("$250.00")).not.toBeInTheDocument()
  })
})
