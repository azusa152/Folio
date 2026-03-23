import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { SignalAlerts } from "../SignalAlerts"

vi.mock("react-router-dom", () => ({
  useNavigate: () => vi.fn(),
}))

vi.mock("@/lib/signal-label", () => ({
  getSignalLabel: (_t: unknown, signal: string) => signal,
  getSignalDescription: (_t: unknown, signal: string) => signal,
}))

describe("SignalAlerts", () => {
  it("renders translated category labels with fallback for unknown categories", () => {
    const stocks = [
      {
        ticker: "AAPL",
        category: "Trend_Setter",
        is_active: true,
        last_scan_signal: "DEEP_VALUE",
      },
      {
        ticker: "ZZZ",
        category: "Unknown_Bucket",
        is_active: true,
        last_scan_signal: "DEEP_VALUE",
      },
    ] as never

    render(<SignalAlerts stocks={stocks} enrichedStocks={[]} signalActivity={[]} />)

    expect(
      screen.getAllByText(
        (_, element) => element?.textContent?.includes("config.category.trend_setter") ?? false,
      ).length,
    ).toBeGreaterThan(0)
    expect(
      screen.getAllByText(
        (_, element) => element?.textContent?.includes("config.category.unknown_bucket") ?? false,
      ).length,
    ).toBeGreaterThan(0)
  })
})
