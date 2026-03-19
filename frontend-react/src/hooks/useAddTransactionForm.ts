import { useEffect, useMemo, useRef, useState } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import client from "@/api/client"
import { useAccountCashBalances, useAccountSellablePositions, useAccounts } from "@/api/hooks/useAccounts"
import { useEligibleAssets, useSuggestRouting, useWrapperEligibility, useWrapperQuota } from "@/api/hooks/useWrappers"
import { useAddTransaction } from "@/api/hooks/useTransactions"
import { useHoldings } from "@/api/hooks/useDashboard"
import { useRadarStocks } from "@/api/hooks/useRadar"
import { useIsMobile } from "@/hooks/use-mobile"
import { useCommandListScrollFix } from "@/hooks/useCommandListScrollFix"
import { useDebouncedValue } from "@/hooks/useDebouncedValue"
import { ELIGIBILITY_CHECK_WRAPPERS, STOCK_CATEGORIES } from "@/lib/constants"
import { getErrorMessage, todayISO } from "@/lib/utils"
import { parseEligibilityError, parseInsufficientBalance } from "@/lib/transactionErrors"

export type TransactionType = "BUY" | "SELL" | "DIVIDEND" | "DEPOSIT" | "WITHDRAWAL"
export type StockCategory = (typeof STOCK_CATEGORIES)[number]

export interface FieldErrors {
  account?: string
  ticker?: string
  quantity?: string
  price?: string
  totalAmount?: string
  transactionDate?: string
  fxRate?: string
  fee?: string
}

export type NisaEligibleAssetItem = {
  ticker: string
  fund_name?: string | null
  asset_type?: string | null
  trust_fee_pct?: number | null
}

export type SellablePositionItem = {
  ticker: string
  fund_name: string
  quantity: number
  cost_basis?: number | null
  current_price?: number | null
  market_value?: number | null
  currency: string
  value_source?: "live_price" | "cost_basis" | "unavailable"
}

export type NisaAssetTypeFilter = "all" | "mutual_fund" | "etf" | "stock" | "reit"

const REQUIRES_ACCOUNT = true

interface UseAddTransactionFormProps {
  open: boolean
  defaultTicker?: string
  defaultHoldingId?: number
  defaultAccountId?: number
  defaultTransactionType?: TransactionType
  defaultCurrency?: string
  onClose: () => void
  onOpenBuyForAccount?: (accountId: number, currency: string) => void
}

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
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const addTransactionMutation = useAddTransaction()
  const { data: holdings } = useHoldings()
  const { data: radarStocks, isLoading: isRadarStocksLoading } = useRadarStocks()
  const { data: accounts } = useAccounts(open)

  const initialTicker = defaultTicker?.toUpperCase() ?? ""
  const initialTransactionType = defaultTransactionType ?? "BUY"
  const initialCurrency = defaultCurrency?.toUpperCase() ?? "USD"

  const [transactionType, setTransactionType] = useState<TransactionType>(initialTransactionType)
  const [accountId, setAccountId] = useState(defaultAccountId != null ? String(defaultAccountId) : "")
  const [ticker, setTicker] = useState(initialTicker)
  const [holdingId, setHoldingId] = useState<string>(() => {
    if (defaultHoldingId != null) return String(defaultHoldingId)
    if (!holdings || !initialTicker) return ""
    const match = holdings.find((h) => h.ticker?.toUpperCase() === initialTicker && h.id != null)
    return match?.id != null ? String(match.id) : ""
  })
  const [quantity, setQuantity] = useState("")
  const [price, setPrice] = useState("")
  const [totalAmount, setTotalAmount] = useState("")
  const [currency, setCurrency] = useState(initialCurrency)
  const [fxRate, setFxRate] = useState("")
  const [fee, setFee] = useState("0")
  const [note, setNote] = useState("")
  const [thesis, setThesis] = useState("")
  const [category, setCategory] = useState<StockCategory>("Growth")
  const [transactionDate, setTransactionDate] = useState(todayISO)
  const [manualTotal, setManualTotal] = useState(false)
  const [moreOptionsOpen, setMoreOptionsOpen] = useState(false)
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [insufficientBalance, setInsufficientBalance] = useState<{ available: number; required: number } | null>(null)
  const [splitSubmitting, setSplitSubmitting] = useState(false)
  const [nisaPickerOpen, setNisaPickerOpen] = useState(false)
  const [nisaPickerSearch, setNisaPickerSearch] = useState("")
  const [nisaAssetTypeFilter, setNisaAssetTypeFilter] = useState<NisaAssetTypeFilter>("all")
  const [cachedSelectedNisaAsset, setCachedSelectedNisaAsset] = useState<NisaEligibleAssetItem | null>(null)
  const [sellPickerOpen, setSellPickerOpen] = useState(false)
  const [sellPickerSearch, setSellPickerSearch] = useState("")
  const [cachedSelectedSellablePosition, setCachedSelectedSellablePosition] = useState<SellablePositionItem | null>(null)

  const isMobile = useIsMobile()
  const commandListScrollFix = useCommandListScrollFix()
  const debouncedTicker = useDebouncedValue(ticker, 400)
  const debouncedNisaPickerSearch = useDebouncedValue(nisaPickerSearch, 300)

  const selectedAccountId = accountId ? Number(accountId) : null
  const { data: cashBalances } = useAccountCashBalances(selectedAccountId, open)
  const selectedCurrencyCashBalance =
    (cashBalances ?? []).find((b) => b.currency.toUpperCase() === currency.toUpperCase())?.balance ?? null
  const selectedAccount = (accounts ?? []).find((account) => account.id === selectedAccountId)
  const selectedWrapper =
    typeof selectedAccount?.tax_wrapper === "string" ? selectedAccount.tax_wrapper.trim().toLowerCase() : ""
  const hasNoAccounts = (accounts ?? []).length === 0
  const isCashMovement = transactionType === "DEPOSIT" || transactionType === "WITHDRAWAL"

  const isNewToRadar = useMemo(() => {
    if (isRadarStocksLoading) return false
    if (isCashMovement) return false
    const normalizedTicker = ticker.trim().toUpperCase()
    if (!normalizedTicker) return false
    return !(radarStocks ?? []).some((stock) => stock.ticker.toUpperCase() === normalizedTicker)
  }, [isCashMovement, isRadarStocksLoading, radarStocks, ticker])

  const shouldCheckEligibility =
    open &&
    transactionType === "BUY" &&
    !isCashMovement &&
    ELIGIBILITY_CHECK_WRAPPERS.has(selectedWrapper) &&
    !!debouncedTicker.trim()
  const shouldSuggestRouting =
    open &&
    transactionType === "BUY" &&
    !isCashMovement &&
    !!debouncedTicker.trim() &&
    !!totalAmount &&
    Number(totalAmount) > 0
  const shouldShowNisaPicker =
    open &&
    transactionType === "BUY" &&
    !isCashMovement &&
    (selectedWrapper === "nisa_tsumitate" || selectedWrapper === "nisa_growth")
  const shouldShowSellPicker =
    open &&
    (transactionType === "SELL" || transactionType === "DIVIDEND") &&
    !isCashMovement &&
    selectedAccountId != null
  const nisaStockFreeInput =
    shouldShowNisaPicker && selectedWrapper === "nisa_growth" && nisaAssetTypeFilter === "stock"
  const nisaEligibleAssetsQuery = useEligibleAssets(shouldShowNisaPicker ? selectedWrapper : undefined, {
    search: debouncedNisaPickerSearch || undefined,
    assetType: nisaAssetTypeFilter === "all" ? undefined : nisaAssetTypeFilter,
    limit: 50,
    enabled: shouldShowNisaPicker && !nisaStockFreeInput,
  })
  const nisaReitFreeInput =
    shouldShowNisaPicker &&
    selectedWrapper === "nisa_growth" &&
    nisaAssetTypeFilter === "reit" &&
    nisaEligibleAssetsQuery.isFetched &&
    (nisaEligibleAssetsQuery.data?.items?.length ?? 0) === 0
  const nisaFreeTickerInput = nisaStockFreeInput || nisaReitFreeInput
  const sellablePositionsQuery = useAccountSellablePositions(selectedAccountId, shouldShowSellPicker)
  const filteredSellablePositions = useMemo(() => {
    const keyword = sellPickerSearch.trim().toLowerCase()
    const rows = (sellablePositionsQuery.data ?? []) as SellablePositionItem[]
    if (!keyword) return rows
    return rows.filter((item) => {
      const tickerLower = item.ticker.toLowerCase()
      const fundNameLower = (item.fund_name || "").toLowerCase()
      return tickerLower.includes(keyword) || fundNameLower.includes(keyword)
    })
  }, [sellPickerSearch, sellablePositionsQuery.data])
  const selectedSellablePosition = useMemo(() => {
    const normalizedTicker = ticker.trim().toUpperCase()
    if (!normalizedTicker) return null
    return (
      ((sellablePositionsQuery.data ?? []) as SellablePositionItem[]).find(
        (item) => item.ticker.toUpperCase() === normalizedTicker,
      ) ?? null
    )
  }, [ticker, sellablePositionsQuery.data])
  const selectedSellablePositionForDisplay = selectedSellablePosition ?? cachedSelectedSellablePosition
  const selectedNisaAsset = useMemo(() => {
    const normalizedTicker = ticker.trim().toUpperCase()
    if (!normalizedTicker) return null
    return (
      (nisaEligibleAssetsQuery.data?.items ?? []).find(
        (item) => item.ticker.toUpperCase() === normalizedTicker,
      ) ?? null
    )
  }, [ticker, nisaEligibleAssetsQuery.data?.items])
  const selectedNisaAssetForDisplay = selectedNisaAsset ?? cachedSelectedNisaAsset
  const routingSuggestionQuery = useSuggestRouting(
    debouncedTicker,
    Number.isFinite(Number(totalAmount)) ? Number(totalAmount) : null,
    shouldSuggestRouting,
  )
  const eligibilityQuery = useWrapperEligibility(
    selectedWrapper || undefined,
    debouncedTicker,
    selectedAccount?.broker || undefined,
    shouldCheckEligibility,
  )
  const eligibility = eligibilityQuery.data
  const shouldShowQuotaSummary =
    open &&
    transactionType === "BUY" &&
    (selectedWrapper === "nisa_tsumitate" || selectedWrapper === "nisa_growth")
  const wrapperQuotaQuery = useWrapperQuota(shouldShowQuotaSummary)
  const selectedQuota = shouldShowQuotaSummary ? wrapperQuotaQuery.data?.quotas?.[selectedWrapper] : undefined
  const forcedCategory = useMemo<StockCategory | null>(() => {
    if (selectedWrapper === "nisa_tsumitate") return "Mutual_Fund"
    if (eligibility?.asset_type === "mutual_fund") return "Mutual_Fund"
    return null
  }, [eligibility?.asset_type, selectedWrapper])
  const suggestedAccount = useMemo(() => {
    const suggestedWrapper = eligibility?.suggested_wrapper
    if (!suggestedWrapper) return null
    return (accounts ?? []).find((account) => {
      if (account.id == null || account.id === selectedAccountId) return false
      const wrapper = typeof account.tax_wrapper === "string" ? account.tax_wrapper.toLowerCase() : ""
      return wrapper === suggestedWrapper
    })
  }, [accounts, eligibility?.suggested_wrapper, selectedAccountId])
  const routingSuggestedAccounts = useMemo(() => {
    const byWrapper = new Map<string, { id: number; currency: string }>()
    for (const account of accounts ?? []) {
      if (account.id == null) continue
      const wrapper = typeof account.tax_wrapper === "string" ? account.tax_wrapper.toLowerCase() : ""
      if (!wrapper || byWrapper.has(wrapper)) continue
      byWrapper.set(wrapper, { id: account.id, currency: (account.currency || "USD").toUpperCase() })
    }
    return byWrapper
  }, [accounts])
  const splitRoutingPlan = useMemo(() => {
    const suggestions = routingSuggestionQuery.data?.suggestions ?? []
    return suggestions
      .map((item) => ({
        wrapper: item.wrapper,
        amount: Number(item.amount),
        account: routingSuggestedAccounts.get(item.wrapper) ?? null,
      }))
      .filter((item) => item.amount > 0)
  }, [routingSuggestionQuery.data?.suggestions, routingSuggestedAccounts])
  const canSplitPurchase =
    transactionType === "BUY" &&
    splitRoutingPlan.length >= 2 &&
    splitRoutingPlan.every((item) => item.account != null)

  const holdingOptions = useMemo(
    () =>
      (holdings ?? [])
        .filter((h) => h.id != null)
        .map((h) => ({ id: h.id, ticker: h.ticker })),
    [holdings],
  )
  const inferredHoldingId = useMemo(() => {
    if (defaultHoldingId != null) return String(defaultHoldingId)
    const match = holdingOptions.find((option) => option.ticker.toUpperCase() === initialTicker)
    return match ? String(match.id) : ""
  }, [defaultHoldingId, holdingOptions, initialTicker])

  const previousNisaFreeTickerInput = useRef(nisaFreeTickerInput)

  useEffect(() => {
    if (!open || isCashMovement || !isNewToRadar || !forcedCategory) return
    setCategory((prev) => (prev === forcedCategory ? prev : forcedCategory))
  }, [forcedCategory, isCashMovement, isNewToRadar, open])

  useEffect(() => {
    const normalizedTicker = ticker.trim().toUpperCase()
    if (!normalizedTicker) {
      setCachedSelectedNisaAsset(null)
      return
    }
    const matched = (nisaEligibleAssetsQuery.data?.items ?? []).find(
      (item) => item.ticker.toUpperCase() === normalizedTicker,
    )
    if (!matched) return
    setCachedSelectedNisaAsset((prev) => {
      if (
        prev?.ticker.toUpperCase() === matched.ticker.toUpperCase() &&
        prev?.fund_name === matched.fund_name &&
        prev?.trust_fee_pct === matched.trust_fee_pct
      ) {
        return prev
      }
      return matched
    })
  }, [ticker, nisaEligibleAssetsQuery.data?.items])

  useEffect(() => {
    if (selectedWrapper !== "nisa_growth") {
      setNisaAssetTypeFilter("all")
    }
  }, [selectedWrapper])

  useEffect(() => {
    if (previousNisaFreeTickerInput.current === nisaFreeTickerInput) return
    previousNisaFreeTickerInput.current = nisaFreeTickerInput
    setTicker("")
    setCachedSelectedNisaAsset(null)
    setNisaPickerSearch("")
    setNisaPickerOpen(false)
    setFieldErrors((prev) => ({ ...prev, ticker: undefined }))
    setInsufficientBalance(null)
  }, [nisaFreeTickerInput])

  useEffect(() => {
    const normalizedTicker = ticker.trim().toUpperCase()
    if (!normalizedTicker) {
      setCachedSelectedSellablePosition(null)
      return
    }
    const matched = ((sellablePositionsQuery.data ?? []) as SellablePositionItem[]).find(
      (item) => item.ticker.toUpperCase() === normalizedTicker,
    )
    if (!matched) return
    setCachedSelectedSellablePosition((prev) => {
      if (
        prev?.ticker.toUpperCase() === matched.ticker.toUpperCase() &&
        prev?.fund_name === matched.fund_name &&
        prev?.quantity === matched.quantity &&
        prev?.market_value === matched.market_value
      ) {
        return prev
      }
      return matched
    })
  }, [ticker, sellablePositionsQuery.data])

  const onSelectNisaAsset = (item: NisaEligibleAssetItem) => {
    setTicker(item.ticker.toUpperCase())
    setCachedSelectedNisaAsset(item)
    setNisaPickerSearch("")
    setFieldErrors((prev) => ({ ...prev, ticker: undefined }))
    setInsufficientBalance(null)
    setNisaPickerOpen(false)
  }

  const onSelectSellablePosition = (item: SellablePositionItem) => {
    setTicker(item.ticker.toUpperCase())
    setCachedSelectedSellablePosition(item)
    setSellPickerSearch("")
    setFieldErrors((prev) => ({ ...prev, ticker: undefined }))
    setInsufficientBalance(null)
    setSellPickerOpen(false)
  }

  const clearSellablePositionCache = () => setCachedSelectedSellablePosition(null)

  const getSellValueSourceLabel = (valueSource?: SellablePositionItem["value_source"]): string | null => {
    if (!valueSource || valueSource === "live_price") return null
    if (valueSource === "cost_basis") return t("transactions.sell_picker.value_source_cost_basis")
    return t("transactions.sell_picker.value_source_unavailable")
  }

  const resetForm = (options?: { keepDefaultTicker?: boolean; keepDefaultHoldingId?: boolean }) => {
    setTransactionType(initialTransactionType)
    setAccountId(defaultAccountId != null ? String(defaultAccountId) : "")
    setTicker(options?.keepDefaultTicker ? initialTicker : "")
    setHoldingId(options?.keepDefaultHoldingId ? inferredHoldingId : "")
    setQuantity("")
    setPrice("")
    setTotalAmount("")
    setCurrency(initialCurrency)
    setFxRate("")
    setFee("0")
    setNote("")
    setThesis("")
    setCategory("Growth")
    setTransactionDate(todayISO())
    setManualTotal(false)
    setMoreOptionsOpen(false)
    setFieldErrors({})
    setInsufficientBalance(null)
    setNisaPickerOpen(false)
    setNisaPickerSearch("")
    setNisaAssetTypeFilter("all")
    setCachedSelectedNisaAsset(null)
    setSellPickerOpen(false)
    setSellPickerSearch("")
    setCachedSelectedSellablePosition(null)
  }

  const applyCashMovementDefaults = (nextCurrency: string) => {
    setTicker(nextCurrency.toUpperCase())
    setQuantity("1")
    setPrice("")
    setManualTotal(true)
  }

  const computeTotalAmount = (nextQuantity: string, nextPrice: string): string => {
    const quantityNum = Number(nextQuantity)
    const priceNum = Number(nextPrice)
    if (!nextQuantity || !nextPrice || Number.isNaN(quantityNum) || Number.isNaN(priceNum)) return ""
    const computed = quantityNum * priceNum
    return Number.isFinite(computed) ? String(computed) : ""
  }

  const validate = (): boolean => {
    const nextErrors: FieldErrors = {}
    const quantityNum = Number(quantity)
    const priceNum = Number(price)
    const totalAmountNum = Number(totalAmount)
    const fxRateNum = Number(fxRate)
    const feeNum = Number(fee)

    if (REQUIRES_ACCOUNT && !accountId) nextErrors.account = t("transactions.form.account_required")
    if (!isCashMovement && !ticker.trim()) nextErrors.ticker = t("transactions.form.error_ticker")
    if (!isCashMovement && (!quantity || Number.isNaN(quantityNum) || quantityNum <= 0)) {
      nextErrors.quantity = t("transactions.form.error_quantity")
    }
    if (!isCashMovement && shouldShowSellPicker && selectedSellablePosition && quantityNum > selectedSellablePosition.quantity) {
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
    if (fxRate && (Number.isNaN(fxRateNum) || fxRateNum <= 0)) nextErrors.fxRate = t("transactions.form.error_fx_rate")
    if (fee && (Number.isNaN(feeNum) || feeNum < 0)) nextErrors.fee = t("transactions.form.error_fee")

    setFieldErrors(nextErrors)
    return Object.keys(nextErrors).length === 0
  }

  const invalidateTransactionQueries = () => {
    const keys = [
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
    ]
    keys.forEach((queryKey) => {
      queryClient.invalidateQueries({ queryKey, refetchType: "all" })
    })
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

  const handleSubmit = () => {
    if (!validate()) return
    if (shouldCheckEligibility && eligibility && !eligibility.eligible) {
      toast.error(t("eligibility.not_eligible"))
      return
    }
    const requiredAmount = Number(totalAmount) + Number(fee || "0")
    const availableAmount = selectedCurrencyCashBalance ?? 0
    if (transactionType === "BUY" && selectedAccountId != null && requiredAmount > availableAmount) {
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

  return {
    // State values
    transactionType,
    accountId,
    ticker,
    holdingId,
    quantity,
    price,
    totalAmount,
    currency,
    fxRate,
    fee,
    note,
    thesis,
    category,
    transactionDate,
    manualTotal,
    moreOptionsOpen,
    fieldErrors,
    insufficientBalance,
    splitSubmitting,
    nisaPickerOpen,
    nisaPickerSearch,
    nisaAssetTypeFilter,
    sellPickerOpen,
    sellPickerSearch,
    // Setters
    setTransactionType,
    setAccountId,
    setTicker,
    setHoldingId,
    setQuantity,
    setPrice,
    setTotalAmount,
    setCurrency,
    setFxRate,
    setFee,
    setNote,
    setThesis,
    setCategory,
    setTransactionDate,
    setManualTotal,
    setMoreOptionsOpen,
    setFieldErrors,
    setInsufficientBalance,
    setNisaPickerOpen,
    setNisaPickerSearch,
    setNisaAssetTypeFilter,
    setSellPickerOpen,
    setSellPickerSearch,
    // Computed/derived values
    selectedAccountId,
    selectedAccount,
    selectedWrapper,
    selectedCurrencyCashBalance,
    hasNoAccounts,
    isCashMovement,
    isNewToRadar,
    shouldCheckEligibility,
    shouldSuggestRouting,
    shouldShowNisaPicker,
    shouldShowSellPicker,
    nisaStockFreeInput,
    nisaFreeTickerInput,
    filteredSellablePositions,
    selectedSellablePosition,
    selectedSellablePositionForDisplay,
    selectedNisaAssetForDisplay,
    eligibility,
    forcedCategory,
    suggestedAccount,
    routingSuggestedAccounts,
    splitRoutingPlan,
    canSplitPurchase,
    holdingOptions,
    shouldShowQuotaSummary,
    selectedQuota,
    // Queries
    accounts,
    cashBalances,
    holdings,
    nisaEligibleAssetsQuery,
    sellablePositionsQuery,
    routingSuggestionQuery,
    eligibilityQuery,
    wrapperQuotaQuery,
    // Helpers
    addTransactionMutation,
    isMobile,
    commandListScrollFix,
    // Handlers
    resetForm,
    applyCashMovementDefaults,
    computeTotalAmount,
    validate,
    invalidateTransactionQueries,
    createSplitTransactions,
    handleSubmit,
    getSellValueSourceLabel,
    onSelectNisaAsset,
    onSelectSellablePosition,
    clearSellablePositionCache,
  }
}
