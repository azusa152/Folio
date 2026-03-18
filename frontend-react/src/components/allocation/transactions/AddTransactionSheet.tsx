import { useEffect, useMemo, useState } from "react"
import { Building2, Check, ChevronsUpDown, Loader2 } from "lucide-react"
import { useQueryClient } from "@tanstack/react-query"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import client from "@/api/client"
import { useAccountCashBalances, useAccountSellablePositions, useAccounts } from "@/api/hooks/useAccounts"
import { useEligibleAssets, useSuggestRouting, useWrapperEligibility, useWrapperQuota } from "@/api/hooks/useWrappers"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command"
import { Input } from "@/components/ui/input"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { useAddTransaction } from "@/api/hooks/useTransactions"
import { EligibilityBadge } from "@/components/common/EligibilityBadge"
import { useHoldings } from "@/api/hooks/useDashboard"
import { useRadarStocks } from "@/api/hooks/useRadar"
import { useIsMobile } from "@/hooks/use-mobile"
import { useCommandListScrollFix } from "@/hooks/useCommandListScrollFix"
import { useDebouncedValue } from "@/hooks/useDebouncedValue"
import { DISPLAY_CURRENCIES, STOCK_CATEGORIES } from "@/lib/constants"
import { cn, getErrorMessage } from "@/lib/utils"

interface Props {
  open: boolean
  onClose: () => void
  defaultTicker?: string
  defaultHoldingId?: number
  defaultAccountId?: number
  defaultTransactionType?: TransactionType
  defaultCurrency?: string
  onOpenBuyForAccount?: (accountId: number, currency: string) => void
  onOpenAccounts?: () => void
}

export type TransactionType = "BUY" | "SELL" | "DIVIDEND" | "DEPOSIT" | "WITHDRAWAL"
type StockCategory = (typeof STOCK_CATEGORIES)[number]
const ELIGIBILITY_CHECK_WRAPPERS = new Set(["nisa_tsumitate", "nisa_growth", "ideco"])

interface FieldErrors {
  account?: string
  ticker?: string
  quantity?: string
  price?: string
  totalAmount?: string
  transactionDate?: string
  fxRate?: string
  fee?: string
}

type NisaEligibleAssetItem = {
  ticker: string
  fund_name?: string | null
  asset_type?: string | null
  trust_fee_pct?: number | null
}

type SellablePositionItem = {
  ticker: string
  fund_name: string
  quantity: number
  cost_basis?: number | null
  current_price?: number | null
  market_value?: number | null
  currency: string
  value_source?: "live_price" | "cost_basis" | "unavailable"
}

function todayISO(): string {
  const date = new Date()
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const day = String(date.getDate()).padStart(2, "0")
  return `${year}-${month}-${day}`
}

export function AddTransactionSheet({
  open,
  onClose,
  defaultTicker,
  defaultHoldingId,
  defaultAccountId,
  defaultTransactionType,
  defaultCurrency,
  onOpenBuyForAccount,
  onOpenAccounts,
}: Props) {
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
    const match = holdings.find((holding) => holding.ticker?.toUpperCase() === initialTicker && holding.id != null)
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
  const [transactionDate, setTransactionDate] = useState(todayISO())
  const [manualTotal, setManualTotal] = useState(false)
  const [moreOptionsOpen, setMoreOptionsOpen] = useState(false)
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [insufficientBalance, setInsufficientBalance] = useState<{ available: number; required: number } | null>(null)
  const [splitSubmitting, setSplitSubmitting] = useState(false)
  const [nisaPickerOpen, setNisaPickerOpen] = useState(false)
  const [nisaPickerSearch, setNisaPickerSearch] = useState("")
  const [nisaAssetTypeFilter, setNisaAssetTypeFilter] = useState<"all" | "mutual_fund" | "etf" | "stock" | "reit">("all")
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
    (cashBalances ?? []).find((balance) => balance.currency.toUpperCase() === currency.toUpperCase())?.balance ?? null
  const selectedAccount = (accounts ?? []).find((account) => account.id === selectedAccountId)
  const selectedWrapper =
    typeof selectedAccount?.tax_wrapper === "string"
      ? selectedAccount.tax_wrapper.trim().toLowerCase()
      : ""
  const hasNoAccounts = (accounts ?? []).length === 0
  const isCashMovement = transactionType === "DEPOSIT" || transactionType === "WITHDRAWAL"
  const isNewToRadar = useMemo(() => {
    if (isRadarStocksLoading) return false
    if (isCashMovement) return false
    const normalizedTicker = ticker.trim().toUpperCase()
    if (!normalizedTicker) return false
    return !(radarStocks ?? []).some((stock) => stock.ticker.toUpperCase() === normalizedTicker)
  }, [isCashMovement, isRadarStocksLoading, radarStocks, ticker])
  const requiresAccount = true
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
  const nisaEligibleAssetsQuery = useEligibleAssets(shouldShowNisaPicker ? selectedWrapper : undefined, {
    search: debouncedNisaPickerSearch || undefined,
    assetType: nisaAssetTypeFilter === "all" ? undefined : nisaAssetTypeFilter,
    limit: 50,
    enabled: shouldShowNisaPicker,
  })
  const sellablePositionsQuery = useAccountSellablePositions(selectedAccountId, shouldShowSellPicker)
  const filteredSellablePositions = useMemo(() => {
    const keyword = sellPickerSearch.trim().toLowerCase()
    const rows = (sellablePositionsQuery.data ?? []) as SellablePositionItem[]
    if (!keyword) return rows
    return rows.filter((item) => {
      const ticker = item.ticker.toLowerCase()
      const fundName = (item.fund_name || "").toLowerCase()
      return ticker.includes(keyword) || fundName.includes(keyword)
    })
  }, [sellPickerSearch, sellablePositionsQuery.data])
  const selectedSellablePosition = useMemo(() => {
    const normalizedTicker = ticker.trim().toUpperCase()
    if (!normalizedTicker) return null
    return ((sellablePositionsQuery.data ?? []) as SellablePositionItem[]).find(
      (item) => item.ticker.toUpperCase() === normalizedTicker,
    ) ?? null
  }, [ticker, sellablePositionsQuery.data])
  const selectedSellablePositionForDisplay = selectedSellablePosition ?? cachedSelectedSellablePosition
  const getSellValueSourceLabel = (
    valueSource?: SellablePositionItem["value_source"],
  ): string | null => {
    if (!valueSource || valueSource === "live_price") return null
    if (valueSource === "cost_basis") return t("transactions.sell_picker.value_source_cost_basis")
    return t("transactions.sell_picker.value_source_unavailable")
  }
  const selectedNisaAsset = useMemo(() => {
    const normalizedTicker = ticker.trim().toUpperCase()
    if (!normalizedTicker) return null
    return (nisaEligibleAssetsQuery.data?.items ?? []).find(
      (item) => item.ticker.toUpperCase() === normalizedTicker,
    ) ?? null
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
      byWrapper.set(wrapper, {
        id: account.id,
        currency: (account.currency || "USD").toUpperCase(),
      })
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

  const holdingOptions = useMemo(
    () =>
      (holdings ?? [])
        .filter((holding) => holding.id != null)
        .map((holding) => ({ id: holding.id, ticker: holding.ticker })),
    [holdings],
  )
  const inferredHoldingId = useMemo(() => {
    if (defaultHoldingId != null) return String(defaultHoldingId)
    const match = holdingOptions.find((option) => option.ticker.toUpperCase() === initialTicker)
    return match ? String(match.id) : ""
  }, [defaultHoldingId, holdingOptions, initialTicker])

  const resetForm = (options?: { keepDefaultTicker?: boolean; keepDefaultHoldingId?: boolean }) => {
    setTransactionType(initialTransactionType)
    setAccountId(defaultAccountId != null ? String(defaultAccountId) : "")
    setTicker(options?.keepDefaultTicker ? initialTicker : "")
    setHoldingId(
      options?.keepDefaultHoldingId
        ? inferredHoldingId
        : "",
    )
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

    if (requiresAccount && !accountId) {
      nextErrors.account = t("transactions.form.account_required")
    }
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
    if (fxRate && (Number.isNaN(fxRateNum) || fxRateNum <= 0)) {
      nextErrors.fxRate = t("transactions.form.error_fx_rate")
    }
    if (fee && (Number.isNaN(feeNum) || feeNum < 0)) {
      nextErrors.fee = t("transactions.form.error_fee")
    }

    setFieldErrors(nextErrors)
    return Object.keys(nextErrors).length === 0
  }

  const parseInsufficientBalance = (err: unknown): { available: number; required: number } | null => {
    const detail =
      err && typeof err === "object" && "detail" in err
        ? (err as { detail?: unknown }).detail
        : null
    if (!detail || typeof detail !== "object") return null
    const errorCode = "error_code" in detail ? (detail as { error_code?: unknown }).error_code : null
    if (errorCode !== "INSUFFICIENT_BALANCE") return null

    const available =
      "available" in detail && typeof (detail as { available?: unknown }).available === "number"
        ? (detail as { available: number }).available
        : 0
    const required =
      "required" in detail && typeof (detail as { required?: unknown }).required === "number"
        ? (detail as { required: number }).required
        : 0
    return { available, required }
  }

  const parseEligibilityError = (err: unknown): { reasons: string[]; suggestedWrapper?: string } | null => {
    const detail =
      err && typeof err === "object" && "detail" in err
        ? (err as { detail?: unknown }).detail
        : null
    if (!detail || typeof detail !== "object") return null
    const errorCode = "error_code" in detail ? (detail as { error_code?: unknown }).error_code : null
    if (errorCode !== "ASSET_NOT_ELIGIBLE") return null

    const reasons =
      "reasons" in detail && Array.isArray((detail as { reasons?: unknown }).reasons)
        ? ((detail as { reasons: unknown[] }).reasons.filter((r) => typeof r === "string") as string[])
        : []
    const suggestedWrapper =
      "suggested_wrapper" in detail && typeof (detail as { suggested_wrapper?: unknown }).suggested_wrapper === "string"
        ? (detail as { suggested_wrapper: string }).suggested_wrapper
        : undefined
    return { reasons, suggestedWrapper }
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
          ? t(eligibilityError.reasons[0], {
              defaultValue: eligibilityError.reasons[0],
            })
          : t("eligibility.not_eligible")
        toast.error(reasonText)
        return
      }
      toast.error(getErrorMessage(err) || t("common.error"))
    } finally {
      setSplitSubmitting(false)
    }
  }

  return (
    <Sheet open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <SheetContent side="right" className="w-80 sm:w-96 overflow-y-auto">
        <SheetHeader>
          <SheetTitle className="text-sm">{t("transactions.form.title")}</SheetTitle>
        </SheetHeader>

        {hasNoAccounts ? (
          <div className="mt-4 flex flex-col items-center justify-center gap-4 px-4 py-12 text-center">
            <div className="rounded-full bg-muted p-4">
              <Building2 className="h-8 w-8 text-muted-foreground" />
            </div>
            <div className="space-y-1">
              <p className="text-sm font-semibold">{t("transactions.empty_state.title")}</p>
              <p className="text-xs text-muted-foreground">{t("transactions.empty_state.description")}</p>
            </div>
            {onOpenAccounts ? (
              <Button size="sm" onClick={onOpenAccounts}>
                {t("transactions.empty_state.create_account")}
              </Button>
            ) : null}
          </div>
        ) : (
          <div className="mt-4 space-y-4">
          <div className="space-y-1">
            <p className="text-xs font-medium">{t("transactions.form.account")}</p>
            <select
              aria-label={t("transactions.form.account")}
              value={accountId}
              onChange={(event) => {
                setAccountId(event.target.value)
                setCachedSelectedSellablePosition(null)
                const nextAccountId = Number(event.target.value)
                const account = (accounts ?? []).find((item) => item.id === nextAccountId)
                if (account?.currency) {
                  const accountCurrency = account.currency.toUpperCase()
                  setCurrency(accountCurrency)
                  if (isCashMovement) applyCashMovementDefaults(accountCurrency)
                }
                setInsufficientBalance(null)
                setFieldErrors((prev) => ({ ...prev, account: undefined }))
              }}
              className="w-full text-xs border border-border rounded px-2 py-1.5 bg-background"
            >
              <option value="">{t("transactions.form.account_required")}</option>
              {(accounts ?? []).map((account) => (
                <option key={account.id} value={account.id}>
                  {account.name} ({account.broker})
                </option>
              ))}
            </select>
            {selectedAccountId != null ? (
              <p className="text-[11px] text-muted-foreground">
                {t("transactions.form.available_cash", {
                  currency,
                  amount: (selectedCurrencyCashBalance ?? 0).toLocaleString(undefined, {
                    maximumFractionDigits: 2,
                  }),
                })}
              </p>
            ) : null}
            {shouldShowQuotaSummary ? (
              <p className="text-[11px] text-muted-foreground">
                {wrapperQuotaQuery.isLoading
                  ? t("common.loading")
                  : selectedQuota
                    ? t("transactions.form.nisa_quota_summary", {
                        wrapper: t(`wrapper.${selectedWrapper}`),
                        remaining: selectedQuota.wrapper_annual_remaining.toLocaleString(undefined, {
                          maximumFractionDigits: 0,
                        }),
                        annual: (selectedQuota.wrapper_annual_used + selectedQuota.wrapper_annual_remaining).toLocaleString(
                          undefined,
                          { maximumFractionDigits: 0 },
                        ),
                      })
                    : t("transactions.form.nisa_quota_unavailable")}
              </p>
            ) : null}
            {transactionType === "BUY" && hasNoAccounts ? (
              <div className="rounded-md border border-amber-500/40 bg-amber-500/10 px-2 py-2 space-y-1">
                <p className="text-[11px] text-amber-800 dark:text-amber-300">
                  {t("transactions.form.buy_no_account_banner")}
                </p>
                {onOpenAccounts ? (
                  <button
                    type="button"
                    className="text-[11px] text-primary hover:underline"
                    onClick={onOpenAccounts}
                  >
                    {t("transactions.form.create_account")}
                  </button>
                ) : null}
              </div>
            ) : null}
            {transactionType !== "BUY" && hasNoAccounts ? (
              <div className="text-[11px] text-muted-foreground">
                <p>{t("transactions.form.account_empty_hint")}</p>
                {onOpenAccounts ? (
                  <button
                    type="button"
                    className="text-primary hover:underline"
                    onClick={onOpenAccounts}
                  >
                    {t("transactions.form.create_account")}
                  </button>
                ) : null}
              </div>
            ) : null}
            {fieldErrors.account ? <p className="text-xs text-destructive">{fieldErrors.account}</p> : null}
            {transactionType === "BUY" && selectedAccountId != null && (selectedCurrencyCashBalance ?? 0) <= 0 ? (
              <p className="text-[11px] text-muted-foreground">{t("transactions.form.buy_no_balance_hint")}</p>
            ) : null}
            {selectedAccountId != null && (transactionType === "SELL" || transactionType === "DIVIDEND") ? (
              <p className="text-[11px] text-muted-foreground">
                {t("transactions.form.proceeds_hint", {
                  account: selectedAccount?.name ?? t("transactions.form.account_required"),
                })}
              </p>
            ) : null}
            {insufficientBalance ? (
              <div className="rounded-md border border-amber-500/40 bg-amber-500/10 px-2 py-1.5 space-y-1">
                <p className="text-[11px] text-amber-800 dark:text-amber-300">
                  {t("transactions.form.insufficient_balance", {
                    available: insufficientBalance.available.toLocaleString(undefined, { maximumFractionDigits: 2 }),
                    required: insufficientBalance.required.toLocaleString(undefined, { maximumFractionDigits: 2 }),
                    currency,
                  })}
                </p>
                <button
                  type="button"
                  className="text-[11px] text-primary hover:underline"
                  onClick={() => {
                    const shortfall = Math.max(0, insufficientBalance.required - insufficientBalance.available)
                    setTransactionType("DEPOSIT")
                    setQuantity("1")
                    setPrice("")
                    setManualTotal(true)
                    setTotalAmount(shortfall > 0 ? String(shortfall) : "")
                    setInsufficientBalance(null)
                  }}
                >
                  {t("transactions.form.deposit_cash")}
                </button>
              </div>
            ) : null}
          </div>

          <div className="space-y-1">
            <p className="text-xs font-medium">{t("transactions.form.type")}</p>
            <div className="grid grid-cols-2 gap-1">
              {(["BUY", "SELL", "DIVIDEND", "DEPOSIT", "WITHDRAWAL"] as TransactionType[]).map((type) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => {
                    setTransactionType(type)
                    setSellPickerOpen(false)
                    setSellPickerSearch("")
                    setInsufficientBalance(null)
                    setFieldErrors({})
                    if (type === "DEPOSIT" || type === "WITHDRAWAL") {
                      applyCashMovementDefaults(currency)
                    }
                  }}
                  className={`text-xs py-1.5 rounded border transition-colors ${
                    transactionType === type
                      ? "bg-primary text-primary-foreground border-primary"
                      : "border-border hover:bg-muted/30"
                  }`}
                >
                  {t(`transactions.type.${type.toLowerCase()}`)}
                </button>
              ))}
            </div>
          </div>

          {!isCashMovement ? (
            <div className="space-y-1">
              <p className="text-xs font-medium">{t("transactions.form.ticker")}</p>
              {shouldShowNisaPicker && selectedWrapper === "nisa_growth" ? (
                <div className="flex flex-wrap gap-1 pb-1">
                  {(["all", "mutual_fund", "etf", "stock", "reit"] as const).map((type) => (
                    <button
                      key={type}
                      type="button"
                      onClick={() => setNisaAssetTypeFilter(type)}
                      className={cn(
                        "rounded-full border px-2 py-1 text-[11px] leading-none",
                        nisaAssetTypeFilter === type
                          ? "border-primary bg-primary text-primary-foreground"
                          : "border-border text-muted-foreground hover:bg-muted/40",
                      )}
                    >
                      {type === "all" ? t("nisa.eligible.filter_all") : t(`nisa.eligible.asset_type.${type}`)}
                    </button>
                  ))}
                </div>
              ) : null}
              {shouldShowNisaPicker ? (
                <Popover
                  open={nisaPickerOpen}
                  onOpenChange={(nextOpen) => {
                    setNisaPickerOpen(nextOpen)
                    if (nextOpen) {
                      setNisaPickerSearch("")
                    }
                  }}
                >
                  <PopoverTrigger asChild>
                    <Button
                      type="button"
                      variant="outline"
                      role="combobox"
                      aria-expanded={nisaPickerOpen}
                      className="h-auto min-h-9 w-full justify-between py-1.5 text-xs"
                    >
                      <span className="min-w-0 text-left">
                        {selectedNisaAssetForDisplay ? (
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <span className="min-w-0 flex flex-col leading-tight">
                                  <span className="truncate font-medium text-xs">
                                    {selectedNisaAssetForDisplay.fund_name || selectedNisaAssetForDisplay.ticker}
                                  </span>
                                  <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
                                    <span>
                                      {selectedNisaAssetForDisplay.ticker}
                                      {selectedNisaAssetForDisplay.trust_fee_pct != null
                                        ? ` · ${t("eligibility.nisa_trust_fee_label")}: ${selectedNisaAssetForDisplay.trust_fee_pct.toFixed(3)}%`
                                        : ""}
                                    </span>
                                    {selectedWrapper === "nisa_growth" && selectedNisaAssetForDisplay.asset_type ? (
                                      <Badge variant="outline" className="h-4 px-1 text-[10px] font-normal">
                                        {t(`nisa.eligible.asset_type.${selectedNisaAssetForDisplay.asset_type}`)}
                                      </Badge>
                                    ) : null}
                                  </span>
                                </span>
                              </TooltipTrigger>
                              {selectedNisaAssetForDisplay.fund_name ? (
                                <TooltipContent side="bottom" className="max-w-xs text-xs">
                                  {selectedNisaAssetForDisplay.fund_name}
                                </TooltipContent>
                              ) : null}
                            </Tooltip>
                          </TooltipProvider>
                        ) : ticker.trim() ? (
                          <span className="truncate">{ticker.trim().toUpperCase()}</span>
                        ) : (
                          t("eligibility.nisa_picker_placeholder")
                        )}
                      </span>
                      <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent
                    className="w-[360px] max-w-[calc(100vw-2rem)] p-0"
                    align="start"
                    onOpenAutoFocus={(event) => {
                      if (isMobile) event.preventDefault()
                    }}
                  >
                    <Command shouldFilter={false}>
                      <CommandInput
                        value={nisaPickerSearch}
                        onValueChange={setNisaPickerSearch}
                        placeholder={t("eligibility.nisa_picker_search")}
                      />
                      <CommandList {...commandListScrollFix}>
                        {nisaEligibleAssetsQuery.isLoading ? (
                          <div className="flex items-center gap-2 px-3 py-4 text-xs text-muted-foreground">
                            <Loader2 className="h-3.5 w-3.5 animate-spin shrink-0" />
                            {t("eligibility.nisa_picker_loading")}
                          </div>
                        ) : (
                          <>
                            <CommandEmpty>{t("eligibility.nisa_picker_empty")}</CommandEmpty>
                            <CommandGroup>
                              {(nisaEligibleAssetsQuery.data?.items ?? []).map((item) => (
                                <CommandItem
                                  key={`${item.ticker}-${item.fund_name}`}
                                  value={`${item.ticker} ${item.fund_name}`}
                                  onSelect={() => {
                                    setTicker(item.ticker.toUpperCase())
                                    setCachedSelectedNisaAsset(item)
                                    setNisaPickerSearch("")
                                    setFieldErrors((prev) => ({ ...prev, ticker: undefined }))
                                    setInsufficientBalance(null)
                                    setNisaPickerOpen(false)
                                  }}
                                >
                                  <Check
                                    className={cn(
                                      "h-4 w-4",
                                      ticker.trim().toUpperCase() === item.ticker.toUpperCase()
                                        ? "opacity-100"
                                        : "opacity-0",
                                    )}
                                  />
                                  <TooltipProvider>
                                    <Tooltip>
                                      <TooltipTrigger asChild>
                                        <div className="min-w-0 flex-1">
                                          <p className="truncate text-xs font-medium">
                                            {item.fund_name || item.ticker}
                                          </p>
                                          <div className="flex items-center gap-1 text-[11px] text-muted-foreground">
                                            <span>
                                              {item.ticker}
                                              {item.trust_fee_pct != null
                                                ? ` · ${t("eligibility.nisa_trust_fee_label")}: ${item.trust_fee_pct.toFixed(3)}%`
                                                : ""}
                                            </span>
                                            {selectedWrapper === "nisa_growth" && item.asset_type ? (
                                              <Badge variant="outline" className="h-4 px-1 text-[10px] font-normal">
                                                {t(`nisa.eligible.asset_type.${item.asset_type}`)}
                                              </Badge>
                                            ) : null}
                                          </div>
                                        </div>
                                      </TooltipTrigger>
                                      {item.fund_name ? (
                                        <TooltipContent side="right" className="max-w-xs text-xs">
                                          {item.fund_name}
                                        </TooltipContent>
                                      ) : null}
                                    </Tooltip>
                                  </TooltipProvider>
                                </CommandItem>
                              ))}
                            </CommandGroup>
                          </>
                        )}
                      </CommandList>
                      {!nisaEligibleAssetsQuery.isLoading && (nisaEligibleAssetsQuery.data?.items?.length ?? 0) > 0 ? (
                        <p className="border-t px-3 py-2 text-[11px] text-muted-foreground">
                          {t("eligibility.nisa_picker_limit_hint")}
                        </p>
                      ) : null}
                    </Command>
                  </PopoverContent>
                </Popover>
              ) : shouldShowSellPicker ? (
                <Popover
                  open={sellPickerOpen}
                  onOpenChange={(nextOpen) => {
                    setSellPickerOpen(nextOpen)
                    if (nextOpen) {
                      setSellPickerSearch("")
                    }
                  }}
                >
                  <PopoverTrigger asChild>
                    <Button
                      type="button"
                      variant="outline"
                      role="combobox"
                      aria-expanded={sellPickerOpen}
                      className="h-auto min-h-9 w-full justify-between py-1.5 text-xs"
                    >
                      <span className="min-w-0 text-left">
                        {selectedSellablePositionForDisplay ? (
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <span className="min-w-0 flex flex-col leading-tight">
                                  <span className="truncate font-medium text-xs">
                                    {selectedSellablePositionForDisplay.fund_name || selectedSellablePositionForDisplay.ticker}
                                  </span>
                                  <span className="truncate text-[11px] text-muted-foreground">
                                    {selectedSellablePositionForDisplay.ticker} · {selectedSellablePositionForDisplay.quantity.toLocaleString()}
                                  </span>
                                  {getSellValueSourceLabel(selectedSellablePositionForDisplay.value_source) ? (
                                    <span
                                      className={cn(
                                        "truncate text-[10px] mt-0.5",
                                        selectedSellablePositionForDisplay.value_source === "cost_basis"
                                          ? "text-amber-500"
                                          : "text-muted-foreground",
                                      )}
                                    >
                                      {getSellValueSourceLabel(selectedSellablePositionForDisplay.value_source)}
                                    </span>
                                  ) : null}
                                </span>
                              </TooltipTrigger>
                              {selectedSellablePositionForDisplay.fund_name ? (
                                <TooltipContent side="bottom" className="max-w-xs text-xs">
                                  {selectedSellablePositionForDisplay.fund_name}
                                </TooltipContent>
                              ) : null}
                            </Tooltip>
                          </TooltipProvider>
                        ) : ticker.trim() ? (
                          <span className="truncate">{ticker.trim().toUpperCase()}</span>
                        ) : transactionType === "DIVIDEND" ? (
                          t("transactions.sell_picker.placeholder_dividend")
                        ) : (
                          t("transactions.sell_picker.placeholder")
                        )}
                      </span>
                      <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent
                    className="w-[360px] max-w-[calc(100vw-2rem)] p-0"
                    align="start"
                    onOpenAutoFocus={(event) => {
                      if (isMobile) event.preventDefault()
                    }}
                  >
                    <Command shouldFilter={false}>
                      <CommandInput
                        value={sellPickerSearch}
                        onValueChange={setSellPickerSearch}
                        placeholder={t("transactions.sell_picker.search")}
                      />
                      <CommandList {...commandListScrollFix}>
                        {sellablePositionsQuery.isLoading ? (
                          <div className="flex items-center gap-2 px-3 py-4 text-xs text-muted-foreground">
                            <Loader2 className="h-3.5 w-3.5 animate-spin shrink-0" />
                            {t("transactions.sell_picker.loading")}
                          </div>
                        ) : sellablePositionsQuery.isError ? (
                          <div className="px-3 py-4 text-xs text-destructive">
                            {t("transactions.sell_picker.load_error")}
                          </div>
                        ) : (
                          <>
                            <CommandEmpty>{t("transactions.sell_picker.empty")}</CommandEmpty>
                            <CommandGroup>
                              {filteredSellablePositions.map((item) => (
                                <CommandItem
                                  key={item.ticker}
                                  value={`${item.ticker} ${item.fund_name}`}
                                  onSelect={() => {
                                    setTicker(item.ticker.toUpperCase())
                                    setCachedSelectedSellablePosition(item)
                                    setSellPickerSearch("")
                                    setFieldErrors((prev) => ({ ...prev, ticker: undefined }))
                                    setInsufficientBalance(null)
                                    setSellPickerOpen(false)
                                  }}
                                >
                                  <Check
                                    className={cn(
                                      "h-4 w-4",
                                      ticker.trim().toUpperCase() === item.ticker.toUpperCase()
                                        ? "opacity-100"
                                        : "opacity-0",
                                    )}
                                  />
                                  <TooltipProvider>
                                    <Tooltip>
                                      <TooltipTrigger asChild>
                                        <div className="min-w-0 flex-1">
                                          <p className="truncate text-xs font-medium">
                                            {item.fund_name || item.ticker}
                                          </p>
                                          <p className="truncate text-[11px] text-muted-foreground">
                                            {item.ticker} · {item.quantity.toLocaleString()} ·{" "}
                                            {item.market_value != null
                                              ? `${item.currency} ${item.market_value.toLocaleString(undefined, { maximumFractionDigits: 2 })}`
                                              : t("transactions.sell_picker.price_unavailable")}
                                          </p>
                                          {getSellValueSourceLabel(item.value_source) ? (
                                            <p
                                              className={cn(
                                                "text-[10px] mt-0.5",
                                                item.value_source === "cost_basis"
                                                  ? "text-amber-500"
                                                  : "text-muted-foreground",
                                              )}
                                            >
                                              {getSellValueSourceLabel(item.value_source)}
                                            </p>
                                          ) : null}
                                        </div>
                                      </TooltipTrigger>
                                      {item.fund_name ? (
                                        <TooltipContent side="right" className="max-w-xs text-xs">
                                          {item.fund_name}
                                        </TooltipContent>
                                      ) : null}
                                    </Tooltip>
                                  </TooltipProvider>
                                </CommandItem>
                              ))}
                            </CommandGroup>
                          </>
                        )}
                      </CommandList>
                    </Command>
                  </PopoverContent>
                </Popover>
              ) : (
                <Input
                  value={ticker}
                  aria-label={t("transactions.form.ticker")}
                  onChange={(event) => {
                    setTicker(event.target.value.toUpperCase())
                    setFieldErrors((prev) => ({ ...prev, ticker: undefined }))
                    setInsufficientBalance(null)
                  }}
                  placeholder="e.g. AAPL"
                  className="text-xs"
                />
              )}
              {shouldShowNisaPicker ? (
                <p className="text-[11px] text-muted-foreground">
                  {selectedWrapper === "nisa_growth"
                    ? t("eligibility.nisa_picker_hint_growth")
                    : t("eligibility.nisa_picker_hint_tsumitate")}
                </p>
              ) : null}
              {transactionType === "BUY" && ELIGIBILITY_CHECK_WRAPPERS.has(selectedWrapper) ? (
                <div className="pt-1 space-y-1">
                  <EligibilityBadge result={eligibility} loading={eligibilityQuery.isLoading} />
                  {eligibility && !eligibility.eligible ? (
                    <div className="space-y-1">
                      <p className="text-[11px] text-destructive">{t("eligibility.not_eligible")}</p>
                      {eligibility.suggested_wrapper ? (
                        suggestedAccount ? (
                          <button
                            type="button"
                            className="text-[11px] text-primary hover:underline"
                            onClick={() => {
                              if (suggestedAccount.id == null) return
                              setAccountId(String(suggestedAccount.id))
                              const nextCurrency = (suggestedAccount.currency || currency).toUpperCase()
                              setCurrency(nextCurrency)
                              setInsufficientBalance(null)
                            }}
                          >
                            {t("eligibility.switch_to_suggested_account", {
                              wrapper: t(`wrapper.${eligibility.suggested_wrapper}`),
                            })}
                          </button>
                        ) : (
                          <p className="text-[11px] text-muted-foreground">
                            {t("eligibility.no_suggested_account", {
                              wrapper: t(`wrapper.${eligibility.suggested_wrapper}`),
                            })}
                          </p>
                        )
                      ) : null}
                    </div>
                  ) : null}
                </div>
              ) : null}
              {transactionType === "BUY" && routingSuggestionQuery.data?.suggestions?.length ? (
                <div className="pt-1 space-y-1">
                  <p className="text-[11px] font-medium">{t("routing.suggest_title")}</p>
                  <div className="space-y-1">
                    {routingSuggestionQuery.data.suggestions.map((item, idx) => {
                      const suggested = routingSuggestedAccounts.get(item.wrapper)
                      return (
                        <div
                          key={`${item.wrapper}-${idx}`}
                          className="rounded-md border border-border bg-muted/20 px-2 py-1.5"
                        >
                          <div className="flex items-center justify-between gap-2 text-[11px]">
                            <span>{t(`wrapper.${item.wrapper}`, { defaultValue: item.wrapper })}</span>
                            <span>{Math.round(item.amount).toLocaleString()}</span>
                          </div>
                          <p className="text-[11px] text-muted-foreground">
                            {t(item.reason, { defaultValue: item.reason })}
                          </p>
                          {suggested ? (
                            <button
                              type="button"
                              className="text-[11px] text-primary hover:underline"
                              onClick={() => {
                                setAccountId(String(suggested.id))
                                setCurrency(suggested.currency)
                                setInsufficientBalance(null)
                              }}
                            >
                              {t("smart_actions.apply_suggestion")}
                            </button>
                          ) : null}
                        </div>
                      )
                    })}
                  </div>
                  {canSplitPurchase ? (
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      className="h-7 text-[11px]"
                      disabled={splitSubmitting || addTransactionMutation.isPending}
                      onClick={() => {
                        createSplitTransactions().catch(() => {
                          // createSplitTransactions handles all user feedback paths.
                        })
                      }}
                    >
                      {t("smart_actions.split_purchase")}
                    </Button>
                  ) : null}
                </div>
              ) : null}
              {fieldErrors.ticker ? <p className="text-xs text-destructive">{fieldErrors.ticker}</p> : null}
            </div>
          ) : null}

          {!isCashMovement && isNewToRadar ? (
            <div className="space-y-1">
              <p className="text-xs font-medium">{t("transactions.form.thesis")}</p>
              <Input
                value={thesis}
                aria-label={t("transactions.form.thesis")}
                onChange={(event) => setThesis(event.target.value)}
                placeholder={t("transactions.form.thesis_hint")}
                className="text-xs"
              />
              <p className="text-xs font-medium pt-2">{t("transactions.form.category")}</p>
              <Select
                value={forcedCategory ?? category}
                onValueChange={(value) => setCategory(value as StockCategory)}
                disabled={forcedCategory != null}
              >
                <SelectTrigger aria-label={t("transactions.form.category")} className="text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {STOCK_CATEGORIES.map((item) => (
                    <SelectItem key={item} value={item} className="text-xs">
                      {t(`config.category.${item.toLowerCase()}`)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {!forcedCategory ? (
                <p className="text-[11px] text-muted-foreground">
                  {t(`config.category_desc.${category.toLowerCase()}`)}
                </p>
              ) : null}
              {forcedCategory ? (
                <p className="text-[11px] text-muted-foreground">{t("transactions.form.mutual_fund_category_hint")}</p>
              ) : null}
            </div>
          ) : null}

          {!isCashMovement ? (
            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-xs font-medium">{t("transactions.form.quantity")}</p>
                  {shouldShowSellPicker && selectedSellablePositionForDisplay ? (
                    <button
                      type="button"
                      className="text-[11px] text-primary hover:underline"
                      onClick={() => {
                        const maxQuantity = String(selectedSellablePositionForDisplay.quantity)
                        setQuantity(maxQuantity)
                        if (!manualTotal) setTotalAmount(computeTotalAmount(maxQuantity, price))
                        setFieldErrors((prev) => ({ ...prev, quantity: undefined }))
                      }}
                    >
                      {t("transactions.sell_picker.max")}
                    </button>
                  ) : null}
                </div>
                <Input
                  type="number"
                  step="any"
                  aria-label={t("transactions.form.quantity")}
                  value={quantity}
                  onChange={(event) => {
                    const nextQuantity = event.target.value
                    setQuantity(nextQuantity)
                    if (!manualTotal) setTotalAmount(computeTotalAmount(nextQuantity, price))
                    setFieldErrors((prev) => ({ ...prev, quantity: undefined }))
                  }}
                  className="text-xs"
                />
                {shouldShowSellPicker && selectedSellablePositionForDisplay ? (
                  <p className="text-[11px] text-muted-foreground">
                    {t("transactions.sell_picker.available", {
                      quantity: selectedSellablePositionForDisplay.quantity.toLocaleString(undefined, {
                        maximumFractionDigits: 6,
                      }),
                      unit: (forcedCategory ?? category) === "Mutual_Fund"
                        ? t("transactions.sell_picker.unit_units")
                        : t("transactions.sell_picker.unit_shares"),
                    })}
                  </p>
                ) : null}
                {fieldErrors.quantity ? <p className="text-xs text-destructive">{fieldErrors.quantity}</p> : null}
              </div>
              <div className="space-y-1">
                <p className="text-xs font-medium">{t("transactions.form.price")}</p>
                <Input
                  type="number"
                  step="any"
                  aria-label={t("transactions.form.price")}
                  value={price}
                  onChange={(event) => {
                    const nextPrice = event.target.value
                    setPrice(nextPrice)
                    if (!manualTotal) setTotalAmount(computeTotalAmount(quantity, nextPrice))
                    setFieldErrors((prev) => ({ ...prev, price: undefined }))
                  }}
                  className="text-xs"
                />
                <p className="text-[11px] text-muted-foreground">{t("transactions.form.price_hint")}</p>
                {fieldErrors.price ? <p className="text-xs text-destructive">{fieldErrors.price}</p> : null}
              </div>
            </div>
          ) : null}

          <div className="space-y-1">
            <p className="text-xs font-medium">
              {isCashMovement ? t("transactions.form.deposit_amount") : t("transactions.form.total_amount")}
            </p>
            <Input
              type="number"
              step="any"
              aria-label={t("transactions.form.total_amount")}
              value={totalAmount}
              onChange={(event) => {
                setManualTotal(true)
                setTotalAmount(event.target.value)
                setFieldErrors((prev) => ({ ...prev, totalAmount: undefined }))
              }}
              className="text-xs"
            />
            {!isCashMovement ? (
              <div className="flex items-center justify-between gap-2">
                {!manualTotal ? (
                  <p className="text-[11px] text-muted-foreground">{t("transactions.form.total_auto")}</p>
                ) : (
                  <p className="text-[11px] text-muted-foreground">{t("transactions.form.total_manual")}</p>
                )}
                <button
                  type="button"
                  className="text-[11px] text-primary hover:underline"
                  onClick={() => {
                    setManualTotal(false)
                    setTotalAmount(computeTotalAmount(quantity, price))
                  }}
                >
                  {t("transactions.form.use_auto_total")}
                </button>
              </div>
            ) : null}
            {fieldErrors.totalAmount ? <p className="text-xs text-destructive">{fieldErrors.totalAmount}</p> : null}
          </div>

          {isCashMovement ? (
            <div className="space-y-1">
              <p className="text-xs font-medium">{t("transactions.form.currency")}</p>
              <select
                aria-label={t("transactions.form.currency")}
                value={currency}
                onChange={(event) => {
                  const nextCurrency = event.target.value
                  setCurrency(nextCurrency)
                  applyCashMovementDefaults(nextCurrency)
                }}
                className="w-full text-xs border border-border rounded px-2 py-1.5 bg-background"
              >
                {DISPLAY_CURRENCIES.map((displayCurrency) => (
                  <option key={displayCurrency} value={displayCurrency}>
                    {displayCurrency}
                  </option>
                ))}
              </select>
            </div>
          ) : null}

          <div className="space-y-1">
            <p className="text-xs font-medium">{t("transactions.form.date")}</p>
            <Input
              type="date"
              aria-label={t("transactions.form.date")}
              value={transactionDate}
              onChange={(event) => {
                setTransactionDate(event.target.value)
                setFieldErrors((prev) => ({ ...prev, transactionDate: undefined }))
              }}
              className="text-xs"
            />
            {fieldErrors.transactionDate ? (
              <p className="text-xs text-destructive">{fieldErrors.transactionDate}</p>
            ) : null}
          </div>

          <div className="space-y-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="w-full text-xs"
              onClick={() => setMoreOptionsOpen((prev) => !prev)}
            >
              {moreOptionsOpen ? t("transactions.form.hide_more") : t("transactions.form.show_more")}
            </Button>

            {moreOptionsOpen ? (
              <div className="space-y-3 rounded-md border border-border p-3">
                <div className="space-y-1">
                  <p className="text-xs font-medium">{t("transactions.form.holding_link")}</p>
                  <select
                    aria-label={t("transactions.form.holding_link")}
                    value={holdingId}
                    onChange={(event) => setHoldingId(event.target.value)}
                    className="w-full text-xs border border-border rounded px-2 py-1.5 bg-background"
                  >
                    <option value="">{t("transactions.form.holding_optional")}</option>
                    {holdingOptions.map((option) => (
                      <option key={option.id} value={option.id}>
                        {option.ticker}
                      </option>
                    ))}
                  </select>
                </div>

                {!isCashMovement ? (
                  <div className="space-y-1">
                    <p className="text-xs font-medium">{t("transactions.form.currency")}</p>
                    <select
                      aria-label={t("transactions.form.currency")}
                      value={currency}
                      onChange={(event) => {
                        setCurrency(event.target.value)
                      }}
                      className="w-full text-xs border border-border rounded px-2 py-1.5 bg-background"
                    >
                      {DISPLAY_CURRENCIES.map((displayCurrency) => (
                        <option key={displayCurrency} value={displayCurrency}>
                          {displayCurrency}
                        </option>
                      ))}
                    </select>
                  </div>
                ) : null}

                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1">
                    <p className="text-xs font-medium">{t("transactions.form.fx_rate")}</p>
                    <Input
                      type="number"
                      step="any"
                      aria-label={t("transactions.form.fx_rate")}
                      value={fxRate}
                      onChange={(event) => {
                        setFxRate(event.target.value)
                        setFieldErrors((prev) => ({ ...prev, fxRate: undefined }))
                      }}
                      className="text-xs"
                    />
                    {fieldErrors.fxRate ? <p className="text-xs text-destructive">{fieldErrors.fxRate}</p> : null}
                  </div>
                  <div className="space-y-1">
                    <p className="text-xs font-medium">{t("transactions.form.fee")}</p>
                    <Input
                      type="number"
                      step="any"
                      aria-label={t("transactions.form.fee")}
                      value={fee}
                      onChange={(event) => {
                        setFee(event.target.value)
                        setFieldErrors((prev) => ({ ...prev, fee: undefined }))
                      }}
                      className="text-xs"
                    />
                    {fieldErrors.fee ? <p className="text-xs text-destructive">{fieldErrors.fee}</p> : null}
                  </div>
                </div>

                <div className="space-y-1">
                  <p className="text-xs font-medium">{t("transactions.form.note")}</p>
                  <textarea
                    value={note}
                    onChange={(event) => setNote(event.target.value)}
                    maxLength={500}
                    className="w-full min-h-[88px] rounded-md border border-border bg-background px-2 py-1.5 text-xs"
                    placeholder={t("transactions.form.note_placeholder")}
                  />
                </div>
              </div>
            ) : null}
          </div>

          <Button
            className="w-full"
            size="sm"
            disabled={splitSubmitting || addTransactionMutation.isPending || (requiresAccount && selectedAccountId == null)}
            onClick={() => {
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
                setInsufficientBalance({
                  available: availableAmount,
                  required: requiredAmount,
                })
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
                        ? t(eligibilityError.reasons[0], {
                            defaultValue: eligibilityError.reasons[0],
                          })
                        : t("eligibility.not_eligible")
                      toast.error(reasonText)
                      return
                    }
                    toast.error(getErrorMessage(err) || t("common.error"))
                  },
                },
              )
            }}
          >
            {t("transactions.form.submit")}
          </Button>
          </div>
        )}
      </SheetContent>
    </Sheet>
  )
}
