import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import Radar from "../Radar"

const mockCategoryTabs = vi.fn()

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}))

vi.mock("react-router-dom", () => ({
  useSearchParams: () => [new URLSearchParams(), vi.fn()],
}))

vi.mock("@/api/hooks/useDashboard", () => ({
  useLastScan: () => ({ data: null }),
  useHoldings: () => ({
    data: [
      { ticker: "AAPL", is_cash: false, quantity: 0 },
      { ticker: "MSFT", is_cash: false, quantity: 3 },
      { ticker: "USD", is_cash: true, quantity: 1000 },
    ],
  }),
}))

vi.mock("@/api/hooks/useRadar", () => ({
  useRadarStocks: () => ({
    data: [
      {
        ticker: "AAPL",
        category: "Growth",
        current_thesis: "A",
        current_tags: [],
        display_order: 1,
        last_scan_signal: "NORMAL",
        signal_since: null,
        is_active: true,
        is_etf: false,
        signals: null,
      },
      {
        ticker: "MSFT",
        category: "Growth",
        current_thesis: "M",
        current_tags: [],
        display_order: 2,
        last_scan_signal: "NORMAL",
        signal_since: null,
        is_active: true,
        is_etf: false,
        signals: null,
      },
    ],
    isLoading: false,
    isError: false,
  }),
  useRadarEnrichedStocks: () => ({ data: [] }),
  useRemovedStocks: () => ({ data: [] }),
  useScanStatus: () => ({ data: { is_running: false } }),
  useScanCompletionEffect: () => undefined,
  useResonance: () => ({ data: {} }),
}))

vi.mock("@/components/radar/CategoryTabs", () => ({
  CategoryTabs: (props: { heldTickers: Set<string> }) => {
    mockCategoryTabs(props)
    return <div data-testid="held-tickers">{Array.from(props.heldTickers).sort().join(",")}</div>
  },
}))

vi.mock("@/components/radar/AddStockDrawer", () => ({
  AddStockDrawer: () => null,
}))

vi.mock("@/components/radar/RadarFilterPanel", () => ({
  RadarFilterPanel: () => null,
}))

describe("Radar held tickers", () => {
  it("excludes zero-quantity positions from held tickers", () => {
    render(<Radar />)
    expect(screen.getByTestId("held-tickers")).toHaveTextContent("MSFT")
    expect(screen.getByTestId("held-tickers")).not.toHaveTextContent("AAPL")
  })
})
