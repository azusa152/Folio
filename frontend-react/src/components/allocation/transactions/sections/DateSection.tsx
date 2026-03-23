import { useTranslation } from "react-i18next"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { DISPLAY_CURRENCIES } from "@/lib/constants"
import type { FieldErrors } from "@/hooks/useAddTransactionForm"

interface HoldingOption {
  id?: number
  ticker: string
}

interface DateSectionProps {
  isCashMovement: boolean
  transactionDate: string
  moreOptionsOpen: boolean
  holdingId: string
  currency: string
  fxRate: string
  fee: string
  note: string
  holdingOptions: HoldingOption[]
  fieldErrors: FieldErrors
  setTransactionDate: (d: string) => void
  setMoreOptionsOpen: (updater: (prev: boolean) => boolean) => void
  setHoldingId: (id: string) => void
  setCurrency: (c: string) => void
  setFxRate: (r: string) => void
  setFee: (f: string) => void
  setNote: (n: string) => void
  setFieldErrors: (updater: (prev: FieldErrors) => FieldErrors) => void
}

export function DateSection({
  isCashMovement,
  transactionDate,
  moreOptionsOpen,
  holdingId,
  currency,
  fxRate,
  fee,
  note,
  holdingOptions,
  fieldErrors,
  setTransactionDate,
  setMoreOptionsOpen,
  setHoldingId,
  setCurrency,
  setFxRate,
  setFee,
  setNote,
  setFieldErrors,
}: DateSectionProps) {
  const { t } = useTranslation()

  return (
    <>
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
                {fieldErrors.fxRate ? (
                  <p className="text-xs text-destructive">{fieldErrors.fxRate}</p>
                ) : null}
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
                {fieldErrors.fee ? (
                  <p className="text-xs text-destructive">{fieldErrors.fee}</p>
                ) : null}
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
    </>
  )
}
