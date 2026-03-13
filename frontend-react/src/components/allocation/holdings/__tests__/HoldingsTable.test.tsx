import type { ComponentProps } from "react"
import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { HoldingsTable } from "../HoldingsTable"

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) => {
      if (key === "allocation.col.fx_rate_info") {
        return `1 ${String(options?.from)} = ${String(options?.rate)} ${String(options?.to)}`
      }
      return key
    },
  }),
}))

vi.mock("@/hooks/useTerminology", () => ({
  useTerminology: () => ({
    term: (_key: string, fallback: string) => fallback,
  }),
}))

describe("HoldingsTable", () => {
  it("renders translated category key for holdings rows", () => {
    render(
      <HoldingsTable
        holdings={[
          {
            ticker: "AAPL",
            account_name: "IB Main",
            category: "Growth",
            quantity: 2,
            market_value: 200,
            weight_pct: 10,
            cost_total: 180,
            change_pct: 5,
            currency: "USD",
          } as unknown as ComponentProps<typeof HoldingsTable>["holdings"][number],
        ]}
        privacyMode={false}
        displayCurrency="USD"
      />,
    )

    expect(screen.getByText("allocation.col.account")).toBeInTheDocument()
    expect(screen.getByText("IB Main")).toBeInTheDocument()
    expect(screen.getByText("config.category.growth")).toBeInTheDocument()
  })

  it("shows cash as neutral with fx rate info and no Home/FX breakdown", () => {
    render(
      <HoldingsTable
        holdings={[
          {
            ticker: "JPY",
            account_name: "SMBC",
            category: "Cash",
            quantity: 1000,
            market_value: 10,
            weight_pct: 1,
            cost_total: 10,
            change_pct: 0,
            purchase_fx_rate: 150,
            current_fx_rate: 0.0067,
            currency: "JPY",
          } as unknown as ComponentProps<typeof HoldingsTable>["holdings"][number],
        ]}
        privacyMode={false}
        displayCurrency="USD"
      />,
    )

    expect(screen.getByText("—")).toBeInTheDocument()
    expect(screen.getByText("1 JPY = 0.0067 USD")).toBeInTheDocument()
    expect(screen.queryByText(/allocation\.col\.home_return/)).not.toBeInTheDocument()
    expect(screen.queryByText(/allocation\.col\.fx_return/)).not.toBeInTheDocument()
  })
})
