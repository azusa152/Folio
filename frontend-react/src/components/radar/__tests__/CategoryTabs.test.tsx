import { describe, expect, it, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { CategoryTabs } from "../CategoryTabs"
import { makeRadarStock } from "./fixtures"

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, params?: { count?: number }) =>
      typeof params?.count === "number" ? `${key} (${params.count})` : key,
  }),
}))

vi.mock("../StockCard", () => ({
  StockCard: () => <div>stock-card</div>,
}))

vi.mock("../ReorderSection", () => ({
  ReorderSection: () => null,
}))

vi.mock("../ArchiveTab", () => ({
  ArchiveTab: () => null,
}))

describe("CategoryTabs", () => {
  it("renders Crypto tab when crypto stocks exist", () => {
    const cryptoStock = makeRadarStock({
      ticker: "BTC-USD",
      category: "Crypto",
      current_thesis: "monitor btc",
      last_scan_signal: "NORMAL",
      signal_since: null,
    })

    render(
      <CategoryTabs
        stocks={[cryptoStock]}
        totalStocks={[cryptoStock]}
        hasActiveFilters={false}
        removedStocks={[]}
        enrichedMap={{}}
        resonanceMap={{}}
        heldTickers={new Set<string>()}
      />,
    )

    expect(screen.getByText("radar.tab.crypto (1)")).toBeInTheDocument()
  })
})
