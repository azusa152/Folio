import { useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { useAddTransaction } from "@/api/hooks/useTransactions"
import { useHoldings } from "@/api/hooks/useDashboard"
import { DISPLAY_CURRENCIES } from "@/lib/constants"
import { getErrorMessage } from "@/lib/utils"

interface Props {
  open: boolean
  onClose: () => void
  defaultTicker?: string
  defaultHoldingId?: number
}

type TransactionType = "BUY" | "SELL" | "DIVIDEND" | "DEPOSIT" | "WITHDRAWAL"

interface FieldErrors {
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

export function AddTransactionSheet({ open, onClose, defaultTicker, defaultHoldingId }: Props) {
  const { t } = useTranslation()
  const addTransactionMutation = useAddTransaction()
  const { data: holdings } = useHoldings()

  const initialTicker = defaultTicker?.toUpperCase() ?? ""

  const [transactionType, setTransactionType] = useState<TransactionType>("BUY")
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
  const [currency, setCurrency] = useState("USD")
  const [fxRate, setFxRate] = useState("")
  const [fee, setFee] = useState("0")
  const [note, setNote] = useState("")
  const [transactionDate, setTransactionDate] = useState(todayISO())
  const [manualTotal, setManualTotal] = useState(false)
  const [moreOptionsOpen, setMoreOptionsOpen] = useState(false)
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})

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
    setTransactionType("BUY")
    setTicker(options?.keepDefaultTicker ? initialTicker : "")
    setHoldingId(
      options?.keepDefaultHoldingId
        ? inferredHoldingId
        : "",
    )
    setQuantity("")
    setPrice("")
    setTotalAmount("")
    setCurrency("USD")
    setFxRate("")
    setFee("0")
    setNote("")
    setTransactionDate(todayISO())
    setManualTotal(false)
    setMoreOptionsOpen(false)
    setFieldErrors({})
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

    if (!ticker.trim()) nextErrors.ticker = t("transactions.form.error_ticker")
    if (!quantity || Number.isNaN(quantityNum) || quantityNum <= 0) {
      nextErrors.quantity = t("transactions.form.error_quantity")
    }
    if (price && (Number.isNaN(priceNum) || priceNum < 0)) {
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

  return (
    <Sheet open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <SheetContent side="right" className="w-80 sm:w-96 overflow-y-auto">
        <SheetHeader>
          <SheetTitle className="text-sm">{t("transactions.form.title")}</SheetTitle>
        </SheetHeader>

        <div className="mt-4 space-y-4">
          <div className="space-y-1">
            <p className="text-xs font-medium">{t("transactions.form.type")}</p>
            <div className="grid grid-cols-2 gap-1">
              {(["BUY", "SELL", "DIVIDEND", "DEPOSIT", "WITHDRAWAL"] as TransactionType[]).map((type) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => setTransactionType(type)}
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

          <div className="space-y-1">
            <p className="text-xs font-medium">{t("transactions.form.total_amount")}</p>
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
            {fieldErrors.totalAmount ? <p className="text-xs text-destructive">{fieldErrors.totalAmount}</p> : null}
          </div>

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

                <div className="space-y-1">
                  <p className="text-xs font-medium">{t("transactions.form.currency")}</p>
                  <select
                    aria-label={t("transactions.form.currency")}
                    value={currency}
                    onChange={(event) => setCurrency(event.target.value)}
                    className="w-full text-xs border border-border rounded px-2 py-1.5 bg-background"
                  >
                    {DISPLAY_CURRENCIES.map((displayCurrency) => (
                      <option key={displayCurrency} value={displayCurrency}>
                        {displayCurrency}
                      </option>
                    ))}
                  </select>
                </div>

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
            disabled={addTransactionMutation.isPending}
            onClick={() => {
              if (!validate()) return

              addTransactionMutation.mutate(
                {
                  holding_id: holdingId ? Number(holdingId) : undefined,
                  ticker: ticker.trim(),
                  transaction_type: transactionType,
                  quantity: Number(quantity),
                  price: price ? Number(price) : undefined,
                  total_amount: Number(totalAmount),
                  currency,
                  fx_rate: fxRate ? Number(fxRate) : undefined,
                  fee: fee ? Number(fee) : 0,
                  note: note.trim(),
                  transaction_date: transactionDate,
                },
                {
                  onSuccess: () => {
                    toast.success(t("transactions.toast.created"))
                    resetForm({ keepDefaultTicker: true, keepDefaultHoldingId: true })
                    onClose()
                  },
                  onError: (err: unknown) => {
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
