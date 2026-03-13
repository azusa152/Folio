import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { AllocationGlance } from "../AllocationGlance"

vi.mock("react-router-dom", () => ({
  useNavigate: () => vi.fn(),
}))

vi.mock("@/hooks/useTerminology", () => ({
  useTerminology: () => ({
    term: (_key: string, fallback?: string) => fallback ?? "",
    isSimplified: false,
  }),
}))

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: unknown }) => <div>{children as never}</div>,
  PieChart: ({ children }: { children: unknown }) => <div>{children as never}</div>,
  Pie: ({ children }: { children: unknown }) => <div>{children as never}</div>,
  Cell: ({ children }: { children?: unknown }) => <div>{children as never}</div>,
  Tooltip: () => null,
  BarChart: ({ children }: { children: unknown }) => <div>{children as never}</div>,
  Bar: ({ children }: { children: unknown }) => <div>{children as never}</div>,
  XAxis: () => null,
  YAxis: () => null,
  ReferenceLine: () => null,
  LabelList: () => null,
}))

describe("AllocationGlance", () => {
  it("renders translated category labels with fallback for unknown keys", () => {
    const rebalance = {
      categories: {
        Trend_Setter: { current_pct: 50, drift_pct: 0 },
        Unknown_Bucket: { current_pct: 50, drift_pct: 0 },
      },
    } as never

    const profile = {
      config: {
        Trend_Setter: 60,
        Unknown_Bucket: 40,
      },
    } as never

    render(<AllocationGlance rebalance={rebalance} profile={profile} />)

    expect(screen.getAllByText(/config\.category\.trend_setter/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/config\.category\.unknown_bucket/).length).toBeGreaterThan(0)
  })
})
