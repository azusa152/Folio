import { useState } from "react"
import { useTranslation } from "react-i18next"
import type { FieldErrors, SellablePositionItem } from "@/hooks/useAddTransactionForm"

export interface TransactionValidationInput {
  accountId: string
  ticker: string
  quantity: string
  price: string
  totalAmount: string
  fxRate: string
  fee: string
  transactionDate: string
  isCashMovement: boolean
  shouldShowSellPicker: boolean
  selectedSellablePosition: SellablePositionItem | null
}

/**
 * Owns all validation error state and the `validate()` function.
 * Receives derived form state as input; the coordinator passes these
 * from `useTransactionFormState`.
 */
export function useTransactionValidation(input: TransactionValidationInput) {
  const { t } = useTranslation()
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [insufficientBalance, setInsufficientBalance] = useState<{
    available: number
    required: number
  } | null>(null)

  const validate = (): boolean => {
    const {
      accountId,
      ticker,
      quantity,
      price,
      totalAmount,
      fxRate,
      fee,
      transactionDate,
      isCashMovement,
      shouldShowSellPicker,
      selectedSellablePosition,
    } = input

    const nextErrors: FieldErrors = {}
    const quantityNum = Number(quantity)
    const priceNum = Number(price)
    const totalAmountNum = Number(totalAmount)
    const fxRateNum = Number(fxRate)
    const feeNum = Number(fee)

    if (!accountId) nextErrors.account = t("transactions.form.account_required")
    if (!isCashMovement && !ticker.trim()) nextErrors.ticker = t("transactions.form.error_ticker")
    if (!isCashMovement && (!quantity || Number.isNaN(quantityNum) || quantityNum <= 0)) {
      nextErrors.quantity = t("transactions.form.error_quantity")
    }
    if (
      !isCashMovement &&
      shouldShowSellPicker &&
      selectedSellablePosition &&
      quantityNum > selectedSellablePosition.quantity
    ) {
      nextErrors.quantity = t("transaction.insufficient_shares", {
        available: selectedSellablePosition.quantity,
        required: quantityNum,
      })
    }
    if (!isCashMovement && price && (Number.isNaN(priceNum) || priceNum < 0)) {
      nextErrors.price = t("transactions.form.error_price")
    }
    if (!totalAmount || Number.isNaN(totalAmountNum) || totalAmountNum <= 0) {
      nextErrors.totalAmount = t("transactions.form.error_total_amount")
    }
    if (!transactionDate) nextErrors.transactionDate = t("transactions.form.error_date")
    if (fxRate && (Number.isNaN(fxRateNum) || fxRateNum <= 0))
      nextErrors.fxRate = t("transactions.form.error_fx_rate")
    if (fee && (Number.isNaN(feeNum) || feeNum < 0)) nextErrors.fee = t("transactions.form.error_fee")

    setFieldErrors(nextErrors)
    return Object.keys(nextErrors).length === 0
  }

  return {
    fieldErrors,
    setFieldErrors,
    insufficientBalance,
    setInsufficientBalance,
    validate,
  }
}
