import { useEffect, useRef } from "react"
import {
  useTransactionFormState,
  type UseTransactionFormStateProps,
} from "@/hooks/transactions/useTransactionFormState"
import { useTransactionValidation } from "@/hooks/transactions/useTransactionValidation"
import { useTransactionSubmit } from "@/hooks/transactions/useTransactionSubmit"
import type { NisaEligibleAssetItem, SellablePositionItem } from "@/hooks/transactions/types"

// ---------------------------------------------------------------------------
// Public types — defined in transactions/types.ts; re-exported here so all
// existing consumers (components, pages) can continue importing from this path.
// ---------------------------------------------------------------------------

export type {
  TransactionType,
  StockCategory,
  FieldErrors,
  NisaEligibleAssetItem,
  SellablePositionItem,
  NisaAssetTypeFilter,
} from "@/hooks/transactions/types"

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface UseAddTransactionFormProps extends UseTransactionFormStateProps {
  onClose: () => void
  onOpenBuyForAccount?: (accountId: number, currency: string) => void
}

// ---------------------------------------------------------------------------
// Coordinator hook
// ---------------------------------------------------------------------------

/**
 * Thin coordinator: composes `useTransactionFormState` (field state + queries),
 * `useTransactionValidation` (error state + validate), and
 * `useTransactionSubmit` (handleSubmit + createSplitTransactions), then bridges
 * the three by wiring resetForm and validation-clearing into picker handlers.
 */
export function useAddTransactionForm({
  open,
  defaultTicker,
  defaultHoldingId,
  defaultAccountId,
  defaultTransactionType,
  defaultCurrency,
  onClose,
  onOpenBuyForAccount,
}: UseAddTransactionFormProps) {
  const formState = useTransactionFormState({
    open,
    defaultTicker,
    defaultHoldingId,
    defaultAccountId,
    defaultTransactionType,
    defaultCurrency,
  })

  const {
    accountId,
    ticker,
    quantity,
    price,
    totalAmount,
    fxRate,
    fee,
    transactionDate,
    currency,
    note,
    thesis,
    holdingId,
    category,
    isCashMovement,
    isNewToRadar,
    shouldCheckEligibility,
    shouldShowSellPicker,
    selectedSellablePosition,
    selectedCurrencyCashBalance,
    transactionType,
    selectedAccountId,
    canSplitPurchase,
    splitRoutingPlan,
    eligibility,
    resetForm: formStateResetForm,
  } = formState

  const validation = useTransactionValidation({
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
  })

  const { validate, setFieldErrors, setInsufficientBalance } = validation

  const resetForm = (options?: { keepDefaultTicker?: boolean; keepDefaultHoldingId?: boolean }) => {
    formStateResetForm(options)
    setFieldErrors({})
    setInsufficientBalance(null)
  }

  const submit = useTransactionSubmit({
    ticker,
    quantity,
    price,
    totalAmount,
    fee,
    fxRate,
    currency,
    note,
    thesis,
    category,
    transactionDate,
    holdingId,
    accountId,
    transactionType,
    isCashMovement,
    isNewToRadar,
    shouldCheckEligibility,
    canSplitPurchase,
    splitRoutingPlan,
    eligibility,
    selectedCurrencyCashBalance,
    selectedAccountId,
    validate,
    setInsufficientBalance,
    resetForm,
    onClose,
    onOpenBuyForAccount,
  })

  // Clear ticker error and insufficient balance when the NISA free-input mode
  // toggles — formState owns the field reset; validation state is cleared here.
  const prevNisaFreeTickerInput = useRef(formState.nisaFreeTickerInput)
  useEffect(() => {
    if (prevNisaFreeTickerInput.current === formState.nisaFreeTickerInput) return
    prevNisaFreeTickerInput.current = formState.nisaFreeTickerInput
    setFieldErrors((prev) => ({ ...prev, ticker: undefined }))
    setInsufficientBalance(null)
  }, [formState.nisaFreeTickerInput, setFieldErrors, setInsufficientBalance])

  // Wrappers that combine formState handlers with validation state clearing.
  const onSelectNisaAsset = (item: NisaEligibleAssetItem) => {
    formState.onSelectNisaAsset(item)
    setFieldErrors((prev) => ({ ...prev, ticker: undefined }))
    setInsufficientBalance(null)
  }
  const onSelectSellablePosition = (item: SellablePositionItem) => {
    formState.onSelectSellablePosition(item)
    setFieldErrors((prev) => ({ ...prev, ticker: undefined }))
    setInsufficientBalance(null)
  }

  return {
    ...formState,
    ...validation,
    ...submit,
    // Override formState handlers with versions that also clear validation state
    onSelectNisaAsset,
    onSelectSellablePosition,
    resetForm,
  }
}
