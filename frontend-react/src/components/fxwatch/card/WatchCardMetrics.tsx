import { Minus, TrendingDown, TrendingUp } from "lucide-react"
import { useTranslation } from "react-i18next"
import { cn } from "@/lib/utils"
import { FINANCE_TEXT } from "@/lib/colors"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { GlossaryTerm } from "@/components/GlossaryTerm"
import type { FxAnalysis } from "@/api/types/fxWatch"

interface Props {
  analysis: FxAnalysis | undefined
  analysisLoading: boolean
  trendDirection: FxAnalysis["trend_direction"]
  signalStrength: FxAnalysis["signal_strength"]
  plainState: "good" | "watch" | "declining" | "none"
  showDetails: boolean
  setShowDetails: (updater: (v: boolean) => boolean) => void
}

function trendIcon(direction: FxAnalysis["trend_direction"]) {
  if (direction === "rising") return <TrendingUp className="h-3.5 w-3.5" />
  if (direction === "falling") return <TrendingDown className="h-3.5 w-3.5" />
  return <Minus className="h-3.5 w-3.5" />
}

export function WatchCardMetrics({
  analysis,
  analysisLoading,
  trendDirection,
  signalStrength,
  plainState,
  showDetails,
  setShowDetails,
}: Props) {
  const { t } = useTranslation()

  return (
    <div>
      <p className="font-medium text-muted-foreground mb-1.5">{t("fx_watch.analysis.title")}</p>

      {analysisLoading && !analysis ? (
        <div className="space-y-1">
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-3 w-4/5" />
        </div>
      ) : analysis ? (
        <div className="space-y-2">
          {analysis.target_hit && analysis.target_rate && (
            <div className="rounded-md border border-emerald-300/60 bg-emerald-500/10 px-2.5 py-2 text-emerald-700 dark:text-emerald-300">
              <p className="font-medium">
                {t("fx_watch.target.hit")} - {analysis.target_rate.toFixed(4)}
              </p>
              <p className="mt-1 text-[11px] leading-snug">{analysis.recommendation}</p>
            </div>
          )}
          <div
            className={cn(
              "rounded-md px-2.5 py-2 text-xs",
              plainState === "good" && "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
              plainState === "watch" && "bg-amber-500/10 text-amber-700 dark:text-amber-300",
              plainState === "declining" && "bg-rose-500/10 text-rose-700 dark:text-rose-300",
              plainState === "none" && "bg-muted/40 text-muted-foreground",
            )}
          >
            {analysis.recommendation}
          </div>

          <Button
            size="sm"
            variant="ghost"
            className="h-7 px-2 text-xs"
            onClick={() => setShowDetails((v) => !v)}
          >
            {showDetails
              ? t("fx_watch.analysis.hide_details")
              : t("fx_watch.analysis.show_details")}
          </Button>

          {showDetails && (
            <>
              <div className="flex items-center justify-between rounded-md bg-muted/40 px-2.5 py-1.5">
                <span className="text-muted-foreground">
                  <GlossaryTerm termKey="lookback_high">
                    {t("fx_watch.indicator.near_high", { days: analysis.lookback_days })}
                  </GlossaryTerm>
                </span>
                <span className={`font-medium ${analysis.is_recent_high ? FINANCE_TEXT.warning : "text-muted-foreground"}`}>
                  {analysis.is_recent_high ? t("common.yes") : t("common.unavailable")}
                  {analysis.lookback_high > 0 && ` ${analysis.lookback_high.toFixed(4)}`}
                </span>
              </div>

              <div className="flex items-center justify-between rounded-md bg-muted/40 px-2.5 py-1.5">
                <span className="text-muted-foreground">
                  {t("fx_watch.analysis.trend_direction")}
                </span>
                <span className="inline-flex items-center gap-1">
                  {trendIcon(trendDirection)}
                  {t(`fx_watch.analysis.trend_${trendDirection}`)}
                  <span className="text-muted-foreground">
                    ({analysis.trend_strength_pct >= 0 ? "+" : ""}
                    {analysis.trend_strength_pct.toFixed(2)}%)
                  </span>
                </span>
              </div>

              <div className="flex items-center justify-between rounded-md bg-muted/40 px-2.5 py-1.5">
                <span className="text-muted-foreground">
                  {t("fx_watch.analysis.high_recency")}
                </span>
                <span>{t("fx_watch.analysis.days_ago", { count: analysis.high_days_ago })}</span>
              </div>

              <div className="flex items-center justify-between rounded-md bg-muted/40 px-2.5 py-1.5">
                <span className="text-muted-foreground">
                  {t("fx_watch.analysis.distance_from_high")}
                </span>
                <span>{analysis.distance_from_high_pct.toFixed(2)}%</span>
              </div>

              <div className="flex items-center justify-between rounded-md bg-muted/40 px-2.5 py-1.5">
                <span className="text-muted-foreground">{t("fx_watch.analysis.signal_strength")}</span>
                <span
                  className={cn(
                    "font-medium",
                    signalStrength === "strong" && FINANCE_TEXT.loss,
                    signalStrength === "moderate" && FINANCE_TEXT.warning,
                    (signalStrength === "weak" || signalStrength === "none") && "text-muted-foreground",
                  )}
                >
                  {t(`fx_watch.analysis.signal_${signalStrength}`)}
                </span>
              </div>

              <div className="flex items-center justify-between rounded-md bg-muted/40 px-2.5 py-1.5">
                <span className="text-muted-foreground">
                  <GlossaryTerm termKey="consecutive_rises">
                    {t("fx_watch.indicator.consecutive", {
                      current: analysis.consecutive_increases,
                      threshold: analysis.consecutive_threshold,
                    })}
                  </GlossaryTerm>
                </span>
                <span className="flex gap-0.5 items-center">
                  {Array.from({ length: analysis.consecutive_threshold }).map((_, i) => (
                    <span
                      key={i}
                      className={`inline-block w-2 h-2 rounded-full ${
                        i < analysis.consecutive_increases ? "bg-primary" : "bg-muted-foreground/30"
                      }`}
                    />
                  ))}
                </span>
              </div>

              <p className="text-muted-foreground leading-snug">{analysis.reasoning}</p>
            </>
          )}
        </div>
      ) : (
        <p className="text-muted-foreground">{t("fx_watch.analysis.waiting")}</p>
      )}
    </div>
  )
}
