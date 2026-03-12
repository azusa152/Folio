import { useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { useAccountCashBalances, useAccounts } from "@/api/hooks/useAccounts"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { useAddTransaction } from "@/api/hooks/useTransactions"
import { useHoldings } from "@/api/hooks/useDashboard"
import { useRadarStocks } from "@/api/hooks/useRadar"
import { CATEGORY_ICON_SHORT, DISPLAY_CURRENCIES, STOCK_CATEGORIES } from "@/lib/constants"
import { getErrorMessage } from "@/lib/utils"

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

  const selectedAccountId = accountId ? Number(accountId) : null
  const { data: cashBalances } = useAccountCashBalances(selectedAccountId, open)
  const selectedCurrencyCashBalance =
    (cashBalances ?? []).find((balance) => balance.currency.toUpperCase() === currency.toUpperCase())?.balance ?? null
  const selectedAccount = (accounts ?? []).find((account) => account.id === selectedAccountId)
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

  return (
    <Sheet open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <SheetContent side="right" className="w-80 sm:w-96 overflow-y-auto">
        <SheetHeader>
          <SheetTitle className="text-sm">{t("transactions.form.title")}</SheetTitle>
        </SheetHeader>

        <div className="mt-4 space-y-4">
          <div className="space-y-1">
            <p className="text-xs font-medium">{t("transactions.form.account")}</p>
            <select
              aria-label={t("transactions.form.account")}
              value={accountId}
              onChange={(event) => {
                setAccountId(event.target.value)
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
              <Input
                value={ticker}
                aria-label={t("transactions.form.ticker")}
                onChange={(event) => {
                  setTicker(event.target.value.toUpperCase())
                  setFieldErrors((prev) => ({ ...prev, ticker: undefined }))
                }}
                placeholder="e.g. AAPL"
                className="text-xs"
              />
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
              <Select value={category} onValueChange={(value) => setCategory(value as StockCategory)}>
                <SelectTrigger aria-label={t("transactions.form.category")} className="text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {STOCK_CATEGORIES.map((item) => (
                    <SelectItem key={item} value={item} className="text-xs">
                      {CATEGORY_ICON_SHORT[item] ?? ""} {t(`config.category.${item.toLowerCase()}`)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          ) : null}

          {!isCashMovement ? (
            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1">
                <p className="text-xs font-medium">{t("transactions.form.quantity")}</p>
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
            disabled={addTransactionMutation.isPending || (requiresAccount && selectedAccountId == null)}
            onClick={() => {
              if (!validate()) return

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
                    if (insufficient) setInsufficientBalance(insufficient)
                    toast.error(getErrorMessage(err) || t("common.error"))
                  },
                },
              )
            }}
          >
            {t("transactions.form.submit")}
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  )
}
