import { ChevronDown, Minus, TrendingDown, TrendingUp } from "lucide-react"
import { useTranslation } from "react-i18next"
import { cn, formatLocalTime } from "@/lib/utils"
import { FINANCE_TEXT } from "@/lib/colors"
import { Badge } from "@/components/ui/badge"
import { FxSparkline } from "../FxSparkline"
import type { FxWatch, FxAnalysis, FxHistoryPoint } from "@/api/types/fxWatch"

interface Props {
  watch: FxWatch
  analysis: FxAnalysis | undefined
  sparklineData: FxHistoryPoint[] | undefined
  pair: string
  rateStr: string
  dailyChangePct: number | null
  dailyChangeStr: string | null
  badgeVariant: "default" | "secondary" | "outline"
  badgeLabel: string
  trendDirection: FxAnalysis["trend_direction"]
  isPrivate: boolean
  expanded: boolean
  setExpanded: (updater: (v: boolean) => boolean) => void
}

function trendIcon(direction: FxAnalysis["trend_direction"]) {
  if (direction === "rising") return <TrendingUp className="h-3.5 w-3.5" />
  if (direction === "falling") return <TrendingDown className="h-3.5 w-3.5" />
  return <Minus className="h-3.5 w-3.5" />
}

export function WatchCardHeader({
  watch,
  analysis,
  sparklineData,
  pair,
  rateStr,
  dailyChangePct,
  dailyChangeStr,
  badgeVariant,
  badgeLabel,
  trendDirection,
  isPrivate,
  expanded,
  setExpanded,
}: Props) {
  const { t } = useTranslation()

  return (
    <button
      onClick={() => setExpanded((v) => !v)}
      aria-expanded={expanded}
      className="w-full text-left px-4 py-3 hover:bg-muted/30 transition-colors rounded-[inherit]"
    >
      <div className="flex items-center gap-3">
        {!isPrivate && <FxSparkline data={sparklineData} />}

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold">{pair}</span>
            {!isPrivate && (
              <span className="text-sm tabular-nums text-foreground">{rateStr}</span>
            )}
            {!isPrivate && dailyChangeStr && (
              <span
                className={`text-xs font-medium tabular-nums ${
                  (dailyChangePct ?? 0) >= 0 ? FINANCE_TEXT.gain : FINANCE_TEXT.loss
                }`}
              >
                {dailyChangeStr}
              </span>
            )}
            <Badge variant={badgeVariant} className="text-xs h-5">
              {badgeLabel}
            </Badge>
          </div>

          {analysis && !isPrivate && (
            <div className="flex items-center gap-2 mt-1 flex-wrap">
              {analysis.is_recent_high && (
                <span
                  className={cn(
                    "inline-flex items-center gap-1 text-xs rounded-full px-2 py-0.5",
                    analysis.scenario === "declining_from_high"
                      ? "bg-muted text-muted-foreground"
                      : "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400",
                  )}
                >
                  {trendIcon(trendDirection)}
                  {analysis.scenario === "declining_from_high"
                    ? t("fx_watch.indicator.high_days_ago", {
                        days: analysis.lookback_days,
                        ago: analysis.high_days_ago,
                      })
                    : t("fx_watch.indicator.near_high", { days: analysis.lookback_days })}
                </span>
              )}
              {analysis.is_recent_high && (
                <span className="text-xs text-muted-foreground">
                  {t("fx_watch.indicator.below_high", {
                    pct: analysis.distance_from_high_pct.toFixed(2),
                  })}
                </span>
              )}
              {analysis.target_rate && (
                <span
                  className={cn(
                    "inline-flex items-center gap-1 text-xs rounded-full px-2 py-0.5",
                    analysis.target_hit
                      ? "bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300"
                      : "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300",
                  )}
                >
                  {analysis.target_hit
                    ? t("fx_watch.target.hit")
                    : t("fx_watch.target.away", {
                        pct: (analysis.target_distance_pct ?? 0).toFixed(2),
                      })}
                </span>
              )}
              <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
                <span>
                  {t("fx_watch.indicator.consecutive", {
                    current: analysis.consecutive_increases,
                    threshold: analysis.consecutive_threshold,
                  })}
                </span>
                <span className="flex gap-0.5">
                  {Array.from({ length: analysis.consecutive_threshold }).map((_, i) => (
                    <span
                      key={i}
                      className={`inline-block w-1.5 h-1.5 rounded-full ${
                        i < analysis.consecutive_increases ? "bg-primary" : "bg-muted-foreground/30"
                      }`}
                    />
                  ))}
                </span>
              </span>
              {watch.last_alerted_at && (
                <span className="text-xs text-muted-foreground">
                  {formatLocalTime(watch.last_alerted_at)}
                </span>
              )}
            </div>
          )}
        </div>

        <ChevronDown
          className={cn(
            "h-3.5 w-3.5 text-muted-foreground shrink-0 transition-transform duration-200",
            expanded && "rotate-180",
          )}
        />
      </div>
    </button>
  )
}
