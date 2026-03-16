import { render } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import Dashboard from "../Dashboard"

let capturedInsightCardProps: unknown = null
const mockInsightCard = vi.fn((props: unknown) => {
  capturedInsightCardProps = props
  return <div data-testid="insight-card" />
})

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: "en" },
  }),
}))

vi.mock("react-router-dom", () => ({
  useNavigate: () => vi.fn(),
}))

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

vi.mock("@/api/hooks/useDashboard", () => ({
  useStocks: () => ({ data: [], isLoading: true, isError: false }),
  useEnrichedStocks: () => ({ data: [], isLoading: false }),
  useLastScan: () => ({ data: null }),
  useHoldings: () => ({ data: [] }),
  useRebalance: () => ({
    data: undefined,
    isLoading: false,
    isFetching: false,
    isError: false,
  }),
  useProfile: () => ({ data: null }),
  useSignalActivity: () => ({ data: [] }),
  useFearGreed: () => ({ data: null, isFetching: false, isError: false }),
  useSnapshots: () => ({ data: [], isLoading: false }),
  useTwr: () => ({ data: null }),
  useGreatMinds: () => ({ data: null, isLoading: false }),
  useInsights: () => ({ data: undefined, isLoading: false }),
}))

vi.mock("@/api/hooks/useAccounts", () => ({
  useAccountSummary: () => ({ data: [], isLoading: false, isError: false }),
}))

vi.mock("@/api/hooks/useRadar", () => ({
  useScanCompletionEffect: () => undefined,
}))

vi.mock("@/api/hooks/useAllocation", () => ({
  useTriggerDigest: () => ({ mutate: vi.fn(), isPending: false }),
}))

vi.mock("@/hooks/useLocalStorage", () => ({
  useLocalStorage: () => [false, vi.fn()],
}))

vi.mock("@/components/common/InsightCard", () => ({
  InsightCard: (props: unknown) => mockInsightCard(props),
}))

vi.mock("@/components/LazySection", () => ({
  LazySection: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

vi.mock("@/components/EmptyState", () => ({
  EmptyState: () => null,
}))

vi.mock("@/components/ui/select", () => ({
  Select: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  SelectContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  SelectItem: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  SelectTrigger: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  SelectValue: () => null,
}))

vi.mock("@/components/ui/button", () => ({
  Button: ({ children, onClick }: { children: React.ReactNode; onClick?: () => void }) => (
    <button onClick={onClick}>{children}</button>
  ),
}))

vi.mock("@/components/dashboard/PortfolioPulse", () => ({
  PortfolioPulse: () => null,
}))
vi.mock("@/components/dashboard/PerformanceChart", () => ({
  PerformanceChart: () => null,
}))
vi.mock("@/components/dashboard/SignalAlerts", () => ({
  SignalAlerts: () => null,
}))
vi.mock("@/components/dashboard/AllocationGlance", () => ({
  AllocationGlance: () => null,
}))
vi.mock("@/components/dashboard/TopHoldings", () => ({
  TopHoldings: () => null,
}))
vi.mock("@/components/dashboard/DividendIncome", () => ({
  DividendIncome: () => null,
}))
vi.mock("@/components/dashboard/ResonanceSummary", () => ({
  ResonanceSummary: () => null,
}))
vi.mock("@/components/dashboard/StockHeatmap", () => ({
  StockHeatmap: () => null,
}))
vi.mock("@/components/dashboard/AccountsOverview", () => ({
  AccountsOverview: () => null,
}))
vi.mock("@/components/dashboard/SectorAllocationCard", () => ({
  SectorAllocationCard: () => null,
}))
vi.mock("@/components/dashboard/HoldingBreakdown", () => ({
  HoldingBreakdown: () => null,
}))

describe("Dashboard insights loading", () => {
  it("passes loading=true to InsightCard while stocks are loading", () => {
    capturedInsightCardProps = null
    render(<Dashboard />)

    expect(mockInsightCard).toHaveBeenCalled()
    expect(capturedInsightCardProps).not.toBeNull()
    const firstCallProps = capturedInsightCardProps as {
      insights?: unknown[]
      isLoading?: boolean
    }
    expect(firstCallProps.insights).toEqual([])
    expect(firstCallProps.isLoading).toBe(true)
  })
})
