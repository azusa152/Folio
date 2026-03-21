import { render, screen } from "@testing-library/react"
import type { HoldingDetail } from "@/api/types/allocation"
import type { ReactNode } from "react"
import { describe, expect, it, vi } from "vitest"
import { GeographicAllocation } from "../GeographicAllocation"

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  BarChart: ({ children }: { children: ReactNode }) => (
    <div data-testid="bar-chart">{children}</div>
  ),
  Bar: () => <div />,
  Cell: () => <div />,
  LabelList: () => <div />,
  XAxis: () => <div />,
  YAxis: () => <div />,
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

describe("GeographicAllocation", () => {
  it("renders chart when data has values", () => {
    render(<GeographicAllocation data={{ US: 50000, TW: 20000, JP: 10000 }} />)

    expect(screen.getByText("allocation.geo.title")).toBeInTheDocument()
    expect(screen.getByText("allocation.geo.cash_included_hint")).toBeInTheDocument()
    expect(screen.getByTestId("bar-chart")).toBeInTheDocument()
  })

  it("returns null when all values are zero", () => {
    const { container } = render(<GeographicAllocation data={{ US: 0, TW: 0 }} />)

    expect(container.innerHTML).toBe("")
  })

  it("returns null when data is empty", () => {
    const { container } = render(<GeographicAllocation data={{}} />)

    expect(container.innerHTML).toBe("")
  })

  it("does not show drill-down UI when no segment is selected", () => {
    render(
      <GeographicAllocation
        data={{ US: 50000, TW: 20000 }}
        holdings={[mockHolding()]}
        privacyMode={false}
      />,
    )

    expect(screen.queryByText("allocation.clear_filter")).not.toBeInTheDocument()
    expect(screen.queryByText("allocation.holdings.title")).not.toBeInTheDocument()
  })
})
