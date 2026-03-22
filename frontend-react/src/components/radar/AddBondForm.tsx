import { useTranslation } from "react-i18next"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { CASH_CURRENCY_OPTIONS, MARKET_TAG_OPTIONS } from "@/lib/constants"

interface Props {
  ticker: string
  bondCurrency: string
  thesis: string
  selectedTags: string[]
  market: string
  isPending: boolean
  onTickerChange: (ticker: string) => void
  onCurrencyChange: (currency: string) => void
  onThesisChange: (thesis: string) => void
  onToggleTag: (tag: string) => void
  onSubmit: () => void
}

export function AddBondForm({
  ticker,
  bondCurrency,
  thesis,
  selectedTags,
  market,
  isPending,
  onTickerChange,
  onCurrencyChange,
  onThesisChange,
  onToggleTag,
  onSubmit,
}: Props) {
  const { t } = useTranslation()
  const tagOptions = MARKET_TAG_OPTIONS[market] ?? MARKET_TAG_OPTIONS.US

  return (
    <div className="space-y-2">
      <div>
        <label htmlFor="add-bond-ticker" className="text-xs text-muted-foreground">
          {t("radar.form.bond_ticker")}
        </label>
        <input
          id="add-bond-ticker"
          className="mt-0.5 w-full rounded-md border border-input bg-background px-2 py-1 text-sm"
          placeholder="TLT, BND, SGOV"
          value={ticker}
          onChange={(e) => onTickerChange(e.target.value)}
        />
      </div>

      <div>
        <label className="text-xs text-muted-foreground">
          {t("radar.form.currency", { currency: "" }).replace(": ", "")}
        </label>
        <Select value={bondCurrency} onValueChange={onCurrencyChange}>
          <SelectTrigger
            aria-label={t("radar.form.currency", { currency: "" }).replace(": ", "")}
            className="text-xs h-8 mt-0.5"
          >
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {CASH_CURRENCY_OPTIONS.map((c) => (
              <SelectItem key={c} value={c} className="text-xs">
                {c}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div>
        <label htmlFor="add-bond-thesis" className="text-xs text-muted-foreground">
          {t("radar.form.thesis")}
        </label>
        <textarea
          id="add-bond-thesis"
          className="mt-0.5 w-full rounded-md border border-input bg-background p-2 text-sm resize-none"
          rows={3}
          placeholder={t("radar.form.bond_thesis_placeholder")}
          value={thesis}
          onChange={(e) => onThesisChange(e.target.value)}
        />
      </div>

      <div>
        <label className="text-xs text-muted-foreground">{t("radar.form.tags")}</label>
        <div className="mt-1 flex flex-wrap gap-1">
          {tagOptions.map((tag) => (
            <button
              key={tag}
              onClick={() => onToggleTag(tag)}
              className={`rounded-full border px-2 py-0.5 text-xs transition-colors ${
                selectedTags.includes(tag)
                  ? "bg-primary text-primary-foreground border-primary"
                  : "border-border text-muted-foreground hover:text-foreground"
              }`}
            >
              {tag}
            </button>
          ))}
        </div>
      </div>

      <Button size="sm" className="w-full" onClick={onSubmit} disabled={isPending}>
        {t("radar.form.add_button")}
      </Button>
    </div>
  )
}
