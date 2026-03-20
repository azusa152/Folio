import { render, screen, fireEvent } from "@testing-library/react"
import { describe, it, expect, vi, beforeEach } from "vitest"
import { AccountSection } from "../AccountSection"
import type { UseQueryResult } from "@tanstack/react-query"

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) => {
      if (opts) return `${key}:${JSON.stringify(opts)}`
      return key
    },
  }),
}))

const noop = vi.fn()

function makeQuery<T>(data: T): UseQueryResult<T> {
  return { data, isLoading: false, isError: false } as unknown as UseQueryResult<T>
}

const defaultProps = {
  accountId: "",
  accounts: [
    { id: 1, name: "Main", broker: "IB", currency: "USD", tax_wrapper: "tokutei" },
    { id: 2, name: "NISA", broker: "SBI", currency: "JPY", tax_wrapper: "nisa_growth" },
  ],
  transactionType: "BUY" as const,
  isCashMovement: false,
  currency: "USD",
  selectedAccountId: null,
  selectedCurrencyCashBalance: null,
  selectedAccount: undefined,
  shouldShowQuotaSummary: false,
  selectedWrapper: "",
  selectedQuota: undefined,
  wrapperQuotaQuery: makeQuery(undefined),
  hasNoAccounts: false,
  fieldErrors: {},
  insufficientBalance: null,
  onOpenAccounts: undefined,
  setAccountId: noop,
  setCurrency: noop,
  setTransactionType: noop,
  setQuantity: noop,
  setPrice: noop,
  setManualTotal: noop,
  setTotalAmount: noop,
  setInsufficientBalance: noop,
  setFieldErrors: noop,
  applyCashMovementDefaults: noop,
  clearSellablePositionCache: noop,
}

describe("AccountSection", () => {
  beforeEach(() => { vi.clearAllMocks() })

  it("renders account select with all options", () => {
    render(<AccountSection {...defaultProps} />)
    expect(screen.getByRole("combobox")).toBeInTheDocument()
    expect(screen.getByText("Main (IB)")).toBeInTheDocument()
    expect(screen.getByText("NISA (SBI)")).toBeInTheDocument()
  })

  it("calls setAccountId when account is selected", () => {
    const setAccountId = vi.fn()
    render(<AccountSection {...defaultProps} setAccountId={setAccountId} />)
    const select = screen.getByRole("combobox")
    fireEvent.change(select, { target: { value: "1" } })
    expect(setAccountId).toHaveBeenCalledWith("1")
  })

  it("calls clearSellablePositionCache when account changes", () => {
    const clearSellablePositionCache = vi.fn()
    render(<AccountSection {...defaultProps} clearSellablePositionCache={clearSellablePositionCache} />)
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "1" } })
    expect(clearSellablePositionCache).toHaveBeenCalled()
  })

  it("updates currency when account with a currency is selected", () => {
    const setCurrency = vi.fn()
    render(<AccountSection {...defaultProps} setCurrency={setCurrency} />)
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "2" } })
    expect(setCurrency).toHaveBeenCalledWith("JPY")
  })

  it("shows available cash balance when account is selected", () => {
    render(
      <AccountSection
        {...defaultProps}
        selectedAccountId={1}
        selectedCurrencyCashBalance={500}
        currency="USD"
      />,
    )
    expect(screen.getByText(/available_cash/)).toBeInTheDocument()
  })

  it("does not show balance when no account is selected", () => {
    render(<AccountSection {...defaultProps} selectedAccountId={null} />)
    expect(screen.queryByText(/available_cash/)).not.toBeInTheDocument()
  })

  it("shows field error for account", () => {
    render(<AccountSection {...defaultProps} fieldErrors={{ account: "Account required" }} />)
    expect(screen.getByText("Account required")).toBeInTheDocument()
  })

  it("shows insufficient balance warning with deposit shortcut", () => {
    render(
      <AccountSection
        {...defaultProps}
        insufficientBalance={{ available: 100, required: 500 }}
        selectedAccountId={1}
      />,
    )
    expect(screen.getByText(/insufficient_balance/)).toBeInTheDocument()
    expect(screen.getByText("transactions.form.deposit_cash")).toBeInTheDocument()
  })

  it("clicking deposit shortcut configures DEPOSIT transaction", () => {
    const setTransactionType = vi.fn()
    const setManualTotal = vi.fn()
    const setTotalAmount = vi.fn()
    const setInsufficientBalance = vi.fn()
    render(
      <AccountSection
        {...defaultProps}
        insufficientBalance={{ available: 100, required: 500 }}
        selectedAccountId={1}
        setTransactionType={setTransactionType}
        setManualTotal={setManualTotal}
        setTotalAmount={setTotalAmount}
        setInsufficientBalance={setInsufficientBalance}
      />,
    )
    fireEvent.click(screen.getByText("transactions.form.deposit_cash"))
    expect(setTransactionType).toHaveBeenCalledWith("DEPOSIT")
    expect(setManualTotal).toHaveBeenCalledWith(true)
    expect(setTotalAmount).toHaveBeenCalledWith("400")
    expect(setInsufficientBalance).toHaveBeenCalledWith(null)
  })

  it("shows BUY no-account banner when BUY and hasNoAccounts", () => {
    render(<AccountSection {...defaultProps} hasNoAccounts={true} transactionType="BUY" accounts={[]} />)
    expect(screen.getByText("transactions.form.buy_no_account_banner")).toBeInTheDocument()
  })

  it("shows generic no-account hint for non-BUY types", () => {
    render(
      <AccountSection
        {...defaultProps}
        hasNoAccounts={true}
        transactionType="SELL"
        accounts={[]}
      />,
    )
    expect(screen.getByText("transactions.form.account_empty_hint")).toBeInTheDocument()
  })

  it("calls onOpenAccounts when create account button is clicked", () => {
    const onOpenAccounts = vi.fn()
    render(
      <AccountSection
        {...defaultProps}
        hasNoAccounts={true}
        transactionType="BUY"
        accounts={[]}
        onOpenAccounts={onOpenAccounts}
      />,
    )
    fireEvent.click(screen.getByText("transactions.form.create_account"))
    expect(onOpenAccounts).toHaveBeenCalled()
  })

  it("shows NISA quota summary when shouldShowQuotaSummary is true", () => {
    render(
      <AccountSection
        {...defaultProps}
        shouldShowQuotaSummary={true}
        selectedWrapper="nisa_growth"
        selectedQuota={{ wrapper_annual_remaining: 1_200_000, wrapper_annual_used: 0 }}
        wrapperQuotaQuery={makeQuery({ quotas: {} })}
        selectedAccountId={2}
      />,
    )
    expect(screen.getByText(/nisa_quota_summary/)).toBeInTheDocument()
  })

  it("shows proceeds hint for SELL when account is selected", () => {
    render(
      <AccountSection
        {...defaultProps}
        transactionType="SELL"
        selectedAccountId={1}
        selectedAccount={{ id: 1, name: "Main", broker: "IB" }}
      />,
    )
    expect(screen.getByText(/proceeds_hint/)).toBeInTheDocument()
  })
})
