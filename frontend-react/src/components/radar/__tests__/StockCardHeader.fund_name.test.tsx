import { describe, expect, it, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { StockCard } from "../StockCard"
import type { RadarStock, RadarEnrichedStock } from "@/api/types/radar"

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}))

vi.mock("@/components/LightweightChartWrapper", () => ({
  LightweightChartWrapper: () => <div data-testid="chart" />,
}))

vi.mock("@/api/hooks/useRadar", () => ({
  useAddThesis: () => ({ mutate: vi.fn(), isPending: false }),
  useUpdateCategory: () => ({ mutate: vi.fn(), isPending: false }),
  useDeactivateStock: () => ({ mutate: vi.fn(), isPending: false }),
  useThesisHistory: () => ({ data: [], isLoading: false }),
  usePriceHistory: () => ({ data: [], isLoading: false }),
  useMoatAnalysis: () => ({ data: null, isLoading: false }),
}))

vi.mock("@/components/radar/SparklineHeader", () => ({
  SparklineHeader: () => <div data-testid="sparkline-header" />,
}))

const MF_STOCK: RadarStock = {
  ticker: "01311143",
  category: "Mutual_Fund",
  current_thesis: "eMAXIS Slim S&P500",
  current_tags: [],
  display_order: 0,
  last_scan_signal: "NORMAL",
  signal_since: null,
  is_active: true,
  is_etf: false,
} as RadarStock

const MF_ENRICHMENT_WITH_NAME: RadarEnrichedStock = {
  ticker: "01311143",
  computed_signal: "NORMAL",
  fund_name: "eMAXIS Slim S&P500",
  nav_date: "2026-03-17",
} as unknown as RadarEnrichedStock

const MF_ENRICHMENT_NO_NAME: RadarEnrichedStock = {
  ticker: "01311143",
  computed_signal: "NORMAL",
  fund_name: null,
} as unknown as RadarEnrichedStock

const REGULAR_STOCK: RadarStock = {
  ticker: "AAPL",
  category: "Moat",
  current_thesis: "iPhone ecosystem",
  current_tags: [],
  display_order: 0,
  last_scan_signal: "NORMAL",
  signal_since: null,
  is_active: true,
  is_etf: false,
} as RadarStock

const REGULAR_ENRICHMENT: RadarEnrichedStock = {
  ticker: "AAPL",
  computed_signal: "NORMAL",
  fund_name: undefined,
} as unknown as RadarEnrichedStock

describe("StockCardHeader — mutual fund name display", () => {
  it("shows fund name as primary label when fund_name is available", () => {
    render(<StockCard stock={MF_STOCK} enrichment={MF_ENRICHMENT_WITH_NAME} index={0} />)
    expect(screen.getByText("eMAXIS Slim S&P500")).toBeInTheDocument()
  })

  it("shows ticker as secondary muted label alongside fund name", () => {
    render(<StockCard stock={MF_STOCK} enrichment={MF_ENRICHMENT_WITH_NAME} index={0} />)
    // ticker appears in the sub-label with the signal icon prefix
    const tickerEl = screen.getByText(/01311143/)
    expect(tickerEl).toBeInTheDocument()
  })

  it("falls back to ticker-only display when fund_name is null", () => {
    render(<StockCard stock={MF_STOCK} enrichment={MF_ENRICHMENT_NO_NAME} index={0} />)
    // fund name text must not appear
    expect(screen.queryByText("eMAXIS Slim S&P500")).not.toBeInTheDocument()
    // ticker is still shown
    expect(screen.getByText(/01311143/)).toBeInTheDocument()
  })

  it("shows ticker-only for non-mutual-fund stock regardless of fund_name field", () => {
    render(
      <StockCard
        stock={REGULAR_STOCK}
        enrichment={{ ...REGULAR_ENRICHMENT, fund_name: "some fund" } as RadarEnrichedStock}
        index={0}
      />,
    )
    // The fund_name should NOT be shown for a non-mutual-fund
    expect(screen.queryByText("some fund")).not.toBeInTheDocument()
    expect(screen.getByText(/AAPL/)).toBeInTheDocument()
  })

  it("renders ticker-only when no enrichment is provided", () => {
    render(<StockCard stock={MF_STOCK} index={0} />)
    expect(screen.getByText(/01311143/)).toBeInTheDocument()
    expect(screen.queryByText("eMAXIS Slim S&P500")).not.toBeInTheDocument()
  })
})
