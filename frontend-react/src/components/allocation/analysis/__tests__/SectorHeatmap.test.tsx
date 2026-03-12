import { render, screen } from "@testing-library/react"
import type { ReactNode } from "react"
import { describe, expect, it, vi } from "vitest"
import { SectorHeatmap } from "../SectorHeatmap"

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  Treemap: ({ data }: { data: Array<{ name: string; weight_pct: number }> }) => (
    <div data-testid="sector-heatmap">
      {data.map((entry) => (
        <div key={entry.name}>
          {entry.name}:{entry.weight_pct.toFixed(1)}%
        </div>
      ))}
    </div>
  ),
  Tooltip: () => <div />,
}))

vi.mock("@/hooks/useRechartsTheme", () => ({
  useRechartsTheme: () => ({
    tickColor: "#6b7280",
    tooltipStyle: {},
    tooltipText: "#111",
  }),
}))

describe("SectorHeatmap", () => {
  it("uses equity_pct for displayed sector percentages", () => {
    render(
      <SectorHeatmap
        data={[
          {
            sector: "Technology",
            value: 26081,
            weight_pct: 22.5,
            equity_pct: 100,
          },
        ]}
      />,
    )

    expect(screen.getByTestId("sector-heatmap")).toBeInTheDocument()
    expect(screen.getByText("Technology:100.0%")).toBeInTheDocument()
  })
})
