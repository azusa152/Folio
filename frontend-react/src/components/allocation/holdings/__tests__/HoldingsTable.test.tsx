import type { ComponentProps } from "react"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
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

vi.mock("@/hooks/usePrivacyMode", () => ({
  maskMoney: (value: number, currency: string) => `${currency} ${value.toFixed(2)}`,
}))

vi.mock("@/hooks/useTerminology", () => ({
  useTerminology: () => ({
    term: (_key: string, fallback: string) => fallback,
  }),
}))

function buildHolding(
  value: Partial<ComponentProps<typeof HoldingsTable>["holdings"][number]>,
): ComponentProps<typeof HoldingsTable>["holdings"][number] {
  return {
    ticker: "AAPL",
    account_name: "IB Main",
    category: "Growth",
    quantity: 2,
    market_value: 200,
    weight_pct: 10,
    cost_total: 180,
    change_pct: 5,
    change_value: 10,
    total_gain_value: 20,
    total_gain_pct: 11.11,
    currency: "USD",
    ...value,
  } as ComponentProps<typeof HoldingsTable>["holdings"][number]
}

describe("HoldingsTable", () => {
  it("renders translated category key for holdings rows", () => {
    render(
      <HoldingsTable
        holdings={[
          buildHolding({}),
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
          buildHolding({
            ticker: "JPY",
            account_name: "SMBC",
            category: "Cash",
            quantity: 1000,
            market_value: 10,
            weight_pct: 1,
            cost_total: 10,
            change_pct: 0,
            change_value: 0,
            total_gain_value: 0,
            total_gain_pct: 0,
            purchase_fx_rate: 150,
            current_fx_rate: 0.0067,
            currency: "JPY",
          }),
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

  it("renders today and total return dual-line values with footer totals", () => {
    render(
      <HoldingsTable
        holdings={[
          buildHolding({
            ticker: "AAPL",
            market_value: 900,
            weight_pct: 60,
            cost_total: 750,
            change_value: 25,
            change_pct: 2.86,
            total_gain_value: 150,
            total_gain_pct: 20,
          }),
          buildHolding({
            ticker: "MSFT",
            market_value: 300,
            weight_pct: 40,
            cost_total: 350,
            change_value: -15,
            change_pct: -4.76,
            total_gain_value: -50,
            total_gain_pct: -14.29,
          }),
        ]}
        privacyMode={false}
        displayCurrency="USD"
      />,
    )

    expect(screen.getByText("+USD 25.00")).toBeInTheDocument()
    expect(screen.getByText("+2.86%")).toBeInTheDocument()
    expect(screen.getByText("+USD 150.00")).toBeInTheDocument()
    expect(screen.getByText("+20.00%")).toBeInTheDocument()

    expect(screen.getByText("allocation.holdings.total_row")).toBeInTheDocument()
    expect(screen.getByText("USD 1200.00")).toBeInTheDocument()
    expect(screen.getByText("+USD 10.00")).toBeInTheDocument()
    expect(screen.getByText("allocation.col.today: +0.84%")).toBeInTheDocument()
    expect(screen.getByText("+USD 100.00")).toBeInTheDocument()
    expect(screen.getByText("allocation.col.total_return: +9.09%")).toBeInTheDocument()
  })

  it("sorts rows when ticker header is clicked", async () => {
    const user = userEvent.setup()
    render(
      <HoldingsTable
        holdings={[
          buildHolding({
            ticker: "AAPL",
            weight_pct: 10,
          }),
          buildHolding({
            ticker: "TSLA",
            weight_pct: 30,
          }),
        ]}
        privacyMode={false}
        displayCurrency="USD"
      />,
    )

    const tickerButtons = screen.getAllByRole("button", { name: "allocation.col.ticker" })
    await user.click(tickerButtons[0])
    const tickerHeader = screen.getByRole("columnheader", { name: "allocation.col.ticker" })
    expect(tickerHeader).toHaveAttribute("aria-sort", "ascending")

    const tickerCells = screen
      .getAllByRole("cell")
      .map((c) => c.textContent)
      .filter((text): text is string => !!text && (text === "AAPL" || text === "TSLA"))
    expect(tickerCells[0]).toBe("AAPL")
    expect(tickerCells[1]).toBe("TSLA")
  })

  it("uses portfolio daily totals in footer when provided", () => {
    render(
      <HoldingsTable
        holdings={[
          buildHolding({
            ticker: "AAPL",
            market_value: 550,
            change_value: null,
            change_pct: null,
          }),
          buildHolding({
            ticker: "MSFT",
            market_value: 450,
            change_value: 20,
            change_pct: 4.65,
          }),
        ]}
        privacyMode={false}
        displayCurrency="USD"
        portfolioTodayChangeValue={5}
        portfolioTodayChangePct={0.5}
      />,
    )

    expect(screen.getByText("+USD 5.00")).toBeInTheDocument()
    expect(screen.getByText("allocation.col.today: +0.50%")).toBeInTheDocument()
  })
})
