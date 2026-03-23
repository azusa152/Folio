import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it } from "vitest"
import { HoldingBreakdown } from "../HoldingBreakdown"
import type { RebalanceResponse } from "@/api/types/dashboard"

function makeHolding(ticker: string, category: string, weight_pct: number) {
  return {
    ticker,
    category,
    currency: "USD",
    quantity: 10,
    market_value: weight_pct * 100,
    weight_pct,
  }
}

function makeRebalance(holdings: ReturnType<typeof makeHolding>[]): Partial<RebalanceResponse> {
  return { holdings_detail: holdings } as Partial<RebalanceResponse>
}

describe("HoldingBreakdown", () => {
  it("renders nothing when rebalance is null", () => {
    const { container } = render(<HoldingBreakdown rebalance={null} />)
    expect(container.innerHTML).toBe("")
  })

  it("renders nothing when holdings_detail is empty", () => {
    const { container } = render(
      <HoldingBreakdown rebalance={makeRebalance([]) as RebalanceResponse} />,
    )
    expect(container.innerHTML).toBe("")
  })

  it("renders skeleton when loading", () => {
    render(<HoldingBreakdown isLoading />)
    expect(
      document.querySelectorAll("[class*='animate-pulse'], [data-slot='skeleton']").length,
    ).toBeGreaterThan(0)
  })

  it("renders holdings sorted by weight descending", () => {
    const rebalance = makeRebalance([
      makeHolding("SMALL", "Growth", 5),
      makeHolding("BIG", "Trend Setter", 30),
      makeHolding("MID", "Moat", 15),
    ])

    render(<HoldingBreakdown rebalance={rebalance as RebalanceResponse} />)

    const percentages = screen.getAllByText(/\d+\.\d%/)
    expect(percentages[0].textContent).toBe("30.0%")
    expect(percentages[1].textContent).toBe("15.0%")
    expect(percentages[2].textContent).toBe("5.0%")
  })

  it("filters out zero-weight holdings", () => {
    const rebalance = makeRebalance([
      makeHolding("GOOD", "Growth", 50),
      makeHolding("ZERO", "Moat", 0),
    ])

    render(<HoldingBreakdown rebalance={rebalance as RebalanceResponse} />)

    expect(screen.getByText(/GOOD/)).toBeInTheDocument()
    expect(screen.queryByText(/ZERO/)).not.toBeInTheDocument()
  })

  it("shows Other bucket and expand button when more than 8 holdings", () => {
    const holdings = Array.from({ length: 10 }, (_, i) => makeHolding(`TICK${i}`, "Growth", 10 - i))
    const rebalance = makeRebalance(holdings)

    render(<HoldingBreakdown rebalance={rebalance as RebalanceResponse} />)

    expect(screen.getByText(/dashboard\.holding_breakdown\.other/)).toBeInTheDocument()
    expect(screen.getByText("dashboard.holding_breakdown.show_all")).toBeInTheDocument()
  })

  it("expands to show all individual holdings (no Other) when button clicked", async () => {
    const user = userEvent.setup()
    const holdings = Array.from({ length: 10 }, (_, i) => makeHolding(`TICK${i}`, "Growth", 10 - i))
    const rebalance = makeRebalance(holdings)

    render(<HoldingBreakdown rebalance={rebalance as RebalanceResponse} />)

    await user.click(screen.getByText("dashboard.holding_breakdown.show_all"))

    expect(screen.getByText(/TICK9/)).toBeInTheDocument()
    expect(screen.queryByText(/dashboard\.holding_breakdown\.other/)).not.toBeInTheDocument()
    expect(screen.getByText("dashboard.holding_breakdown.show_less")).toBeInTheDocument()
  })

  it("collapses back to top 8 + Other when toggled again", async () => {
    const user = userEvent.setup()
    const holdings = Array.from({ length: 10 }, (_, i) => makeHolding(`TICK${i}`, "Growth", 10 - i))
    const rebalance = makeRebalance(holdings)

    render(<HoldingBreakdown rebalance={rebalance as RebalanceResponse} />)

    await user.click(screen.getByText("dashboard.holding_breakdown.show_all"))
    await user.click(screen.getByText("dashboard.holding_breakdown.show_less"))

    expect(screen.getByText(/dashboard\.holding_breakdown\.other/)).toBeInTheDocument()
    expect(screen.getByText("dashboard.holding_breakdown.show_all")).toBeInTheDocument()
  })

  it("does not show expand button when 8 or fewer holdings", () => {
    const holdings = Array.from({ length: 5 }, (_, i) => makeHolding(`TICK${i}`, "Growth", 20))
    const rebalance = makeRebalance(holdings)

    render(<HoldingBreakdown rebalance={rebalance as RebalanceResponse} />)

    expect(screen.queryByText("dashboard.holding_breakdown.show_all")).not.toBeInTheDocument()
    expect(screen.queryByText(/dashboard\.holding_breakdown\.other/)).not.toBeInTheDocument()
  })

  it("aggregates duplicate ticker rows into a single position", () => {
    const rebalance = makeRebalance([
      makeHolding("VTI", "Trend_Setter", 10),
      makeHolding("VTI", "Trend_Setter", 20),
      makeHolding("AAPL", "Moat", 5),
    ])

    render(<HoldingBreakdown rebalance={rebalance as RebalanceResponse} />)

    expect(screen.getByTitle("VTI: 30.0%")).toBeInTheDocument()
    expect(screen.queryByTitle("VTI: 10.0%")).not.toBeInTheDocument()
    expect(screen.queryByTitle("VTI: 20.0%")).not.toBeInTheDocument()
    expect(screen.getByText("30.0%")).toBeInTheDocument()
  })
})
