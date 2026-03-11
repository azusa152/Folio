import { render, screen } from "@testing-library/react"
import type { ReactNode } from "react"
import { describe, expect, it, vi } from "vitest"
import { SectorAllocationCard } from "../SectorAllocationCard"

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  PieChart: ({ children }: { children: ReactNode }) => <div data-testid="sector-pie">{children}</div>,
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

describe("SectorAllocationCard", () => {
  it("renders sector pie chart when data is provided", () => {
    render(
      <SectorAllocationCard
        sectorExposure={[
          { sector: "Technology", value: 30000, weight_pct: 40 },
          { sector: "Healthcare", value: 15000, weight_pct: 20 },
          { sector: "Financials", value: 10000, weight_pct: 13.3 },
        ]}
      />,
    )

    expect(screen.getByText("allocation.sector_standalone.title")).toBeInTheDocument()
    expect(screen.getByTestId("sector-pie")).toBeInTheDocument()
    expect(screen.getByText(/Technology/)).toBeInTheDocument()
    expect(screen.getByText(/Healthcare/)).toBeInTheDocument()
  })

  it("returns null when sectorExposure is empty", () => {
    const { container } = render(
      <SectorAllocationCard sectorExposure={[]} />,
    )

    expect(container.innerHTML).toBe("")
  })

  it("buckets excess sectors into Other", () => {
    const sectors = Array.from({ length: 10 }, (_, i) => ({
      sector: `Sector${i}`,
      value: (10 - i) * 1000,
      weight_pct: (10 - i) * 5,
    }))

    render(<SectorAllocationCard sectorExposure={sectors} />)

    expect(screen.getByText(/allocation\.sector_standalone\.other/)).toBeInTheDocument()
  })
})
