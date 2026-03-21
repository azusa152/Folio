import type { ComponentProps } from "react"
import { render, screen, within } from "@testing-library/react"
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

const termMock = vi.fn((_: string, fallback: string) => fallback)

vi.mock("@/hooks/useTerminology", () => ({
  useTerminology: () => ({
    term: termMock,
    isSimplified: false,
  }),
}))

function buildHolding(
  value: Partial<ComponentProps<typeof HoldingsTable>["holdings"][number]>,
): ComponentProps<typeof HoldingsTable>["holdings"][number] {
  return {
    account_id: 1,
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
  it("uses simplified terminology label for unrealized P/L when available", () => {
    termMock.mockImplementation((key: string, fallback: string) =>
      key === "unrealized_pl" ? "Paper Gain/Loss" : fallback,
    )

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

    expect(screen.getByRole("button", { name: "Paper Gain/Loss" })).toBeInTheDocument()
    expect(screen.getByText("Paper Gain/Loss: +9.09%")).toBeInTheDocument()
  })

  it("renders translated category key for holdings rows", () => {
    termMock.mockImplementation((_: string, fallback: string) => fallback)
    render(
      <HoldingsTable holdings={[buildHolding({})]} privacyMode={false} displayCurrency="USD" />,
    )

    expect(screen.getByText("allocation.col.account")).toBeInTheDocument()
    expect(screen.getByText("IB Main")).toBeInTheDocument()
    expect(screen.getByText("config.category.growth")).toBeInTheDocument()
  })

  it("shows cash as neutral with fx rate info and no Home/FX breakdown", () => {
    termMock.mockImplementation((_: string, fallback: string) => fallback)
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
    termMock.mockImplementation((_: string, fallback: string) => fallback)
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

    expect(screen.getByText("+$25.00")).toBeInTheDocument()
    expect(screen.getByText("+2.86%")).toBeInTheDocument()
    expect(screen.getByText("+$150.00")).toBeInTheDocument()
    expect(screen.getByText("+20.00%")).toBeInTheDocument()

    expect(screen.getByText("allocation.holdings.total_row")).toBeInTheDocument()
    expect(screen.getByText("USD 1200.00")).toBeInTheDocument()
    expect(screen.getByText("+$10.00")).toBeInTheDocument()
    expect(screen.getByText("allocation.col.today: +0.84%")).toBeInTheDocument()
    expect(screen.getByText("+$100.00")).toBeInTheDocument()
    expect(screen.getByText("allocation.col.total_return: +9.09%")).toBeInTheDocument()
  })

  it("sorts rows when ticker header is clicked", async () => {
    termMock.mockImplementation((_: string, fallback: string) => fallback)
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
    termMock.mockImplementation((_: string, fallback: string) => fallback)
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

    expect(screen.getByText("+$5.00")).toBeInTheDocument()
    expect(screen.getByText("allocation.col.today: +0.50%")).toBeInTheDocument()
  })

  it("merges non-cash holdings with same ticker across accounts", () => {
    termMock.mockImplementation((_: string, fallback: string) => fallback)
    render(
      <HoldingsTable
        holdings={[
          buildHolding({
            account_id: 1,
            ticker: "VTI",
            account_name: "IBKR",
            category: "Trend Setter",
            quantity: 10,
            market_value: 1000,
            weight_pct: 40,
            cost_total: 900,
            change_value: 20,
            change_pct: 2.04,
            total_gain_value: 100,
            total_gain_pct: 11.11,
          }),
          buildHolding({
            account_id: 2,
            ticker: "VTI",
            account_name: "Firstrade",
            category: "Trend Setter",
            quantity: 5,
            market_value: 500,
            weight_pct: 20,
            cost_total: 450,
            change_value: 10,
            change_pct: 2.04,
            total_gain_value: 50,
            total_gain_pct: 11.11,
          }),
        ]}
        privacyMode={false}
        displayCurrency="USD"
      />,
    )

    expect(screen.getAllByText("VTI")).toHaveLength(1)
    expect(screen.getByText("Firstrade, IBKR")).toBeInTheDocument()
    expect(screen.getAllByText("USD 1500.00")).toHaveLength(2)
  })

  it("keeps cash holdings split by account even with same ticker", () => {
    termMock.mockImplementation((_: string, fallback: string) => fallback)
    render(
      <HoldingsTable
        holdings={[
          buildHolding({
            account_id: 11,
            ticker: "USD",
            account_name: "IBKR",
            category: "Cash",
            market_value: 1000,
            cost_total: 1000,
            change_value: 0,
            change_pct: 0,
            total_gain_value: 0,
            total_gain_pct: 0,
          }),
          buildHolding({
            account_id: 22,
            ticker: "USD",
            account_name: "Firstrade",
            category: "Cash",
            market_value: 500,
            cost_total: 500,
            change_value: 0,
            change_pct: 0,
            total_gain_value: 0,
            total_gain_pct: 0,
          }),
        ]}
        privacyMode={false}
        displayCurrency="USD"
      />,
    )

    const usdTickerCells = screen
      .getAllByRole("cell")
      .map((c) => c.textContent)
      .filter((text): text is string => text === "USD")
    expect(usdTickerCells).toHaveLength(2)
    expect(screen.getByText("IBKR")).toBeInTheDocument()
    expect(screen.getByText("Firstrade")).toBeInTheDocument()
  })

  it("does not merge non-cash rows when ticker metadata differs", () => {
    termMock.mockImplementation((_: string, fallback: string) => fallback)
    render(
      <HoldingsTable
        holdings={[
          buildHolding({
            ticker: "ABC",
            category: "Growth",
            currency: "USD",
            account_name: "IBKR",
          }),
          buildHolding({
            ticker: "ABC",
            category: "Moat",
            currency: "USD",
            account_name: "Firstrade",
          }),
        ]}
        privacyMode={false}
        displayCurrency="USD"
      />,
    )

    expect(screen.getAllByText("ABC")).toHaveLength(2)
  })

  it("hides merged cost/total return when cost coverage is partial", () => {
    termMock.mockImplementation((_: string, fallback: string) => fallback)
    render(
      <HoldingsTable
        holdings={[
          buildHolding({
            ticker: "QQQ",
            account_name: "IBKR",
            market_value: 1000,
            cost_total: 900,
            total_gain_value: 100,
            total_gain_pct: 11.11,
          }),
          buildHolding({
            ticker: "QQQ",
            account_name: "Firstrade",
            market_value: 500,
            cost_total: null,
            total_gain_value: null,
            total_gain_pct: null,
          }),
        ]}
        privacyMode={false}
        displayCurrency="USD"
      />,
    )

    const qqqCell = screen.getByText("QQQ")
    const row = qqqCell.closest("tr")
    expect(row).not.toBeNull()
    if (!row) return

    expect(within(row).queryByText("USD 900.00")).not.toBeInTheDocument()
    expect(within(row).getAllByText("—").length).toBeGreaterThan(0)
  })

  it("shows deterministic truncated account list for many merged accounts", () => {
    termMock.mockImplementation((_: string, fallback: string) => fallback)
    render(
      <HoldingsTable
        holdings={[
          buildHolding({ ticker: "SPY", account_name: "Zeta" }),
          buildHolding({ ticker: "SPY", account_name: "Alpha", account_id: 2 }),
          buildHolding({ ticker: "SPY", account_name: "Beta", account_id: 3 }),
        ]}
        privacyMode={false}
        displayCurrency="USD"
      />,
    )

    expect(screen.getByText("Alpha, Beta +1")).toBeInTheDocument()
  })
})
