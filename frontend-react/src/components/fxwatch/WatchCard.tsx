import { useState, useMemo } from "react"
import { ChevronDown, Minus, TrendingDown, TrendingUp } from "lucide-react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { cn, formatLocalTime } from "@/lib/utils"
import { FINANCE_TEXT } from "@/lib/colors"
import { formatSignedPct } from "@/lib/format"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { useToggleFxWatch, useDeleteFxWatch, useFxHistory } from "@/api/hooks/useFxWatch"
import { usePrivacyMode } from "@/hooks/usePrivacyMode"
import { FxChart } from "./FxChart"
import { FxSparkline } from "./FxSparkline"
import { EditWatchPopover } from "./EditWatchPopover"
import { GlossaryTerm } from "@/components/GlossaryTerm"
import type { FxWatch, FxAnalysis, FxHistoryPoint } from "@/api/types/fxWatch"

interface Props {
  watch: FxWatch
  analysis: FxAnalysis | undefined
  analysisLoading?: boolean
  sparklineData?: FxHistoryPoint[]
}

function computeDailyChangePct(data: FxHistoryPoint[]): number | null {
  if (data.length < 2) return null
  const prev = data[data.length - 2].close
  const curr = data[data.length - 1].close
  if (prev <= 0) return null
  return ((curr - prev) / prev) * 100
}

function formatChangePct(pct: number | null): string | null {
  if (pct === null) return null
  return formatSignedPct(pct, 2)
}

function trendIcon(direction: FxAnalysis["trend_direction"]) {
  if (direction === "rising") return <TrendingUp className="h-3.5 w-3.5" />
  if (direction === "falling") return <TrendingDown className="h-3.5 w-3.5" />
  return <Minus className="h-3.5 w-3.5" />
}

function safeTrendDirection(
  direction: string | undefined,
): FxAnalysis["trend_direction"] {
  if (direction === "rising" || direction === "falling" || direction === "sideways") {
    return direction
  }
  return "sideways"
}

function safeSignalStrength(
  strength: string | undefined,
): FxAnalysis["signal_strength"] {
  if (
    strength === "strong" ||
    strength === "moderate" ||
    strength === "weak" ||
    strength === "none"
  ) {
    return strength
  }
  return "none"
}

function getPlainSignalState(
  analysis: FxAnalysis | undefined,
  trendDirection: FxAnalysis["trend_direction"],
): "good" | "watch" | "declining" | "none" {
  if (!analysis) return "none"
  if (trendDirection === "falling" && analysis.is_recent_high) return "declining"
  if (analysis.should_alert && analysis.signal_strength === "strong") return "good"
  if (analysis.should_alert || analysis.signal_strength === "moderate" || analysis.signal_strength === "weak") {
    return "watch"
  }
  return "none"
}

export function WatchCard({ watch, analysis, analysisLoading = false, sparklineData }: Props) {
  const { t } = useTranslation()
  const [expanded, setExpanded] = useState(false)
  const [showDetails, setShowDetails] = useState(false)
  const isPrivate = usePrivacyMode((s) => s.isPrivate)

  const toggle = useToggleFxWatch()
  const del = useDeleteFxWatch()

  const needsHistory = expanded && !isPrivate && !sparklineData
  const { data: historyData, isLoading: historyLoading } = useFxHistory(
    watch.base_currency,
    watch.quote_currency,
    needsHistory,
  )

  const pair = `${watch.base_currency}/${watch.quote_currency}`
  const currentRate = analysis?.current_rate
  const rateStr =
    currentRate != null ? currentRate.toFixed(4) : t("common.unavailable")

  const dailyChangePct = useMemo(
    () => computeDailyChangePct(sparklineData ?? historyData ?? []),
    [sparklineData, historyData],
  )
  const dailyChangeStr = formatChangePct(dailyChangePct)

  const handleToggle = () => {
    toggle.mutate(
      { id: watch.id, isActive: watch.is_active },
      {
        onSuccess: () => toast.success(t("common.success")),
        onError: () => toast.error(t("fx_watch.card.toggle_error")),
      },
    )
  }

  const handleDeleteConfirm = () => {
    del.mutate(watch.id, {
      onError: () => toast.error(t("fx_watch.card.delete_error")),
    })
  }
  const trendDirection = safeTrendDirection(analysis?.trend_direction)
  const signalStrength = safeSignalStrength(analysis?.signal_strength)
  const plainState = getPlainSignalState(analysis, trendDirection)
  const targetDirectionLabel = watch.target_direction
    ? watch.target_direction === "above"
      ? t("fx_watch.form.target_direction_above")
      : t("fx_watch.form.target_direction_below")
    : null

  // Badge variant
  const badgeVariant = !watch.is_active ? "secondary" : plainState === "good" ? "default" : "outline"

  const badgeLabel = !watch.is_active
    ? t("fx_watch.badge.inactive")
    : analysisLoading && !analysis
      ? t("fx_watch.badge.loading")
      : plainState === "good"
        ? t("fx_watch.badge.good_time")
        : plainState === "watch"
          ? t("fx_watch.badge.watch")
          : plainState === "declining"
            ? t("fx_watch.badge.declining")
            : analysis
              ? t("fx_watch.badge.normal")
              : t("common.unavailable")

  const borderAccent = analysis?.should_alert
    ? "border-l-4 border-l-destructive"
    : "border-l-4 border-l-border"

  const cardOpacity = watch.is_active ? "" : "opacity-60"

  return (
    <Card className={`${borderAccent} ${cardOpacity} transition-opacity`}>
      <CardContent className="p-0">
        {/* Collapsible header */}
        <button
          onClick={() => setExpanded((v) => !v)}
          aria-expanded={expanded}
          className="w-full text-left px-4 py-3 hover:bg-muted/30 transition-colors rounded-[inherit]"
        >
          <div className="flex items-center gap-3">
            {/* Sparkline — shows skeleton while data loads */}
            {!isPrivate && (
              <FxSparkline data={sparklineData} />
            )}

            {/* Main info */}
            <div className="flex-1 min-w-0">
              {/* Row 1: pair + rate + change + badge */}
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm font-semibold">{pair}</span>
                {!isPrivate && (
                  <span className="text-sm tabular-nums text-foreground">{rateStr}</span>
                )}
                {!isPrivate && dailyChangeStr && (
                  <span
                    className={`text-xs font-medium tabular-nums ${
                      (dailyChangePct ?? 0) >= 0
                        ? FINANCE_TEXT.gain
                        : FINANCE_TEXT.loss
                    }`}
                  >
                    {dailyChangeStr}
                  </span>
                )}
                <Badge variant={badgeVariant} className="text-xs h-5">
                  {badgeLabel}
                </Badge>
              </div>

              {/* Row 2: near-high pill + consecutive bar */}
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
                    <span>{t("fx_watch.indicator.consecutive", { current: analysis.consecutive_increases, threshold: analysis.consecutive_threshold })}</span>
                    <span className="flex gap-0.5">
                      {Array.from({ length: analysis.consecutive_threshold }).map((_, i) => (
                        <span
                          key={i}
                          className={`inline-block w-1.5 h-1.5 rounded-full ${
                            i < analysis.consecutive_increases
                              ? "bg-primary"
                              : "bg-muted-foreground/30"
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

            {/* Chevron */}
            <ChevronDown className={cn("h-3.5 w-3.5 text-muted-foreground shrink-0 transition-transform duration-200", expanded && "rotate-180")} />
          </div>
        </button>

        {expanded && (
          <div className="px-4 pb-4 space-y-3">
            <Separator />

            {/* Action row */}
            <div className="flex gap-2 flex-wrap">
              <Button
                size="sm"
                variant="outline"
                className="text-xs"
                onClick={handleToggle}
                disabled={toggle.isPending}
              >
                {toggle.isPending
                  ? t("common.loading")
                  : watch.is_active
                    ? t("fx_watch.card.disable")
                    : t("fx_watch.card.enable")}
              </Button>
              <EditWatchPopover watch={watch} />
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button size="sm" variant="destructive" className="text-xs">
                    {t("fx_watch.card.delete")}
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>{t("fx_watch.delete.title")}</AlertDialogTitle>
                    <AlertDialogDescription>
                      {t("fx_watch.delete.description", { pair })}
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>{t("common.cancel")}</AlertDialogCancel>
                    <AlertDialogAction onClick={handleDeleteConfirm} disabled={del.isPending}>
                      {t("common.confirm")}
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </div>

            {isPrivate ? (
              <p className="text-sm text-muted-foreground">{t("fx_watch.privacy_enabled")}</p>
            ) : (
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-[3fr_2fr]">
                {/* Left: chart */}
                <div>
                  {(sparklineData ?? historyData) ? (
                    <FxChart
                      data={(sparklineData ?? historyData)!}
                      recentHighDays={watch.recent_high_days}
                      targetRate={analysis?.target_rate}
                    />
                  ) : historyLoading ? (
                    <Skeleton className="h-[220px] w-full" />
                  ) : null}
                </div>

                {/* Right: structured analysis + settings */}
                <div className="space-y-3 text-xs">
                  {/* Structured analysis */}
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
                        {/* Near high indicator */}
                        <div className="flex items-center justify-between rounded-md bg-muted/40 px-2.5 py-1.5">
                          <span className="text-muted-foreground">
                            <GlossaryTerm termKey="lookback_high">
                              {t("fx_watch.indicator.near_high", { days: analysis.lookback_days })}
                            </GlossaryTerm>
                          </span>
                          <span className={`font-medium ${analysis.is_recent_high ? FINANCE_TEXT.warning : "text-muted-foreground"}`}>
                            {analysis.is_recent_high
                              ? t("common.yes")
                              : t("common.unavailable")}
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
                              (signalStrength === "weak" || signalStrength === "none") &&
                                "text-muted-foreground",
                            )}
                          >
                            {t(`fx_watch.analysis.signal_${signalStrength}`)}
                          </span>
                        </div>

                        {/* Consecutive rises bar */}
                        <div className="flex items-center justify-between rounded-md bg-muted/40 px-2.5 py-1.5">
                          <span className="text-muted-foreground">
                            <GlossaryTerm termKey="consecutive_rises">
                              {t("fx_watch.indicator.consecutive", { current: analysis.consecutive_increases, threshold: analysis.consecutive_threshold })}
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

                        {/* Recommendation text */}
                        <p className="text-muted-foreground leading-snug">
                          {analysis.reasoning}
                        </p>
                          </>
                        )}
                      </div>
                    ) : (
                      <p className="text-muted-foreground">{t("fx_watch.analysis.waiting")}</p>
                    )}
                  </div>

                  <Separator />

                  {/* Settings */}
                  <div className="space-y-0.5 text-muted-foreground">
                    <p className="font-medium text-foreground">{t("fx_watch.settings.title")}</p>
                    <p>{t("fx_watch.settings.recent_high", { days: watch.recent_high_days })}</p>
                    <p>{t("fx_watch.settings.consecutive", { days: watch.consecutive_increase_days })}</p>
                    <p>
                      <GlossaryTerm termKey="reminder_interval">
                        {t("fx_watch.settings.interval", { hours: watch.reminder_interval_hours })}
                      </GlossaryTerm>
                    </p>
                    <p>
                      {watch.target_rate && watch.target_direction
                        ? t("fx_watch.settings.target", {
                            direction: targetDirectionLabel,
                            rate: watch.target_rate.toFixed(4),
                          })
                        : t("fx_watch.settings.target_none")}
                    </p>
                    <p>{t("fx_watch.settings.high_alert", { icon: watch.alert_on_recent_high ? "✅" : "❌" })}</p>
                    <p>{t("fx_watch.settings.consec_alert", { icon: watch.alert_on_consecutive_increase ? "✅" : "❌" })}</p>
                    {watch.last_alerted_at ? (
                      <p>
                        {t("fx_watch.settings.last_alert_time", {
                          time: formatLocalTime(watch.last_alerted_at),
                        })}
                      </p>
                    ) : (
                      <p>{t("fx_watch.settings.last_alert_none")}</p>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
