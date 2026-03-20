import { useTranslation } from "react-i18next"
import { Input } from "@/components/ui/input"
import { DISPLAY_CURRENCIES } from "@/lib/constants"
import type { SellablePositionItem, StockCategory, FieldErrors } from "@/hooks/useAddTransactionForm"

interface PriceSectionProps {
  isCashMovement: boolean
  quantity: string
  price: string
  totalAmount: string
  currency: string
  manualTotal: boolean
  shouldShowSellPicker: boolean
  selectedSellablePositionForDisplay: SellablePositionItem | null
  forcedCategory: StockCategory | null
  category: StockCategory
  fieldErrors: FieldErrors
  setQuantity: (q: string) => void
  setPrice: (p: string) => void
  setTotalAmount: (a: string) => void
  setCurrency: (c: string) => void
  setManualTotal: (m: boolean) => void
  setFieldErrors: (updater: (prev: FieldErrors) => FieldErrors) => void
  applyCashMovementDefaults: (currency: string) => void
  computeTotalAmount: (quantity: string, price: string) => string
}

export function PriceSection({
  isCashMovement,
  quantity,
  price,
  totalAmount,
  currency,
  manualTotal,
  shouldShowSellPicker,
  selectedSellablePositionForDisplay,
  forcedCategory,
  category,
  fieldErrors,
  setQuantity,
  setPrice,
  setTotalAmount,
  setCurrency,
  setManualTotal,
  setFieldErrors,
  applyCashMovementDefaults,
  computeTotalAmount,
}: PriceSectionProps) {
  const { t } = useTranslation()

  return (
    <>
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
                  unit:
                    (forcedCategory ?? category) === "Mutual_Fund"
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
    </>
  )
}
