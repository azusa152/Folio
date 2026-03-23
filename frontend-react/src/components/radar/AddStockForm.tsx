import { useTranslation } from "react-i18next"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { STOCK_CATEGORIES, MARKET_OPTIONS } from "@/lib/constants"
import type { StockCategory } from "@/api/types/radar"

interface Props {
  market: string
  ticker: string
  category: StockCategory
  thesis: string
  selectedTags: string[]
  tagOptions: string[]
  marketInfo: (typeof MARKET_OPTIONS)[number]
  isPending: boolean
  onMarketChange: (market: string) => void
  onTickerChange: (ticker: string) => void
  onCategoryChange: (category: StockCategory) => void
  onThesisChange: (thesis: string) => void
  onToggleTag: (tag: string) => void
  onSubmit: () => void
}

export function AddStockForm({
  market,
  ticker,
  category,
  thesis,
  selectedTags,
  tagOptions,
  marketInfo,
  isPending,
  onMarketChange,
  onTickerChange,
  onCategoryChange,
  onThesisChange,
  onToggleTag,
  onSubmit,
}: Props) {
  const { t } = useTranslation()

  return (
    <div className="space-y-2">
      <div>
        <label className="text-xs text-muted-foreground">{t("radar.form.market")}</label>
        <Select value={market} onValueChange={onMarketChange}>
          <SelectTrigger aria-label={t("radar.form.market")} className="text-xs h-8 mt-0.5">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {MARKET_OPTIONS.map((m) => (
              <SelectItem key={m.key} value={m.key} className="text-xs">
                {t(m.labelKey)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <p className="text-xs text-muted-foreground mt-0.5">
          {t("radar.form.currency", { currency: marketInfo.currency })}
        </p>
      </div>

      <div>
        <label htmlFor="add-stock-ticker" className="text-xs text-muted-foreground">
          {t("radar.form.ticker")}
        </label>
        <input
          id="add-stock-ticker"
          className="mt-0.5 w-full rounded-md border border-input bg-background px-2 py-1 text-sm"
          placeholder={market === "TW" ? "2330" : market === "JP" ? "7203" : "AAPL"}
          value={ticker}
          onChange={(e) => onTickerChange(e.target.value)}
        />
      </div>

      <div>
        <label className="text-xs text-muted-foreground">{t("radar.form.category")}</label>
        <Select value={category} onValueChange={(v) => onCategoryChange(v as StockCategory)}>
          <SelectTrigger aria-label={t("radar.form.category")} className="text-xs h-8 mt-0.5">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {STOCK_CATEGORIES.map((c) => (
              <SelectItem key={c} value={c} className="text-xs">
                {t(`config.category.${c.toLowerCase()}`)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <p className="text-[11px] text-muted-foreground mt-1">
          {t(`config.category_desc.${category.toLowerCase()}`)}
        </p>
      </div>

      <div>
        <label htmlFor="add-stock-thesis" className="text-xs text-muted-foreground">
          {t("radar.form.thesis")}
        </label>
        <textarea
          id="add-stock-thesis"
          className="mt-0.5 w-full rounded-md border border-input bg-background p-2 text-sm resize-none"
          rows={3}
          placeholder={t("radar.form.thesis_placeholder")}
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
