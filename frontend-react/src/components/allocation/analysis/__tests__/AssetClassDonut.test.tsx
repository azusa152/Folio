import { render, screen } from "@testing-library/react"
import type { HoldingDetail } from "@/api/types/allocation"
import type { ReactNode } from "react"
import { describe, expect, it, vi } from "vitest"
import { AssetClassDonut } from "../AssetClassDonut"

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  PieChart: ({ children }: { children: ReactNode }) => <div data-testid="pie-chart">{children}</div>,
  Pie: () => <div />,
  Cell: () => <div />,
  Tooltip: () => <div />,
}))

vi.mock("@/hooks/useRechartsTheme", () => ({
  useRechartsTheme: () => ({
    tickColor: "#6b7280",
    tooltipStyle: {},
    tooltipText: "#111",
  }),
}))

const mockHolding = (overrides: Partial<HoldingDetail> = {}): HoldingDetail => ({
  ticker: "AAPL",
  category: "Growth",
  currency: "USD",
  quantity: 10,
  market_value: 1500,
  weight_pct: 50,
  ...overrides,
})

describe("AssetClassDonut", () => {
  it("renders donut chart and legend when data has values", () => {
    render(
      <AssetClassDonut
        data={{ Equity: 70000, "Fixed Income": 15000, Cash: 10000, Alternatives: 5000 }}
      />,
    )

    expect(screen.getByText("allocation.asset_class.title")).toBeInTheDocument()
    expect(screen.getByTestId("pie-chart")).toBeInTheDocument()
    expect(screen.getByText(/allocation\.asset_class\.equity/)).toBeInTheDocument()
  })

  it("renders legend entry for each asset class", () => {
    render(
      <AssetClassDonut
        data={{ Equity: 70000, "Fixed Income": 15000, Cash: 10000, Alternatives: 5000 }}
      />,
    )

    expect(screen.getByText(/allocation\.asset_class\.fixed_income/)).toBeInTheDocument()
    expect(screen.getByText(/allocation\.asset_class\.cash/)).toBeInTheDocument()
    expect(screen.getByText(/allocation\.asset_class\.alternatives/)).toBeInTheDocument()
  })

  it("returns null when all values are zero", () => {
    const { container } = render(
      <AssetClassDonut data={{ Equity: 0, Cash: 0 }} />,
    )

    expect(container.innerHTML).toBe("")
  })

  it("returns null when data is empty", () => {
    const { container } = render(
      <AssetClassDonut data={{}} />,
    )

    expect(container.innerHTML).toBe("")
  })

  it("does not show drill-down UI when no segment is selected", () => {
    render(
      <AssetClassDonut
        data={{ Equity: 70000, Cash: 10000 }}
        holdings={[mockHolding()]}
        privacyMode={false}
      />,
    )

    expect(screen.queryByText("allocation.clear_filter")).not.toBeInTheDocument()
    expect(screen.queryByText("allocation.holdings.title")).not.toBeInTheDocument()
  })
})
