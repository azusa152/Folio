import { render, screen } from "@testing-library/react"
import type { ReactNode } from "react"
import { describe, expect, it, vi } from "vitest"
import { AllocationCharts } from "../AllocationCharts"
import type { CategoryAllocation } from "@/api/types/allocation"

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  BarChart: ({ children }: { children: ReactNode }) => (
    <div data-testid="bar-chart">{children}</div>
  ),
  Bar: ({ children }: { children: ReactNode }) => <div>{children}</div>,
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

vi.mock("../../holdings/HoldingsTable", () => ({
  HoldingsTable: () => <div data-testid="holdings-table" />,
}))

function cat(target: number, current: number, mv = 10000): CategoryAllocation {
  return {
    target_pct: target,
    current_pct: current,
    drift_pct: current - target,
    market_value: mv,
  }
}

const BASE_CATEGORIES: Record<string, CategoryAllocation> = {
  ETF: cat(40, 42, 42000),
  Bond: cat(30, 28, 28000),
  Growth: cat(20, 25, 25000),
  Cash: cat(10, 5, 5000),
}

describe("AllocationCharts", () => {
  it("renders bar chart and summary table", () => {
    render(<AllocationCharts categories={BASE_CATEGORIES} />)

    expect(screen.getByTestId("bar-chart")).toBeInTheDocument()
    expect(screen.getByText("allocation.charts.title")).toBeInTheDocument()
  })

  it("renders summary table with each visible category", () => {
    render(<AllocationCharts categories={BASE_CATEGORIES} />)

    expect(screen.getByText("ETF")).toBeInTheDocument()
    expect(screen.getByText("Bond")).toBeInTheDocument()
    expect(screen.getByText("Growth")).toBeInTheDocument()
    expect(screen.getByText("Cash")).toBeInTheDocument()
  })

  it("groups categories below 1% into Other bucket", () => {
    const categories: Record<string, CategoryAllocation> = {
      ETF: cat(95, 95, 95000),
      Tiny: cat(0, 0.5, 500),
    }
    render(<AllocationCharts categories={categories} />)

    expect(screen.getByText("allocation.charts.other")).toBeInTheDocument()
    expect(screen.queryByText("Tiny")).not.toBeInTheDocument()
  })

  it("does not render Other row when all categories are >= 1%", () => {
    render(<AllocationCharts categories={BASE_CATEGORIES} />)

    expect(screen.queryByText("allocation.charts.other")).not.toBeInTheDocument()
  })

  it("renders legend for target and actual", () => {
    render(<AllocationCharts categories={BASE_CATEGORIES} />)

    // legend items appear twice: once in header, once in table header
    expect(screen.getAllByText("allocation.charts.target").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("allocation.charts.actual").length).toBeGreaterThanOrEqual(1)
  })

  it("does not show holdings drill-down when no category is selected", () => {
    render(<AllocationCharts categories={BASE_CATEGORIES} holdings={[]} />)

    expect(screen.queryByText("allocation.clear_filter")).not.toBeInTheDocument()
    expect(screen.queryByTestId("holdings-table")).not.toBeInTheDocument()
  })
})
