import { fireEvent, render, screen, within } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { AccountsOverview } from "../AccountsOverview"
import { usePrivacyMode } from "@/hooks/usePrivacyMode"
import type { AccountSummaryItem } from "@/api/types/account"
import type { RebalanceResponse } from "@/api/types/dashboard"
import { makeAccountSummaryItem, makeRebalanceResponse } from "./fixtures"

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) => {
      if (key === "common.quantity_unit.shares" && options?.quantity != null) {
        return `${String(options.quantity)} shares`
      }
      if (key === "common.quantity_unit.units" && options?.quantity != null) {
        return `${String(options.quantity)} units`
      }
      if (key === "common.quantity_unit.crypto" && options?.quantity != null && options?.ticker != null) {
        return `${String(options.quantity)} ${String(options.ticker)}`
      }
      if (key === "common.quantity_unit.currency" && options?.quantity != null && options?.ticker != null) {
        return `${String(options.quantity)} ${String(options.ticker)}`
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
      makeAccountSummaryItem({
        account: { id: 1, name: "Broker A", broker: "IB", account_type: "brokerage" },
        holdings_count: 2,
        tickers: ["AAPL", "MSFT"],
        cash_balances: [{ currency: "USD", balance: 150 }],
      }),
      makeAccountSummaryItem({
        account: { id: 2, name: "Wallet B", broker: "Wallet", account_type: "wallet" },
        holdings_count: 1,
        tickers: ["BTC"],
        cash_balances: [{ currency: "USD", balance: 20 }],
      }),
    ]

    const rebalance = makeRebalanceResponse({
      display_currency: "USD",
      holdings_detail: [
        { account_id: 1, account_name: "Broker A", ticker: "AAPL", market_value: 1000, weight_pct: 10, quantity: 1, category: "Growth", currency: "USD" },
        { account_id: 1, account_name: "Broker A", ticker: "MSFT", market_value: 500, weight_pct: 5, quantity: 1, category: "Moat", currency: "USD" },
        { account_id: 2, account_name: "Wallet B", ticker: "BTC", market_value: 400, weight_pct: 4, quantity: 0.01, category: "Crypto", currency: "USD" },
      ],
    })

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
      makeAccountSummaryItem({
        account: { id: 1, name: "Broker A", broker: "IB", account_type: "brokerage" },
        holdings_count: 1,
        tickers: ["AAPL"],
        cash_balances: [{ currency: "USD", balance: 100 }],
      }),
    ]

    const rebalance = makeRebalanceResponse({
      holdings_detail: [
        { account_id: 1, account_name: "Broker A", ticker: "AAPL", market_value: 1000, weight_pct: 10, quantity: 1, category: "Growth", currency: "USD" },
      ],
    })

    renderOverview({ accountSummary, rebalance, displayCurrency: "USD" })

    expect(screen.getAllByText("***").length).toBeGreaterThan(0)
    expect(screen.queryByText("$1,100.00")).not.toBeInTheDocument()
    expect(screen.queryByTitle(/1100\.00/)).not.toBeInTheDocument()
  })

  it("converts non-display cash when fx is available from rebalance holdings", () => {
    const accountSummary = [
      makeAccountSummaryItem({
        account: { id: 3, name: "Global Account", broker: "Bank", account_type: "bank" },
        holdings_count: 0,
        tickers: [],
        cash_balances: [{ currency: "JPY", balance: 5000 }],
      }),
    ]

    const rebalance = makeRebalanceResponse({
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
    })

    renderOverview({ accountSummary, rebalance, displayCurrency: "USD" })

    expect(screen.getAllByText("$50.00").length).toBeGreaterThan(0)
    expect(screen.queryByText("dashboard.accounts_overview.cash_missing_fx_hint")).not.toBeInTheDocument()
  })

  it("shows missing-fx hint when expanded and account has non-display-currency cash without fx source", () => {
    const accountSummary = [
      makeAccountSummaryItem({
        account: { id: 3, name: "Global Account", broker: "Bank", account_type: "bank" },
        holdings_count: 0,
        tickers: [],
        cash_balances: [
          { currency: "USD", balance: 100 },
          { currency: "JPY", balance: 5000 },
        ],
      }),
    ]

    renderOverview({ accountSummary, rebalance: null, displayCurrency: "USD" })

    fireEvent.click(screen.getByRole("button", { name: /Global Account.*dashboard\.accounts_overview\.toggle_details/ }))
    expect(screen.getByText("dashboard.accounts_overview.cash_missing_fx_hint")).toBeInTheDocument()
  })

  it("shows legend overflow label when there are more than four accounts", () => {
    const accountSummary = Array.from({ length: 5 }, (_, index) =>
      makeAccountSummaryItem({
        account: { id: index + 1, name: `Account ${index + 1}`, broker: "Broker", account_type: "brokerage" },
        holdings_count: 1,
        tickers: [`TICK${index + 1}`],
        cash_balances: [{ currency: "USD", balance: 100 - index }],
      }),
    )

    const rebalance = makeRebalanceResponse({
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
    })

    renderOverview({ accountSummary, rebalance, displayCurrency: "USD" })

    expect(screen.getByText("dashboard.accounts_overview.legend_more")).toBeInTheDocument()
  })

  it("expands account details when row body is clicked, not action links", () => {
    const accountSummary = [
      makeAccountSummaryItem({
        account: { id: 3, name: "Global Account", broker: "Bank", account_type: "bank" },
        holdings_count: 0,
        tickers: [],
        cash_balances: [
          { currency: "USD", balance: 100 },
          { currency: "JPY", balance: 5000 },
        ],
      }),
    ]

    renderOverview({ accountSummary, rebalance: null, displayCurrency: "USD" })

    expect(screen.queryByText("dashboard.accounts_overview.cash_missing_fx_hint")).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole("link", { name: "dashboard.accounts_overview.deposit" }))
    expect(screen.queryByText("dashboard.accounts_overview.cash_missing_fx_hint")).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: /Global Account.*dashboard\.accounts_overview\.toggle_details/ }))
    expect(screen.getByText("dashboard.accounts_overview.cash_missing_fx_hint")).toBeInTheDocument()
  })

  it("supports click highlight sync between legend and distribution bar", () => {
    const accountSummary = [
      makeAccountSummaryItem({
        account: { id: 1, name: "Broker A", broker: "IB", account_type: "brokerage" },
        holdings_count: 2,
        tickers: ["AAPL", "MSFT"],
        cash_balances: [{ currency: "USD", balance: 150 }],
      }),
      makeAccountSummaryItem({
        account: { id: 2, name: "Wallet B", broker: "Wallet", account_type: "wallet" },
        holdings_count: 1,
        tickers: ["BTC"],
        cash_balances: [{ currency: "USD", balance: 20 }],
      }),
    ]

    const rebalance = makeRebalanceResponse({
      holdings_detail: [
        { account_id: 1, account_name: "Broker A", ticker: "AAPL", market_value: 1000, weight_pct: 10, quantity: 1, category: "Growth", currency: "USD" },
        { account_id: 1, account_name: "Broker A", ticker: "MSFT", market_value: 500, weight_pct: 5, quantity: 1, category: "Moat", currency: "USD" },
        { account_id: 2, account_name: "Wallet B", ticker: "BTC", market_value: 400, weight_pct: 4, quantity: 0.01, category: "Crypto", currency: "USD" },
      ],
    })

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
      makeAccountSummaryItem({
        account: { id: 1, name: "Broker A", broker: "IB", account_type: "brokerage" },
        holdings_count: 4,
        tickers: ["USD", "BTC", "AAPL", "MSFT"],
        cash_balances: [{ currency: "USD", balance: 150 }],
      }),
    ]

    const rebalance = makeRebalanceResponse({
      holdings_detail: [
        { account_id: 1, account_name: "Broker A", ticker: "BTC", market_value: 900, weight_pct: 9, quantity: 0.12345678, category: "Crypto", currency: "USD", cost_total: 870 },
        { account_id: 1, account_name: "Broker A", ticker: "AAPL", market_value: 700, weight_pct: 7, quantity: 3, category: "Growth", currency: "USD", cost_total: 650 },
        { account_id: 1, account_name: "Broker A", ticker: "MSFT", market_value: 400, weight_pct: 4, quantity: 2, category: "Moat", currency: "USD", cost_total: 390 },
      ],
    })

    renderOverview({ accountSummary, rebalance, displayCurrency: "USD" })

    fireEvent.click(screen.getByRole("button", { name: /Broker A.*dashboard\.accounts_overview\.toggle_details/ }))

    expect(screen.getByText("dashboard.accounts_overview.top_positions_label")).toBeInTheDocument()
    expect(screen.getByText("BTC")).toBeInTheDocument()
    expect(screen.getByText("0.12345678 BTC")).toBeInTheDocument()
    expect(screen.getByText("AAPL")).toBeInTheDocument()
    expect(screen.getByText("3 shares")).toBeInTheDocument()
    expect(screen.getByText("MSFT")).toBeInTheDocument()
    expect(screen.queryByText("dashboard.accounts_overview.more_positions")).not.toBeInTheDocument()
    expect(screen.getByText("dashboard.accounts_overview.unrealized_pnl")).toBeInTheDocument()
    expect(screen.getByText("dashboard.accounts_overview.value_breakdown_label")).toBeInTheDocument()
    expect(screen.getByText("dashboard.accounts_overview.cash_category")).toBeInTheDocument()
    expect(screen.queryByText("dashboard.accounts_overview.cash_label:")).not.toBeInTheDocument()

    const links = screen.getAllByRole("link", { name: "dashboard.accounts_overview.view_positions" })
    expect(links.some((link) => link.getAttribute("href") === "/allocation?tab=accounts&accountId=1")).toBe(true)
  })

  it("renders signed negative unrealized percentage at account level", () => {
    const accountSummary = [
      makeAccountSummaryItem({
        account: { id: 11, name: "Loss Account", broker: "IB", account_type: "brokerage" },
        holdings_count: 1,
        tickers: ["AAPL"],
        cash_balances: [{ currency: "USD", balance: 0 }],
      }),
    ]

    const rebalance = makeRebalanceResponse({
      holdings_detail: [
        { account_id: 11, account_name: "Loss Account", ticker: "AAPL", market_value: 850, weight_pct: 10, quantity: 1234.56789, category: "Growth", currency: "USD", cost_total: 1000 },
      ],
    })

    renderOverview({ accountSummary, rebalance, displayCurrency: "USD" })

    fireEvent.click(screen.getByRole("button", { name: /Loss Account.*dashboard\.accounts_overview\.toggle_details/ }))

    expect(screen.getByText("1,234.5679 shares")).toBeInTheDocument()
    expect(screen.getByText("-$150.00 (-15.0%)")).toBeInTheDocument()
  })

  it("shows daily change when holdings include change_pct", () => {
    const accountSummary = [
      makeAccountSummaryItem({
        account: { id: 12, name: "Daily Account", broker: "IB", account_type: "brokerage" },
        holdings_count: 1,
        tickers: ["AAPL"],
        cash_balances: [{ currency: "USD", balance: 150 }],
      }),
    ]

    const rebalance = makeRebalanceResponse({
      holdings_detail: [
        {
          account_id: 12,
          account_name: "Daily Account",
          ticker: "AAPL",
          market_value: 1100,
          weight_pct: 10,
          quantity: 2,
          category: "Growth",
          currency: "USD",
          change_pct: 10,
        },
      ],
    })

    renderOverview({ accountSummary, rebalance, displayCurrency: "USD" })

    fireEvent.click(screen.getByRole("button", { name: /Daily Account.*dashboard\.accounts_overview\.toggle_details/ }))

    expect(screen.getByText("dashboard.accounts_overview.today_change")).toBeInTheDocument()
    expect(screen.getByText("+$100.00 (+10.0%)")).toBeInTheDocument()
  })

  it("hides daily change when holdings have no change_pct data", () => {
    const accountSummary = [
      makeAccountSummaryItem({
        account: { id: 13, name: "No Daily Change", broker: "IB", account_type: "brokerage" },
        holdings_count: 1,
        tickers: ["MSFT"],
        cash_balances: [{ currency: "USD", balance: 100 }],
      }),
    ]

    const rebalance = makeRebalanceResponse({
      holdings_detail: [
        {
          account_id: 13,
          account_name: "No Daily Change",
          ticker: "MSFT",
          market_value: 900,
          weight_pct: 10,
          quantity: 1,
          category: "Growth",
          currency: "USD",
        },
      ],
    })

    renderOverview({ accountSummary, rebalance, displayCurrency: "USD" })

    fireEvent.click(screen.getByRole("button", { name: /No Daily Change.*dashboard\.accounts_overview\.toggle_details/ }))

    expect(screen.getByText("dashboard.accounts_overview.today_change")).toBeInTheDocument()
    expect(screen.getByText("dashboard.accounts_overview.today_change_unavailable")).toBeInTheDocument()
  })

  it("shows today amount as estimate when daily coverage is limited", () => {
    const accountSummary = [
      makeAccountSummaryItem({
        account: { id: 14, name: "Partial Coverage", broker: "IB", account_type: "brokerage" },
        holdings_count: 2,
        tickers: ["AAPL", "MSFT"],
        cash_balances: [{ currency: "USD", balance: 0 }],
      }),
    ]

    const rebalance = makeRebalanceResponse({
      holdings_detail: [
        {
          account_id: 14,
          account_name: "Partial Coverage",
          ticker: "AAPL",
          market_value: 1100,
          weight_pct: 10,
          quantity: 2,
          category: "Growth",
          currency: "USD",
          change_pct: 10,
        },
        {
          account_id: 14,
          account_name: "Partial Coverage",
          ticker: "MSFT",
          market_value: 900,
          weight_pct: 9,
          quantity: 1,
          category: "Moat",
          currency: "USD",
        },
      ],
    })

    renderOverview({ accountSummary, rebalance, displayCurrency: "USD" })

    fireEvent.click(screen.getByRole("button", { name: /Partial Coverage.*dashboard\.accounts_overview\.toggle_details/ }))

    expect(screen.getByText("dashboard.accounts_overview.today_change")).toBeInTheDocument()
    expect(screen.getByText("+$100.00")).toBeInTheDocument()
    expect(screen.getByText("dashboard.accounts_overview.today_change_estimated")).toBeInTheDocument()
  })

  it("uses localized other category label instead of raw backend category name", () => {
    const accountSummary = [
      makeAccountSummaryItem({
        account: { id: 15, name: "Other Category Account", broker: "IB", account_type: "brokerage" },
        holdings_count: 1,
        tickers: ["XYZ"],
        cash_balances: [{ currency: "USD", balance: 0 }],
      }),
    ]

    const rebalance = makeRebalanceResponse({
      holdings_detail: [
        {
          account_id: 15,
          account_name: "Other Category Account",
          ticker: "XYZ",
          market_value: 1000,
          weight_pct: 10,
          quantity: 1,
          category: "SpecialBucket",
          currency: "USD",
          change_pct: 1.5,
        },
        {
          account_id: 15,
          account_name: "Other Category Account",
          ticker: "ABC",
          market_value: 300,
          weight_pct: 3,
          quantity: 1,
          category: "LegacyAlt",
          currency: "USD",
        },
      ],
    })

    renderOverview({ accountSummary, rebalance, displayCurrency: "USD" })

    fireEvent.click(screen.getByRole("button", { name: /Other Category Account.*dashboard\.accounts_overview\.toggle_details/ }))

    expect(screen.getAllByText("dashboard.accounts_overview.other_category")).toHaveLength(1)
    expect(screen.queryByText("SpecialBucket")).not.toBeInTheDocument()
    expect(screen.queryByText("LegacyAlt")).not.toBeInTheDocument()
  })

  it("does not double count cash when both cash holding and cash_balances are present", () => {
    const accountSummary = [
      makeAccountSummaryItem({
        account: { id: 16, name: "No Double Cash", broker: "IB", account_type: "brokerage" },
        holdings_count: 1,
        tickers: ["AAPL"],
        cash_balances: [{ currency: "USD", balance: 500 }],
      }),
    ]

    const rebalance = makeRebalanceResponse({
      holdings_detail: [
        {
          account_id: 16,
          account_name: "No Double Cash",
          ticker: "AAPL",
          market_value: 1000,
          weight_pct: 10,
          quantity: 1,
          category: "Growth",
          currency: "USD",
        },
        {
          account_id: 16,
          account_name: "No Double Cash",
          ticker: "USD",
          market_value: 500,
          weight_pct: 5,
          quantity: 500,
          category: "Cash",
          currency: "USD",
        },
      ],
    })

    renderOverview({ accountSummary, rebalance, displayCurrency: "USD" })

    expect(screen.getAllByText("$1,500.00").length).toBeGreaterThan(0)
    expect(screen.queryByText("$2,000.00")).not.toBeInTheDocument()
  })

  it("shows no-positions message when account has no holdings", () => {
    const accountSummary = [
      makeAccountSummaryItem({
        account: { id: 9, name: "Cash Account", broker: "Bank", account_type: "bank" },
        holdings_count: 0,
        tickers: [],
        cash_balances: [{ currency: "USD", balance: 20 }],
      }),
    ]

    renderOverview({ accountSummary, rebalance: null, displayCurrency: "USD" })

    fireEvent.click(screen.getByRole("button", { name: /Cash Account.*dashboard\.accounts_overview\.toggle_details/ }))
    expect(screen.getByText(/dashboard\.accounts_overview\.no_positions/)).toBeInTheDocument()
    expect(screen.getByText("dashboard.accounts_overview.cash_label:")).toBeInTheDocument()
  })

  it("masks expanded position values in privacy mode", () => {
    usePrivacyMode.setState({ isPrivate: true })

    const accountSummary = [
      makeAccountSummaryItem({
        account: { id: 1, name: "Broker A", broker: "IB", account_type: "brokerage" },
        holdings_count: 1,
        tickers: ["AAPL"],
        cash_balances: [{ currency: "USD", balance: 100 }],
      }),
    ]

    const rebalance = makeRebalanceResponse({
      holdings_detail: [
        { account_id: 1, account_name: "Broker A", ticker: "AAPL", market_value: 1000, weight_pct: 10, quantity: 1, category: "Growth", currency: "USD", cost_total: 700 },
      ],
    })

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
