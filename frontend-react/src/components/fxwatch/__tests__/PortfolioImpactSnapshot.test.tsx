import { fireEvent, render, screen } from "@testing-library/react"
import type { ReactNode } from "react"
import { describe, expect, it, vi } from "vitest"
import type { CurrencyExposureResponse } from "@/api/types/allocation"
import { PortfolioImpactSnapshot } from "../PortfolioImpactSnapshot"

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  PieChart: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  Pie: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  Cell: ({ children }: { children?: ReactNode }) => <div>{children}</div>,
  Tooltip: () => null,
  BarChart: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  Bar: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  LabelList: () => <div />,
  XAxis: () => <div />,
  YAxis: () => <div />,
}))

vi.mock("@/hooks/useRechartsTheme", () => ({
  useRechartsTheme: () => ({
    tickColor: "#6b7280",
    tooltipStyle: {},
    tooltipText: "#111827",
  }),
}))

function makeExposure(overrides: Partial<CurrencyExposureResponse> = {}): CurrencyExposureResponse {
  return {
    home_currency: "USD",
    total_value_home: 100000,
    breakdown: [
      { currency: "USD", value: 60000, percentage: 60, is_home: true },
      { currency: "JPY", value: 25000, percentage: 25, is_home: false },
      { currency: "TWD", value: 15000, percentage: 15, is_home: false },
    ],
    non_home_pct: 40,
    cash_breakdown: [
      { currency: "USD", value: 15000, percentage: 75, is_home: true },
      { currency: "JPY", value: 5000, percentage: 25, is_home: false },
    ],
    cash_non_home_pct: 25,
    total_cash_home: 20000,
    fx_movements: [
      { pair: "USD/JPY", current_rate: 150.1, change_pct: 1.2, direction: "up", impact_home_value: 120 },
      { pair: "TWD/USD", current_rate: 0.031, change_pct: -0.6, direction: "down", impact_home_value: -30 },
    ],
    fx_rate_alerts: [],
    risk_level: "medium",
    advice: ["Advice 1", "Advice 2", "Advice 3"],
    calculated_at: "2026-03-15T00:00:00Z",
    ...overrides,
  }
}

describe("PortfolioImpactSnapshot", () => {
  it("renders neutral net impact without positive sign", () => {
    render(
      <PortfolioImpactSnapshot
        exposure={makeExposure({
          fx_movements: [
            { pair: "USD/JPY", current_rate: 150.1, change_pct: 0, direction: "flat", impact_home_value: 0 },
          ],
        })}
        privacyMode={false}
      />,
    )

    expect(screen.getByText("fx_watch.overview.net_impact_neutral")).toBeInTheDocument()
    expect(screen.getByText("0 USD")).toBeInTheDocument()
    expect(screen.queryByText("+0 USD")).not.toBeInTheDocument()
  })

  it("shows advice toggle and expands full advice list", () => {
    render(<PortfolioImpactSnapshot exposure={makeExposure()} privacyMode={false} />)

    expect(screen.getByText((content) => content.includes("Advice 1"))).toBeInTheDocument()
    expect(screen.getByText((content) => content.includes("Advice 2"))).toBeInTheDocument()
    expect(screen.queryByText((content) => content.includes("Advice 3"))).not.toBeInTheDocument()

    fireEvent.click(screen.getByText("fx_watch.overview.advice_show_more"))
    expect(screen.getByText((content) => content.includes("Advice 3"))).toBeInTheDocument()
  })

  it("masks sensitive values in privacy mode", () => {
    render(<PortfolioImpactSnapshot exposure={makeExposure()} privacyMode />)

    expect(screen.getAllByText("***").length).toBeGreaterThanOrEqual(3)
    expect(screen.queryByText("+90 USD")).not.toBeInTheDocument()
    expect(screen.getAllByText("fx_watch.overview.privacy_hidden").length).toBeGreaterThanOrEqual(2)
  })

  it("renders active alert chips when alerts exist", () => {
    render(
      <PortfolioImpactSnapshot
        exposure={makeExposure({
          fx_rate_alerts: [
            {
              pair: "USD/JPY",
              alert_type: "daily_spike",
              change_pct: 1.2,
              direction: "up",
              current_rate: 150.1,
              period_label: "1d",
            },
          ],
        })}
        privacyMode={false}
      />,
    )

    expect(screen.getByText("fx_watch.overview.active_alerts")).toBeInTheDocument()
    expect(screen.getByText("USD/JPY")).toBeInTheDocument()
    expect(screen.getByText("1d")).toBeInTheDocument()
    expect(screen.getByText("+1.20%")).toBeInTheDocument()
  })
})
