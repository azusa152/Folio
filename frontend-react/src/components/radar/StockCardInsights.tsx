import { type ReactNode, memo, useState } from "react"
import { ChevronDown } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { GlossaryTerm } from "@/components/GlossaryTerm"
import { PriceChart } from "@/components/radar/PriceChart"
import { GrossMarginChart } from "@/components/radar/GrossMarginChart"
import { FundamentalsTab } from "@/components/radar/FundamentalsTab"
import { cn } from "@/lib/utils"
import { CATEGORY_ICON_SHORT } from "@/lib/constants"
import { formatPrice, formatMarketCap } from "@/lib/format"
import { FINANCE_CHIP } from "@/lib/colors"
import { useThesisHistory } from "@/api/hooks/useRadar"
import type { PricePoint, MoatAnalysis } from "@/api/hooks/useRadar"
import type { RadarStock, RadarEnrichedStock, ResonanceMap } from "@/api/types/radar"

const SKIP_DIVIDEND_CATEGORIES = new Set(["Trend_Setter", "Growth", "Cash"])

const GLOSSARY_KEYS = {
  rsi: "rsi",
  bias: "bias",
  volumeRatio: "volume_ratio",
  ma200: "ma200",
  ma60: "ma60",
} as const

function MetricChip({
  label,
  value,
  color,
}: {
  label: ReactNode
  value: string | number | null | undefined
  color?: string
}) {
  if (value == null) return null
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${color ?? "border-border text-foreground"}`}>
      {label}: {value}
    </span>
  )
}

function ThesisHistorySection({ ticker }: { ticker: string }) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const { data: history, isLoading } = useThesisHistory(ticker, open)

  return (
    <div>
      <button
        onClick={() => setOpen((v) => !v)}
        className="text-xs text-muted-foreground underline underline-offset-2 hover:text-foreground transition-colors"
      >
        <span className="inline-flex items-center gap-1">
          <ChevronDown className={cn("h-3.5 w-3.5 transition-transform duration-200", open && "rotate-180")} />
          {t("radar.stock_card.history")}
        </span>
      </button>
      {open && (
        <div className="mt-2 space-y-2">
          {isLoading ? (
            <p className="text-xs text-muted-foreground">{t("common.loading")}</p>
          ) : !history?.length ? (
            <p className="text-xs text-muted-foreground">{t("radar.stock_card.no_history")}</p>
          ) : (
            history.map((entry) => (
              <div key={entry.version} className="rounded border border-border p-2 text-xs">
                <p className="font-semibold text-muted-foreground">
                  v{entry.version} — {entry.created_at.slice(0, 10)}
                </p>
                <p className="mt-0.5">{entry.content}</p>
                {entry.tags.length > 0 && (
                  <p className="mt-0.5 text-muted-foreground">{entry.tags.map((tag) => `#${tag}`).join(" ")}</p>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}

function SectionHeading({ children }: { children: ReactNode }) {
  return (
    <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
      {children}
    </p>
  )
}

interface Props {
  stock: RadarStock
  enrichment?: RadarEnrichedStock
  resonance?: ResonanceMap[string]
  isHeld: boolean
  isCrypto: boolean
  currency: { symbol: string; code: string }
  marketLabel: string
  marketCap?: number | null
  priceHistory?: PricePoint[]
  priceLoading: boolean
  moatData?: MoatAnalysis
  moatLoading: boolean
  showMoatChart: boolean
}

export const StockCardInsights = memo(function StockCardInsights({
  stock,
  enrichment,
  resonance,
  isHeld,
  isCrypto,
  currency,
  marketLabel,
  marketCap,
  priceHistory,
  priceLoading,
  moatData,
  moatLoading,
  showMoatChart,
}: Props) {
  const { t } = useTranslation()

  const sig = enrichment?.signals
  const rsi = sig?.rsi ?? enrichment?.rsi
  const bias = sig?.bias ?? enrichment?.bias
  const volumeRatio = sig?.volume_ratio ?? enrichment?.volume_ratio
  const changePct = sig?.change_pct ?? enrichment?.change_pct

  return (
    <div className="space-y-4">
      {/* Section 1: Signals & Trend */}
      <div className="space-y-2">
        <SectionHeading>{t("radar.stock_card.section_signals")}</SectionHeading>

        {!isCrypto && (
          <div className="flex flex-wrap gap-1.5 text-xs">
            <MetricChip
              label={<GlossaryTerm termKey={GLOSSARY_KEYS.rsi}>{t("utils.signals.rsi")}</GlossaryTerm>}
              value={rsi != null ? rsi.toFixed(1) : null}
              color={
                rsi != null && rsi < 35
                  ? FINANCE_CHIP.gain
                  : rsi != null && rsi > 70
                    ? FINANCE_CHIP.loss
                    : undefined
              }
            />
            <MetricChip
              label={<GlossaryTerm termKey={GLOSSARY_KEYS.bias}>{t("utils.signals.bias")}</GlossaryTerm>}
              value={bias != null ? `${bias.toFixed(1)}%` : null}
              color={
                bias != null && bias > 20
                  ? FINANCE_CHIP.loss
                  : bias != null && bias < -5
                    ? FINANCE_CHIP.gain
                    : undefined
              }
            />
            {volumeRatio != null && (
              <MetricChip
                label={
                  <GlossaryTerm termKey={GLOSSARY_KEYS.volumeRatio}>
                    {t("utils.signals.volume_ratio")}
                  </GlossaryTerm>
                }
                value={`${volumeRatio.toFixed(1)}x`}
              />
            )}
          </div>
        )}

        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
          {sig?.price != null && (
            <span>{t("utils.signals.price")}: {currency.symbol}{formatPrice(sig.price as number, currency.code)}</span>
          )}
          {!isCrypto && sig?.ma200 != null && (
            <span>
              <GlossaryTerm termKey={GLOSSARY_KEYS.ma200}>{t("utils.signals.ma200")}</GlossaryTerm>:{" "}
              {currency.symbol}{formatPrice(sig.ma200 as number, currency.code)}
            </span>
          )}
          {!isCrypto && sig?.ma60 != null && (
            <span>
              <GlossaryTerm termKey={GLOSSARY_KEYS.ma60}>{t("utils.signals.ma60")}</GlossaryTerm>:{" "}
              {currency.symbol}{formatPrice(sig.ma60 as number, currency.code)}
            </span>
          )}
          {isCrypto && changePct != null && (
            <span>{t("allocation.crypto.change_24h_short")}: {changePct >= 0 ? "+" : "-"}{Math.abs(changePct).toFixed(2)}%</span>
          )}
        </div>

        <div>
          <p className="text-xs font-medium text-muted-foreground mb-1">
            {t("radar.stock_card.price_chart_title")}
          </p>
          {priceLoading ? (
            <Skeleton className="h-[200px] w-full" />
          ) : priceHistory && priceHistory.length >= 5 ? (
            <PriceChart data={priceHistory} />
          ) : (
            <p className="text-xs text-muted-foreground">{t("chart.insufficient_data")}</p>
          )}
        </div>

        {moatLoading ? (
          <Skeleton className="h-[160px] w-full" />
        ) : showMoatChart && moatData ? (
          <GrossMarginChart data={moatData} />
        ) : null}
      </div>

      {/* Section 2: Fundamentals */}
      <div className="space-y-2">
        <SectionHeading>{t("radar.stock_card.section_fundamentals")}</SectionHeading>
        <FundamentalsTab ticker={stock.ticker} fundamentals={enrichment?.fundamentals} />
      </div>

      {/* Section 3: Thesis */}
      <div className="space-y-2">
        <SectionHeading>{t("radar.stock_card.section_thesis")}</SectionHeading>
        <div className="rounded-md bg-muted/30 p-2 text-sm">
          {stock.current_thesis || (
            <span className="text-muted-foreground italic">{t("radar.stock_card.no_thesis")}</span>
          )}
        </div>
        {stock.current_tags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {stock.current_tags.map((tag) => (
              <Badge key={tag} variant="secondary" className="text-xs">
                {tag}
              </Badge>
            ))}
          </div>
        )}
        <ThesisHistorySection ticker={stock.ticker} />
      </div>

      {/* Section 4: Portfolio Context */}
      <div className="space-y-2">
        <SectionHeading>{t("radar.stock_card.section_portfolio")}</SectionHeading>
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
          <span>
            {CATEGORY_ICON_SHORT[stock.category] ?? ""} {stock.category.replace("_", " ")} · {marketLabel}
          </span>
          {marketCap != null && (
            <span>{t("radar.stock_card.fundamentals.market_cap_short")}: {formatMarketCap(marketCap)}</span>
          )}
          {isHeld && (
            <span className="text-primary font-medium">{t("radar.stock_card.held")}</span>
          )}
        </div>
        {resonance && resonance.length > 0 && (
          <p className="text-xs text-muted-foreground">
            🏆 {resonance.map((r) => r.guru_display_name).join(", ")} ({resonance.length})
          </p>
        )}
        {enrichment?.earnings?.next_earnings_date && (
          <p className="text-xs text-muted-foreground">
            📅 {t("radar.stock_card.earnings")}: {enrichment.earnings.next_earnings_date}
            {enrichment.earnings.days_until != null && enrichment.earnings.days_until <= 14 && (
              <span className="ml-1 text-amber-500">({enrichment.earnings.days_until}d)</span>
            )}
          </p>
        )}
        {!SKIP_DIVIDEND_CATEGORIES.has(stock.category) && enrichment?.dividend?.dividend_yield != null && (
          <p className="text-xs text-muted-foreground">
            💰 {t("radar.stock_card.dividend")}: {enrichment.dividend.dividend_yield.toFixed(2)}%
          </p>
        )}
      </div>
    </div>
  )
})
