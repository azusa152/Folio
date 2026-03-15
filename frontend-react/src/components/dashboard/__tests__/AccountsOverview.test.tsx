import { fireEvent, render, screen, within } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { AccountsOverview } from "../AccountsOverview"
import { usePrivacyMode } from "@/hooks/usePrivacyMode"
import type { AccountSummaryItem } from "@/api/types/account"
import type { RebalanceResponse } from "@/api/types/dashboard"

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) => {
      if (key === "dashboard.accounts_overview.shares_label" && options?.quantity != null) {
        return `${String(options.quantity)} shares`
      }
      return key
    },
  }),
}))

function renderOverview({
  accountSummary = [],
  rebalance = null,
  displayCurrency = "USD",
  isLoading = false,
  isError = false,
}: {
  accountSummary?: AccountSummaryItem[]
  rebalance?: RebalanceResponse | null
  displayCurrency?: string
  isLoading?: boolean
  isError?: boolean
}) {
  return render(
    <MemoryRouter>
      <AccountsOverview
        accountSummary={accountSummary}
        rebalance={rebalance}
        displayCurrency={displayCurrency}
        isLoading={isLoading}
        isError={isError}
      />
    </MemoryRouter>,
  )
}

describe("AccountsOverview", () => {
  beforeEach(() => {
    usePrivacyMode.setState({ isPrivate: false })
  })

  it("renders empty state when there are no accounts", () => {
    renderOverview({})

    expect(screen.getByText("dashboard.accounts_overview.empty_title")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "dashboard.accounts_overview.empty_cta" })).toBeInTheDocument()
  })

  it("aggregates per-account totals, sorts by total value, and renders account actions", () => {
    const accountSummary = [
      {
        account: { id: 1, name: "Broker A", broker: "IB", account_type: "brokerage" },
        holdings_count: 2,
        tickers: ["AAPL", "MSFT"],
        cash_balances: [{ currency: "USD", balance: 150 }],
      },
      {
        account: { id: 2, name: "Wallet B", broker: "Wallet", account_type: "wallet" },
        holdings_count: 1,
        tickers: ["BTC"],
        cash_balances: [{ currency: "USD", balance: 20 }],
      },
    ] as unknown as AccountSummaryItem[]

    const rebalance = {
      display_currency: "USD",
      holdings_detail: [
        { account_id: 1, account_name: "Broker A", ticker: "AAPL", market_value: 1000, weight_pct: 10, quantity: 1, category: "Growth", currency: "USD" },
        { account_id: 1, account_name: "Broker A", ticker: "MSFT", market_value: 500, weight_pct: 5, quantity: 1, category: "Moat", currency: "USD" },
        { account_id: 2, account_name: "Wallet B", ticker: "BTC", market_value: 400, weight_pct: 4, quantity: 0.01, category: "Crypto", currency: "USD" },
      ],
    } as unknown as RebalanceResponse

    renderOverview({ accountSummary, rebalance, displayCurrency: "USD" })

    const names = screen.getAllByText(/Broker A|Wallet B/).map((el) => el.textContent)
    expect(names[0]).toBe("Broker A")
    expect(names[1]).toBe("Wallet B")

    expect(screen.getByText("$1,650.00")).toBeInTheDocument()
    expect(screen.getByText("$420.00")).toBeInTheDocument()
    expect(screen.getByText(/dashboard\.accounts_overview\.header_total_label/)).toBeInTheDocument()
    expect(screen.getByText("dashboard.accounts_overview.distribution_label")).toBeInTheDocument()

    const depositLinks = screen.getAllByRole("link", { name: "dashboard.accounts_overview.deposit" })
    expect(depositLinks.some((link) => link.getAttribute("href") === "/allocation?tab=accounts&accountId=1&action=deposit")).toBe(true)

    const tradeLinks = screen.getAllByRole("link", { name: "dashboard.accounts_overview.trade" })
    expect(tradeLinks.some((link) => link.getAttribute("href") === "/allocation?tab=accounts&accountId=1&action=trade")).toBe(true)
  })

  it("masks monetary values in privacy mode", () => {
    usePrivacyMode.setState({ isPrivate: true })

    const accountSummary = [
      {
        account: { id: 1, name: "Broker A", broker: "IB", account_type: "brokerage" },
        holdings_count: 1,
        tickers: ["AAPL"],
        cash_balances: [{ currency: "USD", balance: 100 }],
      },
    ] as unknown as AccountSummaryItem[]

    const rebalance = {
      holdings_detail: [
        { account_id: 1, account_name: "Broker A", ticker: "AAPL", market_value: 1000, weight_pct: 10, quantity: 1, category: "Growth", currency: "USD" },
      ],
    } as unknown as RebalanceResponse

    renderOverview({ accountSummary, rebalance, displayCurrency: "USD" })

    expect(screen.getAllByText("***").length).toBeGreaterThan(0)
    expect(screen.queryByText("$1,100.00")).not.toBeInTheDocument()
    expect(screen.queryByTitle(/1100\.00/)).not.toBeInTheDocument()
  })

  it("converts non-display cash when fx is available from rebalance holdings", () => {
    const accountSummary = [
      {
        account: { id: 3, name: "Global Account", broker: "Bank", account_type: "bank" },
        holdings_count: 0,
        tickers: [],
        cash_balances: [{ currency: "JPY", balance: 5000 }],
      },
    ] as unknown as AccountSummaryItem[]

    const rebalance = {
      holdings_detail: [
        {
          account_id: 99,
          account_name: "FX Source",
          ticker: "TM",
          market_value: 100,
          weight_pct: 1,
          quantity: 1,
          category: "Moat",
          currency: "JPY",
          current_fx_rate: 0.01,
        },
      ],
    } as unknown as RebalanceResponse

    renderOverview({ accountSummary, rebalance, displayCurrency: "USD" })

    expect(screen.getAllByText("$50.00").length).toBeGreaterThan(0)
    expect(screen.queryByText("dashboard.accounts_overview.cash_missing_fx_hint")).not.toBeInTheDocument()
  })

  it("shows missing-fx hint when expanded and account has non-display-currency cash without fx source", () => {
    const accountSummary = [
      {
        account: { id: 3, name: "Global Account", broker: "Bank", account_type: "bank" },
        holdings_count: 0,
        tickers: [],
        cash_balances: [
          { currency: "USD", balance: 100 },
          { currency: "JPY", balance: 5000 },
        ],
      },
    ] as unknown as AccountSummaryItem[]

    renderOverview({ accountSummary, rebalance: null, displayCurrency: "USD" })

    fireEvent.click(screen.getByRole("button", { name: /Global Account.*dashboard\.accounts_overview\.toggle_details/ }))
    expect(screen.getByText("dashboard.accounts_overview.cash_missing_fx_hint")).toBeInTheDocument()
  })

  it("shows legend overflow label when there are more than four accounts", () => {
    const accountSummary = Array.from({ length: 5 }, (_, index) => ({
      account: { id: index + 1, name: `Account ${index + 1}`, broker: "Broker", account_type: "brokerage" },
      holdings_count: 1,
      tickers: [`TICK${index + 1}`],
      cash_balances: [{ currency: "USD", balance: 100 - index }],
    })) as unknown as AccountSummaryItem[]

    const rebalance = {
      holdings_detail: accountSummary.map((item, index) => ({
        account_id: item.account!.id,
        account_name: item.account!.name,
        ticker: item.tickers[0],
        market_value: 1000 - index * 10,
        weight_pct: 1,
        quantity: 1,
        category: "Growth",
        currency: "USD",
      })),
    } as unknown as RebalanceResponse

    renderOverview({ accountSummary, rebalance, displayCurrency: "USD" })

    expect(screen.getByText("dashboard.accounts_overview.legend_more")).toBeInTheDocument()
  })

  it("expands account details when row body is clicked, not action links", () => {
    const accountSummary = [
      {
        account: { id: 3, name: "Global Account", broker: "Bank", account_type: "bank" },
        holdings_count: 0,
        tickers: [],
        cash_balances: [
          { currency: "USD", balance: 100 },
          { currency: "JPY", balance: 5000 },
        ],
      },
    ] as unknown as AccountSummaryItem[]

    renderOverview({ accountSummary, rebalance: null, displayCurrency: "USD" })

    expect(screen.queryByText("dashboard.accounts_overview.cash_missing_fx_hint")).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole("link", { name: "dashboard.accounts_overview.deposit" }))
    expect(screen.queryByText("dashboard.accounts_overview.cash_missing_fx_hint")).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: /Global Account.*dashboard\.accounts_overview\.toggle_details/ }))
    expect(screen.getByText("dashboard.accounts_overview.cash_missing_fx_hint")).toBeInTheDocument()
  })

  it("supports click highlight sync between legend and distribution bar", () => {
    const accountSummary = [
      {
        account: { id: 1, name: "Broker A", broker: "IB", account_type: "brokerage" },
        holdings_count: 2,
        tickers: ["AAPL", "MSFT"],
        cash_balances: [{ currency: "USD", balance: 150 }],
      },
      {
        account: { id: 2, name: "Wallet B", broker: "Wallet", account_type: "wallet" },
        holdings_count: 1,
        tickers: ["BTC"],
        cash_balances: [{ currency: "USD", balance: 20 }],
      },
    ] as unknown as AccountSummaryItem[]

    const rebalance = {
      holdings_detail: [
        { account_id: 1, account_name: "Broker A", ticker: "AAPL", market_value: 1000, weight_pct: 10, quantity: 1, category: "Growth", currency: "USD" },
        { account_id: 1, account_name: "Broker A", ticker: "MSFT", market_value: 500, weight_pct: 5, quantity: 1, category: "Moat", currency: "USD" },
        { account_id: 2, account_name: "Wallet B", ticker: "BTC", market_value: 400, weight_pct: 4, quantity: 0.01, category: "Crypto", currency: "USD" },
      ],
    } as unknown as RebalanceResponse

    renderOverview({ accountSummary, rebalance, displayCurrency: "USD" })

    const legendButton = screen.getAllByText("Broker A")[0]?.closest("button")
    expect(legendButton).not.toBeNull()
    if (!legendButton) return
    fireEvent.click(legendButton)
    expect(legendButton).toHaveAttribute("aria-pressed", "true")

    const bar = screen.getByRole("group", { name: "dashboard.accounts_overview.stacked_bar_aria" })
    const barButton = within(bar).getByRole("button", { name: /Wallet B/ })
    fireEvent.click(barButton)
    expect(barButton).toHaveAttribute("aria-pressed", "true")
  })

  it("shows top holdings, overflow link, and unrealized summary when account row is expanded", () => {
    const accountSummary = [
      {
        account: { id: 1, name: "Broker A", broker: "IB", account_type: "brokerage" },
        holdings_count: 4,
        tickers: ["AAPL", "MSFT", "NVDA", "AMZN"],
        cash_balances: [{ currency: "USD", balance: 150 }],
      },
    ] as unknown as AccountSummaryItem[]

    const rebalance = {
      holdings_detail: [
        { account_id: 1, account_name: "Broker A", ticker: "AAPL", market_value: 1000, weight_pct: 10, quantity: 3, category: "Growth", currency: "USD", cost_total: 800 },
        { account_id: 1, account_name: "Broker A", ticker: "MSFT", market_value: 700, weight_pct: 7, quantity: 2, category: "Moat", currency: "USD", cost_total: 650 },
        { account_id: 1, account_name: "Broker A", ticker: "NVDA", market_value: 500, weight_pct: 5, quantity: 1, category: "Growth", currency: "USD", cost_total: 450 },
        { account_id: 1, account_name: "Broker A", ticker: "AMZN", market_value: 300, weight_pct: 3, quantity: 1, category: "Growth", currency: "USD", cost_total: 280 },
      ],
    } as unknown as RebalanceResponse

    renderOverview({ accountSummary, rebalance, displayCurrency: "USD" })

    fireEvent.click(screen.getByRole("button", { name: /Broker A.*dashboard\.accounts_overview\.toggle_details/ }))

    expect(screen.getByText("dashboard.accounts_overview.top_positions_label")).toBeInTheDocument()
    expect(screen.getByText("AAPL")).toBeInTheDocument()
    expect(screen.getByText("3 shares")).toBeInTheDocument()
    expect(screen.getByText("MSFT")).toBeInTheDocument()
    expect(screen.getByText("NVDA")).toBeInTheDocument()
    expect(screen.queryByText("AMZN")).not.toBeInTheDocument()
    expect(screen.getByText("dashboard.accounts_overview.more_positions")).toBeInTheDocument()
    expect(screen.getByText("dashboard.accounts_overview.account_gain_loss")).toBeInTheDocument()

    const links = screen.getAllByRole("link", { name: "dashboard.accounts_overview.view_positions" })
    expect(links.some((link) => link.getAttribute("href") === "/allocation?tab=accounts&accountId=1")).toBe(true)
  })

  it("renders signed negative unrealized percentage at account level", () => {
    const accountSummary = [
      {
        account: { id: 11, name: "Loss Account", broker: "IB", account_type: "brokerage" },
        holdings_count: 1,
        tickers: ["AAPL"],
        cash_balances: [{ currency: "USD", balance: 0 }],
      },
    ] as unknown as AccountSummaryItem[]

    const rebalance = {
      holdings_detail: [
        { account_id: 11, account_name: "Loss Account", ticker: "AAPL", market_value: 850, weight_pct: 10, quantity: 1234.56789, category: "Growth", currency: "USD", cost_total: 1000 },
      ],
    } as unknown as RebalanceResponse

    renderOverview({ accountSummary, rebalance, displayCurrency: "USD" })

    fireEvent.click(screen.getByRole("button", { name: /Loss Account.*dashboard\.accounts_overview\.toggle_details/ }))

    expect(screen.getByText("1,234.5679 shares")).toBeInTheDocument()
    expect(screen.getByText("-$150.00 (-15.0%)")).toBeInTheDocument()
  })

  it("shows no-positions message when account has no holdings", () => {
    const accountSummary = [
      {
        account: { id: 9, name: "Cash Account", broker: "Bank", account_type: "bank" },
        holdings_count: 0,
        tickers: [],
        cash_balances: [{ currency: "USD", balance: 20 }],
      },
    ] as unknown as AccountSummaryItem[]

    renderOverview({ accountSummary, rebalance: null, displayCurrency: "USD" })

    fireEvent.click(screen.getByRole("button", { name: /Cash Account.*dashboard\.accounts_overview\.toggle_details/ }))
    expect(screen.getByText(/dashboard\.accounts_overview\.no_positions/)).toBeInTheDocument()
  })

  it("masks expanded position values in privacy mode", () => {
    usePrivacyMode.setState({ isPrivate: true })

    const accountSummary = [
      {
        account: { id: 1, name: "Broker A", broker: "IB", account_type: "brokerage" },
        holdings_count: 1,
        tickers: ["AAPL"],
        cash_balances: [{ currency: "USD", balance: 100 }],
      },
    ] as unknown as AccountSummaryItem[]

    const rebalance = {
      holdings_detail: [
        { account_id: 1, account_name: "Broker A", ticker: "AAPL", market_value: 1000, weight_pct: 10, quantity: 1, category: "Growth", currency: "USD", cost_total: 700 },
      ],
    } as unknown as RebalanceResponse

    renderOverview({ accountSummary, rebalance, displayCurrency: "USD" })

    fireEvent.click(screen.getByRole("button", { name: /Broker A.*dashboard\.accounts_overview\.toggle_details/ }))
    expect(screen.getAllByText("***").length).toBeGreaterThan(2)
    expect(screen.queryByText("$1,000.00")).not.toBeInTheDocument()
  })

  it("renders error state when account summary query fails", () => {
    renderOverview({ isError: true, accountSummary: [], rebalance: null, displayCurrency: "USD" })

    expect(screen.getByText("dashboard.accounts_overview.error_title")).toBeInTheDocument()
    expect(screen.getByText("dashboard.accounts_overview.error_description")).toBeInTheDocument()
  })
})
