import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { RebalanceAnalysis } from "../RebalanceAnalysis"

const mockUseAllocRebalance = vi.fn()

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}))

vi.mock("@/hooks/useTerminology", () => ({
  useTerminology: () => ({
    term: (_key: string, fallback: string) => fallback,
  }),
}))

vi.mock("@/api/hooks/useAllocation", () => ({
  useAllocRebalance: (...args: unknown[]) => mockUseAllocRebalance(...args),
}))

vi.mock("@/api/hooks/useAnalytics", () => ({
  useDrawdown: () => ({ data: [], isLoading: false, isError: false }),
  useRiskMetrics: () => ({ data: null, isLoading: false, isError: false }),
}))

vi.mock("../HealthScore", () => ({
  HealthScore: () => <div data-testid="health-score" />,
}))
vi.mock("../AllocationCharts", () => ({
  AllocationCharts: () => <div data-testid="allocation-charts" />,
}))
vi.mock("../GeographicAllocation", () => ({
  GeographicAllocation: () => <div data-testid="geo" />,
}))
vi.mock("../AssetClassDonut", () => ({
  AssetClassDonut: () => <div data-testid="asset-class" />,
}))
vi.mock("../DrawdownChart", () => ({
  DrawdownChart: () => <div data-testid="drawdown-chart" />,
}))
vi.mock("../RiskMetricsCards", () => ({
  RiskMetricsCards: () => <div data-testid="risk-metrics" />,
}))
vi.mock("../XRayOverlap", () => ({
  XRayOverlap: () => <div data-testid="xray" />,
}))
vi.mock("../SectorHeatmap", () => ({
  SectorHeatmap: () => <div data-testid="sector-heatmap" />,
}))
vi.mock("../../holdings/HoldingsTable", () => ({
  HoldingsTable: () => <div data-testid="holdings-table" />,
}))

describe("RebalanceAnalysis", () => {
  it("shows refreshing hint only during background fetch", () => {
    const rebalanceData = {
      health_score: 80,
      health_level: "healthy",
      calculated_at: "2026-01-01T00:00:00Z",
      advice: [],
      categories: [],
      holdings_detail: [],
      geographic_allocation: null,
      asset_class_allocation: null,
      xray: [],
      xray_coverage_pct: 0,
      xray_skipped_etfs: [],
      sector_exposure: [],
    }

    mockUseAllocRebalance.mockReturnValue({
      data: rebalanceData,
      isLoading: false,
      isFetching: false,
    })
    const { rerender } = render(
      <RebalanceAnalysis displayCurrency="USD" privacyMode={false} enabled />,
    )
    expect(screen.queryByText("allocation.refreshing")).not.toBeInTheDocument()

    mockUseAllocRebalance.mockReturnValue({
      data: rebalanceData,
      isLoading: false,
      isFetching: true,
    })
    rerender(<RebalanceAnalysis displayCurrency="USD" privacyMode={false} enabled />)
    expect(screen.getByText("allocation.refreshing")).toBeInTheDocument()
  })
})
