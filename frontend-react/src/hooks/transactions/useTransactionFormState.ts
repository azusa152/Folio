import { useEffect, useMemo, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { useAccounts } from "@/api/hooks/useAccounts"
import { useHoldings } from "@/api/hooks/useDashboard"
import { useRadarStocks } from "@/api/hooks/useRadar"
import { useIsMobile } from "@/hooks/use-mobile"
import { useCommandListScrollFix } from "@/hooks/useCommandListScrollFix"
import { useDebouncedValue } from "@/hooks/useDebouncedValue"
import { ELIGIBILITY_CHECK_WRAPPERS } from "@/lib/constants"
import { todayISO } from "@/lib/utils"
import { useTransactionQueries } from "./useTransactionQueries"
import type {
  TransactionType,
  StockCategory,
  NisaEligibleAssetItem,
  SellablePositionItem,
  NisaAssetTypeFilter,
} from "./types"

export interface UseTransactionFormStateProps {
  open: boolean
  defaultTicker?: string
  defaultHoldingId?: number
  defaultAccountId?: number
  defaultTransactionType?: TransactionType
  defaultCurrency?: string
}

/**
 * Manages all form field state, API queries, derived computed values, and
 * picker/reset handlers.  Error state is intentionally excluded — that lives
 * in `useTransactionValidation`.
 */
export function useTransactionFormState({
  open,
  defaultTicker,
  defaultHoldingId,
  defaultAccountId,
  defaultTransactionType,
  defaultCurrency,
}: UseTransactionFormStateProps) {
  const { t } = useTranslation()
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
  const [nisaPickerOpen, setNisaPickerOpen] = useState(false)
  const [nisaPickerSearch, setNisaPickerSearch] = useState("")
  const [nisaAssetTypeFilter, setNisaAssetTypeFilter] = useState<NisaAssetTypeFilter>("all")
  const [cachedSelectedNisaAsset, setCachedSelectedNisaAsset] = useState<NisaEligibleAssetItem | null>(null)
  const [sellPickerOpen, setSellPickerOpen] = useState(false)
  const [sellPickerSearch, setSellPickerSearch] = useState("")
  const [cachedSelectedSellablePosition, setCachedSelectedSellablePosition] =
    useState<SellablePositionItem | null>(null)

  const isMobile = useIsMobile()
  const commandListScrollFix = useCommandListScrollFix()
  const debouncedTicker = useDebouncedValue(ticker, 400)
  const debouncedNisaPickerSearch = useDebouncedValue(nisaPickerSearch, 300)

  const selectedAccountId = accountId ? Number(accountId) : null
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
  const shouldShowQuotaSummary =
    open &&
    transactionType === "BUY" &&
    (selectedWrapper === "nisa_tsumitate" || selectedWrapper === "nisa_growth")

  const queries = useTransactionQueries({
    open,
    accounts,
    selectedAccountId,
    selectedWrapper,
    selectedAccountBroker: selectedAccount?.broker || undefined,
    currency,
    ticker: debouncedTicker,
    totalAmount,
    transactionType,
    shouldShowNisaPicker,
    shouldShowSellPicker,
    shouldCheckEligibility,
    shouldSuggestRouting,
    shouldShowQuotaSummary,
    nisaStockFreeInput,
    nisaPickerSearch: debouncedNisaPickerSearch,
    nisaAssetTypeFilter,
  })

  const {
    nisaEligibleAssetsQuery,
    nisaFreeTickerInput,
    sellablePositionsQuery,
    eligibility,
    forcedCategory,
    suggestedAccount,
    routingSuggestedAccounts,
    splitRoutingPlan,
    canSplitPurchase,
    wrapperQuotaQuery,
    selectedQuota,
  } = queries

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
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setCategory((prev) => (prev === forcedCategory ? prev : forcedCategory))
  }, [forcedCategory, isCashMovement, isNewToRadar, open])

  useEffect(() => {
    const normalizedTicker = ticker.trim().toUpperCase()
    if (!normalizedTicker) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
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
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setNisaAssetTypeFilter("all")
    }
  }, [selectedWrapper])

  useEffect(() => {
    if (previousNisaFreeTickerInput.current === nisaFreeTickerInput) return
    previousNisaFreeTickerInput.current = nisaFreeTickerInput
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setTicker("")
    setCachedSelectedNisaAsset(null)
    setNisaPickerSearch("")
    setNisaPickerOpen(false)
  }, [nisaFreeTickerInput])

  useEffect(() => {
    const normalizedTicker = ticker.trim().toUpperCase()
    if (!normalizedTicker) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
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
    setNisaPickerOpen(false)
  }

  const onSelectSellablePosition = (item: SellablePositionItem) => {
    setTicker(item.ticker.toUpperCase())
    setCachedSelectedSellablePosition(item)
    setSellPickerSearch("")
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

  return {
    // Field state
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
    nisaPickerOpen,
    nisaPickerSearch,
    nisaAssetTypeFilter,
    sellPickerOpen,
    sellPickerSearch,
    // Field setters
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
    setNisaPickerOpen,
    setNisaPickerSearch,
    setNisaAssetTypeFilter,
    setSellPickerOpen,
    setSellPickerSearch,
    // Derived / computed
    selectedAccountId,
    selectedAccount,
    selectedWrapper,
    selectedCurrencyCashBalance: queries.selectedCurrencyCashBalance,
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
    cashBalances: queries.cashBalancesQuery.data,
    holdings,
    nisaEligibleAssetsQuery,
    sellablePositionsQuery,
    routingSuggestionQuery: queries.routingSuggestionQuery,
    eligibilityQuery: queries.eligibilityQuery,
    wrapperQuotaQuery,
    // Helpers
    isMobile,
    commandListScrollFix,
    // Handlers
    resetForm,
    applyCashMovementDefaults,
    computeTotalAmount,
    getSellValueSourceLabel,
    onSelectNisaAsset,
    onSelectSellablePosition,
    clearSellablePositionCache,
  }
}
