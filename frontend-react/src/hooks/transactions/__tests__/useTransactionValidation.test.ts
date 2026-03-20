import { describe, it, expect } from "vitest"
import { renderHook, act } from "@testing-library/react"
import { useTransactionValidation } from "../useTransactionValidation"
import type { TransactionValidationInput } from "../useTransactionValidation"

function makeInput(overrides: Partial<TransactionValidationInput> = {}): TransactionValidationInput {
  return {
    accountId: "1",
    ticker: "AAPL",
    quantity: "10",
    price: "150",
    totalAmount: "1500",
    fxRate: "",
    fee: "0",
    transactionDate: "2026-01-01",
    isCashMovement: false,
    shouldShowSellPicker: false,
    selectedSellablePosition: null,
    ...overrides,
  }
}

describe("useTransactionValidation", () => {
  describe("validate() — success cases", () => {
    it("returns true and clears errors for valid stock buy", () => {
      const { result } = renderHook(() => useTransactionValidation(makeInput()))
      let isValid = false
      act(() => { isValid = result.current.validate() })
      expect(isValid).toBe(true)
      expect(result.current.fieldErrors).toEqual({})
    })

    it("returns true for valid cash movement (ticker and quantity not required)", () => {
      const { result } = renderHook(() =>
        useTransactionValidation(makeInput({
          isCashMovement: true,
          ticker: "",
          quantity: "",
          totalAmount: "500",
        })),
      )
      let isValid = false
      act(() => { isValid = result.current.validate() })
      expect(isValid).toBe(true)
      expect(result.current.fieldErrors).toEqual({})
    })
  })

  describe("validate() — required field errors", () => {
    it("sets account error when accountId is empty", () => {
      const { result } = renderHook(() =>
        useTransactionValidation(makeInput({ accountId: "" })),
      )
      act(() => { result.current.validate() })
      expect(result.current.fieldErrors.account).toBe("transactions.form.account_required")
    })

    it("sets ticker error when ticker is blank for non-cash movement", () => {
      const { result } = renderHook(() =>
        useTransactionValidation(makeInput({ ticker: "  " })),
      )
      act(() => { result.current.validate() })
      expect(result.current.fieldErrors.ticker).toBe("transactions.form.error_ticker")
    })

    it("sets quantity error when quantity is zero for non-cash movement", () => {
      const { result } = renderHook(() =>
        useTransactionValidation(makeInput({ quantity: "0" })),
      )
      act(() => { result.current.validate() })
      expect(result.current.fieldErrors.quantity).toBe("transactions.form.error_quantity")
    })

    it("sets quantity error when quantity is negative for non-cash movement", () => {
      const { result } = renderHook(() =>
        useTransactionValidation(makeInput({ quantity: "-5" })),
      )
      act(() => { result.current.validate() })
      expect(result.current.fieldErrors.quantity).toBe("transactions.form.error_quantity")
    })

    it("sets totalAmount error when totalAmount is empty", () => {
      const { result } = renderHook(() =>
        useTransactionValidation(makeInput({ totalAmount: "" })),
      )
      act(() => { result.current.validate() })
      expect(result.current.fieldErrors.totalAmount).toBe("transactions.form.error_total_amount")
    })

    it("sets totalAmount error when totalAmount is zero", () => {
      const { result } = renderHook(() =>
        useTransactionValidation(makeInput({ totalAmount: "0" })),
      )
      act(() => { result.current.validate() })
      expect(result.current.fieldErrors.totalAmount).toBe("transactions.form.error_total_amount")
    })

    it("sets transactionDate error when date is empty", () => {
      const { result } = renderHook(() =>
        useTransactionValidation(makeInput({ transactionDate: "" })),
      )
      act(() => { result.current.validate() })
      expect(result.current.fieldErrors.transactionDate).toBe("transactions.form.error_date")
    })
  })

  describe("validate() — optional field format errors", () => {
    it("sets price error when price is negative", () => {
      const { result } = renderHook(() =>
        useTransactionValidation(makeInput({ price: "-1" })),
      )
      act(() => { result.current.validate() })
      expect(result.current.fieldErrors.price).toBe("transactions.form.error_price")
    })

    it("does not set price error when price is empty (optional)", () => {
      const { result } = renderHook(() =>
        useTransactionValidation(makeInput({ price: "" })),
      )
      act(() => { result.current.validate() })
      expect(result.current.fieldErrors.price).toBeUndefined()
    })

    it("sets fxRate error when fxRate is zero", () => {
      const { result } = renderHook(() =>
        useTransactionValidation(makeInput({ fxRate: "0" })),
      )
      act(() => { result.current.validate() })
      expect(result.current.fieldErrors.fxRate).toBe("transactions.form.error_fx_rate")
    })

    it("does not set fxRate error when fxRate is empty (optional)", () => {
      const { result } = renderHook(() =>
        useTransactionValidation(makeInput({ fxRate: "" })),
      )
      act(() => { result.current.validate() })
      expect(result.current.fieldErrors.fxRate).toBeUndefined()
    })

    it("sets fee error when fee is negative", () => {
      const { result } = renderHook(() =>
        useTransactionValidation(makeInput({ fee: "-1" })),
      )
      act(() => { result.current.validate() })
      expect(result.current.fieldErrors.fee).toBe("transactions.form.error_fee")
    })
  })

  describe("validate() — sell quantity check", () => {
    it("sets quantity error when sell quantity exceeds available position", () => {
      const { result } = renderHook(() =>
        useTransactionValidation(makeInput({
          quantity: "20",
          shouldShowSellPicker: true,
          selectedSellablePosition: {
            ticker: "AAPL",
            fund_name: "Apple Inc.",
            quantity: 10,
            currency: "USD",
            value_source: "live_price",
          },
        })),
      )
      act(() => { result.current.validate() })
      expect(result.current.fieldErrors.quantity).toBe("transaction.insufficient_shares")
    })

    it("does not set error when sell quantity equals available position", () => {
      const { result } = renderHook(() =>
        useTransactionValidation(makeInput({
          quantity: "10",
          shouldShowSellPicker: true,
          selectedSellablePosition: {
            ticker: "AAPL",
            fund_name: "Apple Inc.",
            quantity: 10,
            currency: "USD",
            value_source: "live_price",
          },
        })),
      )
      act(() => { result.current.validate() })
      expect(result.current.fieldErrors.quantity).toBeUndefined()
    })
  })

  describe("setFieldErrors and setInsufficientBalance", () => {
    it("clears individual field error via setFieldErrors", () => {
      const { result } = renderHook(() =>
        useTransactionValidation(makeInput({ accountId: "" })),
      )
      act(() => { result.current.validate() })
      expect(result.current.fieldErrors.account).toBeDefined()

      act(() => {
        result.current.setFieldErrors((prev) => ({ ...prev, account: undefined }))
      })
      expect(result.current.fieldErrors.account).toBeUndefined()
    })

    it("sets insufficientBalance and clears it", () => {
      const { result } = renderHook(() => useTransactionValidation(makeInput()))
      act(() => {
        result.current.setInsufficientBalance({ available: 1000, required: 1500 })
      })
      expect(result.current.insufficientBalance).toEqual({ available: 1000, required: 1500 })

      act(() => { result.current.setInsufficientBalance(null) })
      expect(result.current.insufficientBalance).toBeNull()
    })
  })

  describe("multiple errors at once", () => {
    it("returns false and sets multiple errors on fully empty input", () => {
      const { result } = renderHook(() =>
        useTransactionValidation(makeInput({
          accountId: "",
          ticker: "",
          quantity: "",
          totalAmount: "",
          transactionDate: "",
        })),
      )
      let isValid = true
      act(() => { isValid = result.current.validate() })
      expect(isValid).toBe(false)
      expect(result.current.fieldErrors.account).toBeDefined()
      expect(result.current.fieldErrors.ticker).toBeDefined()
      expect(result.current.fieldErrors.quantity).toBeDefined()
      expect(result.current.fieldErrors.totalAmount).toBeDefined()
      expect(result.current.fieldErrors.transactionDate).toBeDefined()
    })
  })
})
