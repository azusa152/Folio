import { describe, it, expect, beforeEach, vi } from "vitest"
import { renderHook } from "@testing-library/react"
import { useTransactionQueries } from "../useTransactionQueries"
import type { TransactionType } from "../types"
import type { AccountResponse } from "@/api/types/account"

// ---------------------------------------------------------------------------
// Hoisted mock state
// ---------------------------------------------------------------------------

const { eligibilityState, routingState } = vi.hoisted(() => ({
  eligibilityState: {
    data: undefined as
      | { asset_type?: string | null; suggested_wrapper?: string | null; eligible?: boolean }
      | undefined,
    isLoading: false,
  },
  routingState: {
    data: undefined as
      | { suggestions: Array<{ wrapper: string; amount: string | number }> }
      | undefined,
    isLoading: false,
  },
}))

vi.mock("@/api/hooks/useAccounts", () => ({
  useAccountCashBalances: () => ({ data: [], isLoading: false }),
  useAccountSellablePositions: () => ({ data: [], isLoading: false, isError: false }),
}))

vi.mock("@/api/hooks/useWrappers", () => ({
  useWrapperEligibility: () => ({
    data: eligibilityState.data,
    isLoading: eligibilityState.isLoading,
  }),
  useSuggestRouting: () => ({ data: routingState.data, isLoading: routingState.isLoading }),
  useEligibleAssets: () => ({ data: { items: [] }, isLoading: false, isFetched: false }),
  useWrapperQuota: () => ({ data: undefined, isLoading: false }),
}))

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeAccount(overrides: {
  id: number
  name: string
  tax_wrapper: string
  currency?: string
}): AccountResponse {
  return {
    id: overrides.id,
    user_id: "test",
    name: overrides.name,
    broker: "Rakuten",
    account_type: "brokerage",
    tax_wrapper: overrides.tax_wrapper as AccountResponse["tax_wrapper"],
    currency: overrides.currency ?? "JPY",
    institution: "",
    note: "",
    is_active: true,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
  }
}

const TOKUTEI_ACCOUNT = makeAccount({ id: 1, name: "Tokutei", tax_wrapper: "tokutei" })
const NISA_GROWTH_ACCOUNT = makeAccount({ id: 2, name: "NISA Growth", tax_wrapper: "nisa_growth" })
const NISA_TSUMITATE_ACCOUNT = makeAccount({
  id: 3,
  name: "NISA Tsumitate",
  tax_wrapper: "nisa_tsumitate",
})

function makeProps(
  overrides: Partial<{
    accounts: AccountResponse[]
    selectedAccountId: number | null
    selectedWrapper: string
    transactionType: TransactionType
    ticker: string
    totalAmount: string
    currency: string
  }> = {},
) {
  return {
    open: true,
    accounts: overrides.accounts ?? [TOKUTEI_ACCOUNT],
    selectedAccountId: overrides.selectedAccountId ?? 1,
    selectedWrapper: overrides.selectedWrapper ?? "tokutei",
    selectedAccountBroker: "Rakuten",
    currency: overrides.currency ?? "JPY",
    ticker: overrides.ticker ?? "AAPL",
    totalAmount: overrides.totalAmount ?? "100000",
    transactionType: (overrides.transactionType ?? "BUY") as TransactionType,
    shouldShowNisaPicker: false,
    shouldShowSellPicker: false,
    shouldCheckEligibility: true,
    shouldSuggestRouting: true,
    shouldShowQuotaSummary: false,
    nisaStockFreeInput: false,
    nisaPickerSearch: "",
    nisaAssetTypeFilter: "all" as const,
  }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("useTransactionQueries", () => {
  beforeEach(() => {
    eligibilityState.data = undefined
    eligibilityState.isLoading = false
    routingState.data = undefined
    routingState.isLoading = false
  })

  describe("forcedCategory", () => {
    it("returns 'Mutual_Fund' for nisa_tsumitate regardless of eligibility", () => {
      const { result } = renderHook(() =>
        useTransactionQueries(makeProps({ selectedWrapper: "nisa_tsumitate" })),
      )
      expect(result.current.forcedCategory).toBe("Mutual_Fund")
    })

    it("returns 'Mutual_Fund' when eligibility asset_type is mutual_fund", () => {
      eligibilityState.data = { asset_type: "mutual_fund" }
      const { result } = renderHook(() =>
        useTransactionQueries(makeProps({ selectedWrapper: "tokutei" })),
      )
      expect(result.current.forcedCategory).toBe("Mutual_Fund")
    })

    it("returns null for non-NISA wrapper with non-mutual-fund asset", () => {
      eligibilityState.data = { asset_type: "etf" }
      const { result } = renderHook(() =>
        useTransactionQueries(makeProps({ selectedWrapper: "tokutei" })),
      )
      expect(result.current.forcedCategory).toBeNull()
    })

    it("returns null when no eligibility data", () => {
      eligibilityState.data = undefined
      const { result } = renderHook(() => useTransactionQueries(makeProps()))
      expect(result.current.forcedCategory).toBeNull()
    })
  })

  describe("suggestedAccount", () => {
    it("returns null when eligibility has no suggested_wrapper", () => {
      eligibilityState.data = { suggested_wrapper: null }
      const { result } = renderHook(() =>
        useTransactionQueries(
          makeProps({ accounts: [TOKUTEI_ACCOUNT, NISA_GROWTH_ACCOUNT], selectedAccountId: 1 }),
        ),
      )
      expect(result.current.suggestedAccount).toBeNull()
    })

    it("returns undefined when suggested_wrapper matches the current account (excluded from search)", () => {
      eligibilityState.data = { suggested_wrapper: "tokutei" }
      const { result } = renderHook(() =>
        useTransactionQueries(
          makeProps({
            accounts: [TOKUTEI_ACCOUNT, NISA_GROWTH_ACCOUNT],
            selectedAccountId: 1,
            selectedWrapper: "tokutei",
          }),
        ),
      )
      // account id=1 is the selected account, so it is excluded and find() returns undefined
      expect(result.current.suggestedAccount).toBeUndefined()
    })

    it("finds an account matching the suggested_wrapper", () => {
      eligibilityState.data = { suggested_wrapper: "nisa_growth" }
      const { result } = renderHook(() =>
        useTransactionQueries(
          makeProps({
            accounts: [TOKUTEI_ACCOUNT, NISA_GROWTH_ACCOUNT],
            selectedAccountId: 1,
            selectedWrapper: "tokutei",
          }),
        ),
      )
      expect(result.current.suggestedAccount?.id).toBe(2)
      expect(result.current.suggestedAccount?.tax_wrapper).toBe("nisa_growth")
    })

    it("returns undefined when no account matches the suggested_wrapper", () => {
      eligibilityState.data = { suggested_wrapper: "ideco" }
      const { result } = renderHook(() =>
        useTransactionQueries(
          makeProps({ accounts: [TOKUTEI_ACCOUNT, NISA_GROWTH_ACCOUNT], selectedAccountId: 1 }),
        ),
      )
      expect(result.current.suggestedAccount).toBeUndefined()
    })
  })

  describe("routingSuggestedAccounts", () => {
    it("builds a map of wrapper → { id, currency } from accounts", () => {
      const { result } = renderHook(() =>
        useTransactionQueries(
          makeProps({ accounts: [TOKUTEI_ACCOUNT, NISA_GROWTH_ACCOUNT, NISA_TSUMITATE_ACCOUNT] }),
        ),
      )
      const map = result.current.routingSuggestedAccounts
      expect(map.get("tokutei")).toEqual({ id: 1, currency: "JPY" })
      expect(map.get("nisa_growth")).toEqual({ id: 2, currency: "JPY" })
      expect(map.get("nisa_tsumitate")).toEqual({ id: 3, currency: "JPY" })
    })

    it("uses first account per wrapper (deduplication)", () => {
      const duplicate = makeAccount({ id: 99, name: "Dup", tax_wrapper: "tokutei" })
      const { result } = renderHook(() =>
        useTransactionQueries(makeProps({ accounts: [TOKUTEI_ACCOUNT, duplicate] })),
      )
      // First account (id=1) wins
      expect(result.current.routingSuggestedAccounts.get("tokutei")?.id).toBe(1)
    })

    it("uppercases currency in the map", () => {
      const lower = makeAccount({ id: 5, name: "X", tax_wrapper: "tokutei", currency: "jpy" })
      const { result } = renderHook(() => useTransactionQueries(makeProps({ accounts: [lower] })))
      expect(result.current.routingSuggestedAccounts.get("tokutei")?.currency).toBe("JPY")
    })
  })

  describe("splitRoutingPlan", () => {
    it("maps routing suggestions to accounts from routingSuggestedAccounts", () => {
      routingState.data = {
        suggestions: [
          { wrapper: "tokutei", amount: "60000" },
          { wrapper: "nisa_growth", amount: "40000" },
        ],
      }
      const { result } = renderHook(() =>
        useTransactionQueries(makeProps({ accounts: [TOKUTEI_ACCOUNT, NISA_GROWTH_ACCOUNT] })),
      )
      const plan = result.current.splitRoutingPlan
      expect(plan).toHaveLength(2)
      expect(plan[0]).toEqual({
        wrapper: "tokutei",
        amount: 60000,
        account: { id: 1, currency: "JPY" },
      })
      expect(plan[1]).toEqual({
        wrapper: "nisa_growth",
        amount: 40000,
        account: { id: 2, currency: "JPY" },
      })
    })

    it("filters out 0-amount items", () => {
      routingState.data = {
        suggestions: [
          { wrapper: "tokutei", amount: "100000" },
          { wrapper: "nisa_growth", amount: "0" },
        ],
      }
      const { result } = renderHook(() =>
        useTransactionQueries(makeProps({ accounts: [TOKUTEI_ACCOUNT, NISA_GROWTH_ACCOUNT] })),
      )
      expect(result.current.splitRoutingPlan).toHaveLength(1)
      expect(result.current.splitRoutingPlan[0].wrapper).toBe("tokutei")
    })

    it("sets account to null when no matching account exists for the wrapper", () => {
      routingState.data = {
        suggestions: [{ wrapper: "ideco", amount: "50000" }],
      }
      const { result } = renderHook(() =>
        useTransactionQueries(makeProps({ accounts: [TOKUTEI_ACCOUNT] })),
      )
      expect(result.current.splitRoutingPlan[0].account).toBeNull()
    })

    it("returns empty array when routing data is undefined", () => {
      routingState.data = undefined
      const { result } = renderHook(() => useTransactionQueries(makeProps()))
      expect(result.current.splitRoutingPlan).toHaveLength(0)
    })
  })

  describe("canSplitPurchase", () => {
    function twoItemPlan() {
      routingState.data = {
        suggestions: [
          { wrapper: "tokutei", amount: "60000" },
          { wrapper: "nisa_growth", amount: "40000" },
        ],
      }
    }

    it("is true when transactionType is BUY and plan has ≥2 items with known accounts", () => {
      twoItemPlan()
      const { result } = renderHook(() =>
        useTransactionQueries(
          makeProps({
            transactionType: "BUY",
            accounts: [TOKUTEI_ACCOUNT, NISA_GROWTH_ACCOUNT],
          }),
        ),
      )
      expect(result.current.canSplitPurchase).toBe(true)
    })

    it("is false when transactionType is SELL", () => {
      twoItemPlan()
      const { result } = renderHook(() =>
        useTransactionQueries(
          makeProps({
            transactionType: "SELL",
            accounts: [TOKUTEI_ACCOUNT, NISA_GROWTH_ACCOUNT],
          }),
        ),
      )
      expect(result.current.canSplitPurchase).toBe(false)
    })

    it("is false when plan has fewer than 2 items", () => {
      routingState.data = { suggestions: [{ wrapper: "tokutei", amount: "100000" }] }
      const { result } = renderHook(() =>
        useTransactionQueries(makeProps({ transactionType: "BUY", accounts: [TOKUTEI_ACCOUNT] })),
      )
      expect(result.current.canSplitPurchase).toBe(false)
    })

    it("is false when any plan item has no matching account", () => {
      // nisa_growth suggestion but only tokutei account → account will be null
      routingState.data = {
        suggestions: [
          { wrapper: "tokutei", amount: "60000" },
          { wrapper: "nisa_growth", amount: "40000" },
        ],
      }
      const { result } = renderHook(() =>
        useTransactionQueries(makeProps({ transactionType: "BUY", accounts: [TOKUTEI_ACCOUNT] })),
      )
      expect(result.current.canSplitPurchase).toBe(false)
    })
  })
})
