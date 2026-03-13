import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it } from "vitest"
import { AccountsOverview } from "../AccountsOverview"
import { usePrivacyMode } from "@/hooks/usePrivacyMode"
import type { AccountSummaryItem } from "@/api/types/account"
import type { RebalanceResponse } from "@/api/types/dashboard"

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

    expect(screen.getByText("$50.00")).toBeInTheDocument()
    expect(screen.queryByText("dashboard.accounts_overview.cash_missing_fx_hint")).not.toBeInTheDocument()
  })

  it("shows missing-fx hint when account has non-display-currency cash without fx source", () => {
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

    expect(screen.getByText("dashboard.accounts_overview.cash_missing_fx_hint")).toBeInTheDocument()
  })

  it("renders error state when account summary query fails", () => {
    renderOverview({ isError: true, accountSummary: [], rebalance: null, displayCurrency: "USD" })

    expect(screen.getByText("dashboard.accounts_overview.error_title")).toBeInTheDocument()
    expect(screen.getByText("dashboard.accounts_overview.error_description")).toBeInTheDocument()
  })
})
