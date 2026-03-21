import { useState } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import client from "@/api/client"
import { useAddTransaction } from "@/api/hooks/useTransactions"
import { getErrorMessage } from "@/lib/utils"
import { parseEligibilityError, parseInsufficientBalance } from "@/lib/transactionErrors"
import type { TransactionType, StockCategory } from "./types"

interface SplitRoutingItem {
  wrapper: string
  amount: number
  account: { id: number; currency: string } | null
}

interface EligibilityData {
  eligible: boolean
  suggested_wrapper?: string | null
  reasons?: string[]
}

interface Props {
  ticker: string
  quantity: string
  price: string
  totalAmount: string
  fee: string
  fxRate: string
  currency: string
  note: string
  thesis: string
  category: StockCategory
  transactionDate: string
  holdingId: string
  accountId: string
  transactionType: TransactionType
  isCashMovement: boolean
  isNewToRadar: boolean
  shouldCheckEligibility: boolean
  canSplitPurchase: boolean
  splitRoutingPlan: SplitRoutingItem[]
  eligibility: EligibilityData | undefined | null
  selectedCurrencyCashBalance: number | null
  selectedAccountId: number | null
  validate: () => boolean
  setInsufficientBalance: (v: { available: number; required: number } | null) => void
  resetForm: (options?: { keepDefaultTicker?: boolean; keepDefaultHoldingId?: boolean }) => void
  onClose: () => void
  onOpenBuyForAccount?: (accountId: number, currency: string) => void
}

const INVALIDATION_KEYS = [
  ["transactions"],
  ["holdings"],
  ["rebalance"],
  ["drawdown"],
  ["risk-metrics"],
  ["currency-exposure"],
  ["stress-test"],
  ["snapshots"],
  ["account-cash-balances"],
  ["accounts"],
  ["account-summary"],
  ["account-positions"],
  ["account-transactions"],
  ["account-sellable-positions"],
  ["stocks"],
  ["wrapper-quota"],
  ["wrapper-restoration"],
] as const

export function useTransactionSubmit({
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
}: Props) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const addTransactionMutation = useAddTransaction()
  const [splitSubmitting, setSplitSubmitting] = useState(false)

  const invalidateTransactionQueries = () => {
    INVALIDATION_KEYS.forEach((queryKey) => {
      queryClient.invalidateQueries({ queryKey, refetchType: "all" })
    })
  }

  const handleSubmit = () => {
    if (!validate()) return
    if (shouldCheckEligibility && eligibility && !eligibility.eligible) {
      toast.error(t("eligibility.not_eligible"))
      return
    }
    const requiredAmount = Number(totalAmount) + Number(fee || "0")
    const availableAmount = selectedCurrencyCashBalance ?? 0
    if (
      transactionType === "BUY" &&
      selectedAccountId != null &&
      requiredAmount > availableAmount
    ) {
      setInsufficientBalance({ available: availableAmount, required: requiredAmount })
      return
    }
    addTransactionMutation.mutate(
      {
        account_id: Number(accountId),
        holding_id: holdingId ? Number(holdingId) : undefined,
        ticker: isCashMovement ? currency.toUpperCase() : ticker.trim(),
        transaction_type: transactionType,
        quantity: isCashMovement ? 1 : Number(quantity),
        price: !isCashMovement && price ? Number(price) : undefined,
        total_amount: Number(totalAmount),
        currency,
        fx_rate: fxRate ? Number(fxRate) : undefined,
        fee: fee ? Number(fee) : 0,
        note: note.trim(),
        thesis: thesis.trim() || undefined,
        category: isNewToRadar ? category : undefined,
        transaction_date: transactionDate,
      },
      {
        onSuccess: (data) => {
          const selectedId = accountId ? Number(accountId) : null
          if (transactionType === "DEPOSIT" && selectedId != null) {
            toast.success(t("transactions.toast.created"), {
              description: t("transactions.form.deposit_success_trade"),
              action: onOpenBuyForAccount
                ? {
                    label: t("transactions.type.buy"),
                    onClick: () => onOpenBuyForAccount(selectedId, currency),
                  }
                : undefined,
            })
          } else {
            toast.success(t("transactions.toast.created"))
          }
          if (data.auto_radar) {
            toast.info(t("holding.auto_radar"))
          }
          resetForm({ keepDefaultTicker: true, keepDefaultHoldingId: true })
          onClose()
        },
        onError: (err: unknown) => {
          const insufficient = parseInsufficientBalance(err)
          if (insufficient) {
            setInsufficientBalance(insufficient)
            return
          }
          const eligibilityError = parseEligibilityError(err)
          if (eligibilityError) {
            setInsufficientBalance(null)
            const reasonText = eligibilityError.reasons.length
              ? t(eligibilityError.reasons[0], { defaultValue: eligibilityError.reasons[0] })
              : t("eligibility.not_eligible")
            toast.error(reasonText)
            return
          }
          toast.error(getErrorMessage(err) || t("common.error"))
        },
      },
    )
  }

  const createSplitTransactions = async () => {
    if (!canSplitPurchase) return
    if (!validate()) return
    if (shouldCheckEligibility && eligibility && !eligibility.eligible) {
      toast.error(t("eligibility.not_eligible"))
      return
    }

    const totalAmountNumber = Number(totalAmount)
    const quantityNumber = Number(quantity)
    const feeNumber = Number(fee || "0")
    if (!Number.isFinite(totalAmountNumber) || totalAmountNumber <= 0) return
    if (!Number.isFinite(quantityNumber) || quantityNumber <= 0) return

    const normalizedTicker = ticker.trim().toUpperCase()
    let remainingAmount = totalAmountNumber
    let remainingQuantity = quantityNumber
    let remainingFee = feeNumber

    const payloads = splitRoutingPlan.map((item, index) => {
      const isLast = index === splitRoutingPlan.length - 1
      const ratio = totalAmountNumber > 0 ? item.amount / totalAmountNumber : 0
      const splitAmount = isLast ? remainingAmount : Number(item.amount.toFixed(2))
      const splitQuantity = isLast
        ? Number(remainingQuantity.toFixed(6))
        : Number((quantityNumber * ratio).toFixed(6))
      const splitFee = isLast ? remainingFee : Number((feeNumber * ratio).toFixed(2))
      remainingAmount = Number((remainingAmount - splitAmount).toFixed(2))
      remainingQuantity = Number((remainingQuantity - splitQuantity).toFixed(6))
      remainingFee = Number((remainingFee - splitFee).toFixed(2))
      const account = item.account
      return {
        account_id: account ? account.id : Number(accountId),
        holding_id: holdingId ? Number(holdingId) : undefined,
        ticker: normalizedTicker,
        transaction_type: "BUY" as const,
        quantity: splitQuantity,
        price: price ? Number(price) : undefined,
        total_amount: splitAmount,
        currency: account ? account.currency : currency,
        fx_rate: fxRate ? Number(fxRate) : undefined,
        fee: splitFee,
        note: note.trim(),
        thesis: thesis.trim() || undefined,
        category: isNewToRadar ? category : undefined,
        transaction_date: transactionDate,
      }
    })

    setSplitSubmitting(true)
    const createdTransactionIds: number[] = []
    try {
      for (const payload of payloads) {
        const created = await addTransactionMutation.mutateAsync(payload)
        if (created.id != null) {
          createdTransactionIds.push(Number(created.id))
        }
      }
      invalidateTransactionQueries()
      toast.success(t("smart_actions.split_success", { count: payloads.length }))
      resetForm({ keepDefaultTicker: true, keepDefaultHoldingId: true })
      onClose()
    } catch (err) {
      if (createdTransactionIds.length > 0) {
        for (const txnId of [...createdTransactionIds].reverse()) {
          const { error } = await client.DELETE("/transactions/{txn_id}", {
            params: { path: { txn_id: txnId } },
          })
          if (error) {
            toast.error(t("smart_actions.split_rollback_failed"))
            break
          }
        }
        invalidateTransactionQueries()
      }
      const insufficient = parseInsufficientBalance(err)
      if (insufficient) {
        setInsufficientBalance(insufficient)
        return
      }
      const eligibilityError = parseEligibilityError(err)
      if (eligibilityError) {
        const reasonText = eligibilityError.reasons.length
          ? t(eligibilityError.reasons[0], { defaultValue: eligibilityError.reasons[0] })
          : t("eligibility.not_eligible")
        toast.error(reasonText)
        return
      }
      toast.error(getErrorMessage(err) || t("common.error"))
    } finally {
      setSplitSubmitting(false)
    }
  }

  return {
    addTransactionMutation,
    splitSubmitting,
    invalidateTransactionQueries,
    handleSubmit,
    createSplitTransactions,
  }
}
