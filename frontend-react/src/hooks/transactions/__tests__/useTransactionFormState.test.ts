import { describe, it, expect, beforeEach, vi } from "vitest"
import { renderHook, act } from "@testing-library/react"
import { useTransactionFormState } from "../useTransactionFormState"

const { accountsState } = vi.hoisted(() => ({
  accountsState: {
    accounts: [
      { id: 1, name: "Main", broker: "IB", currency: "USD", tax_wrapper: "tokutei" },
    ] as Array<{
      id: number
      name: string
      broker: string
      currency: string
      tax_wrapper: string
    }>,
  },
}))

vi.mock("@/api/hooks/useAccounts", () => ({
  useAccounts: () => ({ data: accountsState.accounts }),
  useAccountCashBalances: () => ({ data: [{ currency: "USD", balance: 1000 }] }),
  useAccountSellablePositions: () => ({ data: [], isLoading: false, isError: false }),
}))

vi.mock("@/api/hooks/useWrappers", () => ({
  useWrapperEligibility: () => ({ data: undefined, isLoading: false }),
  useSuggestRouting: () => ({ data: undefined, isLoading: false }),
  useEligibleAssets: () => ({ data: { items: [] }, isLoading: false, isFetched: false }),
  useWrapperQuota: () => ({ data: undefined, isLoading: false }),
}))

vi.mock("@/api/hooks/useDashboard", () => ({
  useHoldings: () => ({ data: [{ id: 1, ticker: "AAPL" }] }),
}))

vi.mock("@/api/hooks/useRadar", () => ({
  useRadarStocks: () => ({ data: [], isLoading: false }),
}))

vi.mock("@/hooks/use-mobile", () => ({
  useIsMobile: () => false,
}))

vi.mock("@/hooks/useCommandListScrollFix", () => ({
  useCommandListScrollFix: () => ({
    onWheel: vi.fn(),
    onTouchStart: vi.fn(),
    onTouchMove: vi.fn(),
  }),
}))

vi.mock("@/hooks/useDebouncedValue", () => ({
  useDebouncedValue: (value: unknown) => value,
}))

const defaultProps = {
  open: true,
}

describe("useTransactionFormState", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    accountsState.accounts = [
      { id: 1, name: "Main", broker: "IB", currency: "USD", tax_wrapper: "tokutei" },
    ]
  })

  describe("initial state", () => {
    it("sets transactionType to BUY by default", () => {
      const { result } = renderHook(() => useTransactionFormState(defaultProps))
      expect(result.current.transactionType).toBe("BUY")
    })

    it("applies defaultTransactionType prop", () => {
      const { result } = renderHook(() =>
        useTransactionFormState({ ...defaultProps, defaultTransactionType: "SELL" }),
      )
      expect(result.current.transactionType).toBe("SELL")
    })

    it("applies defaultTicker prop (uppercased)", () => {
      const { result } = renderHook(() =>
        useTransactionFormState({ ...defaultProps, defaultTicker: "aapl" }),
      )
      expect(result.current.ticker).toBe("AAPL")
    })

    it("applies defaultCurrency prop (uppercased)", () => {
      const { result } = renderHook(() =>
        useTransactionFormState({ ...defaultProps, defaultCurrency: "jpy" }),
      )
      expect(result.current.currency).toBe("JPY")
    })

    it("starts with fee set to 0", () => {
      const { result } = renderHook(() => useTransactionFormState(defaultProps))
      expect(result.current.fee).toBe("0")
    })

    it("starts with empty quantity and price", () => {
      const { result } = renderHook(() => useTransactionFormState(defaultProps))
      expect(result.current.quantity).toBe("")
      expect(result.current.price).toBe("")
      expect(result.current.totalAmount).toBe("")
    })
  })

  describe("computeTotalAmount()", () => {
    it("returns quantity × price as string", () => {
      const { result } = renderHook(() => useTransactionFormState(defaultProps))
      expect(result.current.computeTotalAmount("10", "150")).toBe("1500")
    })

    it("returns empty string when quantity is empty", () => {
      const { result } = renderHook(() => useTransactionFormState(defaultProps))
      expect(result.current.computeTotalAmount("", "150")).toBe("")
    })

    it("returns empty string when price is empty", () => {
      const { result } = renderHook(() => useTransactionFormState(defaultProps))
      expect(result.current.computeTotalAmount("10", "")).toBe("")
    })

    it("returns empty string when quantity is NaN", () => {
      const { result } = renderHook(() => useTransactionFormState(defaultProps))
      expect(result.current.computeTotalAmount("abc", "150")).toBe("")
    })

    it("returns empty string when price is NaN", () => {
      const { result } = renderHook(() => useTransactionFormState(defaultProps))
      expect(result.current.computeTotalAmount("10", "abc")).toBe("")
    })

    it("handles fractional quantities correctly", () => {
      const { result } = renderHook(() => useTransactionFormState(defaultProps))
      expect(result.current.computeTotalAmount("0.5", "200")).toBe("100")
    })
  })

  describe("applyCashMovementDefaults()", () => {
    it("sets ticker to the given currency (uppercased)", () => {
      const { result } = renderHook(() => useTransactionFormState(defaultProps))
      act(() => {
        result.current.applyCashMovementDefaults("jpy")
      })
      expect(result.current.ticker).toBe("JPY")
    })

    it("sets quantity to 1", () => {
      const { result } = renderHook(() => useTransactionFormState(defaultProps))
      act(() => {
        result.current.applyCashMovementDefaults("USD")
      })
      expect(result.current.quantity).toBe("1")
    })

    it("clears price", () => {
      const { result } = renderHook(() => useTransactionFormState(defaultProps))
      act(() => {
        result.current.setPrice("999")
      })
      act(() => {
        result.current.applyCashMovementDefaults("USD")
      })
      expect(result.current.price).toBe("")
    })

    it("sets manualTotal to true", () => {
      const { result } = renderHook(() => useTransactionFormState(defaultProps))
      act(() => {
        result.current.applyCashMovementDefaults("USD")
      })
      expect(result.current.manualTotal).toBe(true)
    })
  })

  describe("resetForm()", () => {
    it("resets transactionType to initial", () => {
      const { result } = renderHook(() =>
        useTransactionFormState({ ...defaultProps, defaultTransactionType: "SELL" }),
      )
      act(() => {
        result.current.setTransactionType("DEPOSIT")
      })
      act(() => {
        result.current.resetForm()
      })
      expect(result.current.transactionType).toBe("SELL")
    })

    it("clears ticker by default", () => {
      const { result } = renderHook(() => useTransactionFormState(defaultProps))
      act(() => {
        result.current.setTicker("AAPL")
      })
      act(() => {
        result.current.resetForm()
      })
      expect(result.current.ticker).toBe("")
    })

    it("keeps ticker when keepDefaultTicker is true", () => {
      const { result } = renderHook(() =>
        useTransactionFormState({ ...defaultProps, defaultTicker: "MSFT" }),
      )
      act(() => {
        result.current.setTicker("GOOGL")
      })
      act(() => {
        result.current.resetForm({ keepDefaultTicker: true })
      })
      expect(result.current.ticker).toBe("MSFT")
    })

    it("resets quantity, price, totalAmount to empty", () => {
      const { result } = renderHook(() => useTransactionFormState(defaultProps))
      act(() => {
        result.current.setQuantity("10")
        result.current.setPrice("100")
        result.current.setTotalAmount("1000")
      })
      act(() => {
        result.current.resetForm()
      })
      expect(result.current.quantity).toBe("")
      expect(result.current.price).toBe("")
      expect(result.current.totalAmount).toBe("")
    })

    it("resets fee to 0", () => {
      const { result } = renderHook(() => useTransactionFormState(defaultProps))
      act(() => {
        result.current.setFee("50")
      })
      act(() => {
        result.current.resetForm()
      })
      expect(result.current.fee).toBe("0")
    })

    it("resets manualTotal to false", () => {
      const { result } = renderHook(() => useTransactionFormState(defaultProps))
      act(() => {
        result.current.setManualTotal(true)
      })
      act(() => {
        result.current.resetForm()
      })
      expect(result.current.manualTotal).toBe(false)
    })

    it("resets NISA picker state", () => {
      const { result } = renderHook(() => useTransactionFormState(defaultProps))
      act(() => {
        result.current.setNisaPickerOpen(true)
        result.current.setNisaPickerSearch("fund")
        result.current.setNisaAssetTypeFilter("etf")
      })
      act(() => {
        result.current.resetForm()
      })
      expect(result.current.nisaPickerOpen).toBe(false)
      expect(result.current.nisaPickerSearch).toBe("")
      expect(result.current.nisaAssetTypeFilter).toBe("all")
    })

    it("resets sell picker state", () => {
      const { result } = renderHook(() => useTransactionFormState(defaultProps))
      act(() => {
        result.current.setSellPickerOpen(true)
        result.current.setSellPickerSearch("aapl")
      })
      act(() => {
        result.current.resetForm()
      })
      expect(result.current.sellPickerOpen).toBe(false)
      expect(result.current.sellPickerSearch).toBe("")
    })
  })

  describe("getSellValueSourceLabel()", () => {
    it("returns null for live_price", () => {
      const { result } = renderHook(() => useTransactionFormState(defaultProps))
      expect(result.current.getSellValueSourceLabel("live_price")).toBeNull()
    })

    it("returns null when valueSource is undefined", () => {
      const { result } = renderHook(() => useTransactionFormState(defaultProps))
      expect(result.current.getSellValueSourceLabel(undefined)).toBeNull()
    })

    it("returns i18n key string for cost_basis", () => {
      const { result } = renderHook(() => useTransactionFormState(defaultProps))
      expect(result.current.getSellValueSourceLabel("cost_basis")).toBe(
        "transactions.sell_picker.value_source_cost_basis",
      )
    })

    it("returns i18n key string for unavailable", () => {
      const { result } = renderHook(() => useTransactionFormState(defaultProps))
      expect(result.current.getSellValueSourceLabel("unavailable")).toBe(
        "transactions.sell_picker.value_source_unavailable",
      )
    })
  })

  describe("derived state", () => {
    it("isCashMovement is true for DEPOSIT", () => {
      const { result } = renderHook(() =>
        useTransactionFormState({ ...defaultProps, defaultTransactionType: "DEPOSIT" }),
      )
      expect(result.current.isCashMovement).toBe(true)
    })

    it("isCashMovement is false for BUY", () => {
      const { result } = renderHook(() => useTransactionFormState(defaultProps))
      expect(result.current.isCashMovement).toBe(false)
    })

    it("hasNoAccounts is false when accounts are present", () => {
      const { result } = renderHook(() => useTransactionFormState(defaultProps))
      expect(result.current.hasNoAccounts).toBe(false)
    })

    it("selectedAccountId is null when accountId is empty", () => {
      const { result } = renderHook(() => useTransactionFormState(defaultProps))
      expect(result.current.selectedAccountId).toBeNull()
    })

    it("selectedAccountId reflects parsed accountId", () => {
      const { result } = renderHook(() =>
        useTransactionFormState({ ...defaultProps, defaultAccountId: 1 }),
      )
      expect(result.current.selectedAccountId).toBe(1)
    })
  })

  describe("onSelectNisaAsset()", () => {
    it("sets ticker from selected asset", () => {
      const { result } = renderHook(() => useTransactionFormState(defaultProps))
      act(() => {
        result.current.onSelectNisaAsset({
          ticker: "7203",
          fund_name: "Toyota",
          asset_type: "stock",
          trust_fee_pct: null,
        })
      })
      expect(result.current.ticker).toBe("7203")
      expect(result.current.nisaPickerOpen).toBe(false)
      expect(result.current.nisaPickerSearch).toBe("")
    })
  })

  describe("onSelectSellablePosition()", () => {
    it("sets ticker from selected position", () => {
      const { result } = renderHook(() => useTransactionFormState(defaultProps))
      act(() => {
        result.current.onSelectSellablePosition({
          ticker: "aapl",
          fund_name: "Apple Inc.",
          quantity: 10,
          currency: "USD",
          value_source: "live_price",
        })
      })
      expect(result.current.ticker).toBe("AAPL")
      expect(result.current.sellPickerOpen).toBe(false)
      expect(result.current.sellPickerSearch).toBe("")
    })
  })

  describe("useEffect syncs", () => {
    describe("nisaAssetTypeFilter reset when wrapper leaves nisa_growth", () => {
      it("resets nisaAssetTypeFilter to 'all' when switching from nisa_growth to a non-NISA account", () => {
        accountsState.accounts = [
          {
            id: 1,
            name: "NISA Growth",
            broker: "Rakuten",
            currency: "JPY",
            tax_wrapper: "nisa_growth",
          },
          { id: 2, name: "Tokutei", broker: "Rakuten", currency: "JPY", tax_wrapper: "tokutei" },
        ]
        const { result } = renderHook(() =>
          useTransactionFormState({ ...defaultProps, defaultAccountId: 1 }),
        )

        // Set a non-default filter while on nisa_growth account
        act(() => {
          result.current.setNisaAssetTypeFilter("etf")
        })
        expect(result.current.nisaAssetTypeFilter).toBe("etf")

        // Switch to the tokutei account — wrapper changes from nisa_growth to tokutei
        act(() => {
          result.current.setAccountId("2")
        })
        expect(result.current.nisaAssetTypeFilter).toBe("all")
      })

      it("does not reset nisaAssetTypeFilter when staying on nisa_growth", () => {
        accountsState.accounts = [
          {
            id: 1,
            name: "NISA Growth",
            broker: "Rakuten",
            currency: "JPY",
            tax_wrapper: "nisa_growth",
          },
        ]
        const { result } = renderHook(() =>
          useTransactionFormState({ ...defaultProps, defaultAccountId: 1 }),
        )

        act(() => {
          result.current.setNisaAssetTypeFilter("etf")
        })
        // No account change — filter should be preserved
        expect(result.current.nisaAssetTypeFilter).toBe("etf")
      })
    })

    describe("nisaFreeTickerInput toggle clears ticker and pickers", () => {
      it("clears ticker when nisaFreeTickerInput transitions from true to false", () => {
        // nisa_growth + transactionType=BUY + nisaAssetTypeFilter=stock → nisaStockFreeInput=true → nisaFreeTickerInput=true
        accountsState.accounts = [
          {
            id: 1,
            name: "NISA Growth",
            broker: "Rakuten",
            currency: "JPY",
            tax_wrapper: "nisa_growth",
          },
          { id: 2, name: "Tokutei", broker: "Rakuten", currency: "JPY", tax_wrapper: "tokutei" },
        ]
        const { result } = renderHook(() =>
          useTransactionFormState({ ...defaultProps, defaultAccountId: 1 }),
        )

        // Enter free-ticker mode: nisa_growth + filter=stock
        act(() => {
          result.current.setNisaAssetTypeFilter("stock")
        })
        // Manually set a ticker value to verify it gets cleared
        act(() => {
          result.current.setTicker("7203.T")
        })
        expect(result.current.ticker).toBe("7203.T")

        // Leave free-ticker mode by switching to non-NISA account
        // (this changes selectedWrapper away from nisa_growth, so nisaStockFreeInput becomes false)
        act(() => {
          result.current.setAccountId("2")
        })
        // ticker should be cleared and pickers should close
        expect(result.current.ticker).toBe("")
        expect(result.current.nisaPickerOpen).toBe(false)
        expect(result.current.nisaPickerSearch).toBe("")
      })
    })
  })
})
