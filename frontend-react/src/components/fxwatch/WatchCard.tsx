import { useState, useMemo } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { formatSignedPct } from "@/lib/format"
import { Card, CardContent } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import { useToggleFxWatch, useDeleteFxWatch, useFxHistory } from "@/api/hooks/useFxWatch"
import { usePrivacyMode } from "@/hooks/usePrivacyMode"
import { FxChart } from "./FxChart"
import { WatchCardHeader } from "./card/WatchCardHeader"
import { WatchCardActions } from "./card/WatchCardActions"
import { WatchCardMetrics } from "./card/WatchCardMetrics"
import { WatchCardInsights } from "./card/WatchCardInsights"
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

function safeTrendDirection(direction: string | undefined): FxAnalysis["trend_direction"] {
  if (direction === "rising" || direction === "falling" || direction === "sideways")
    return direction
  return "sideways"
}

function safeSignalStrength(strength: string | undefined): FxAnalysis["signal_strength"] {
  if (
    strength === "strong" ||
    strength === "moderate" ||
    strength === "weak" ||
    strength === "none"
  )
    return strength
  return "none"
}

function getPlainSignalState(
  analysis: FxAnalysis | undefined,
  trendDirection: FxAnalysis["trend_direction"],
): "good" | "watch" | "declining" | "none" {
  if (!analysis) return "none"
  if (trendDirection === "falling" && analysis.is_recent_high) return "declining"
  if (analysis.should_alert && analysis.signal_strength === "strong") return "good"
  if (
    analysis.should_alert ||
    analysis.signal_strength === "moderate" ||
    analysis.signal_strength === "weak"
  ) {
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
  const rateStr = currentRate != null ? currentRate.toFixed(4) : t("common.unavailable")

  const dailyChangePct = useMemo(
    () => computeDailyChangePct(sparklineData ?? historyData ?? []),
    [sparklineData, historyData],
  )
  const dailyChangeStr = dailyChangePct !== null ? formatSignedPct(dailyChangePct, 2) : null

  const trendDirection = safeTrendDirection(analysis?.trend_direction)
  const signalStrength = safeSignalStrength(analysis?.signal_strength)
  const plainState = getPlainSignalState(analysis, trendDirection)

  const targetDirectionLabel = watch.target_direction
    ? watch.target_direction === "above"
      ? t("fx_watch.form.target_direction_above")
      : t("fx_watch.form.target_direction_below")
    : null

  const badgeVariant = !watch.is_active
    ? "secondary"
    : plainState === "good"
      ? "default"
      : "outline"
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

  const borderAccent = analysis?.should_alert
    ? "border-l-4 border-l-destructive"
    : "border-l-4 border-l-border"
  const cardOpacity = watch.is_active ? "" : "opacity-60"

  return (
    <Card className={`${borderAccent} ${cardOpacity} transition-opacity`}>
      <CardContent className="p-0">
        <WatchCardHeader
          watch={watch}
          analysis={analysis}
          sparklineData={sparklineData}
          pair={pair}
          rateStr={rateStr}
          dailyChangePct={dailyChangePct}
          dailyChangeStr={dailyChangeStr}
          badgeVariant={badgeVariant}
          badgeLabel={badgeLabel}
          trendDirection={trendDirection}
          isPrivate={isPrivate}
          expanded={expanded}
          setExpanded={setExpanded}
        />

        {expanded && (
          <div className="px-4 pb-4 space-y-3">
            <Separator />

            <WatchCardActions
              watch={watch}
              pair={pair}
              handleToggle={handleToggle}
              handleDeleteConfirm={handleDeleteConfirm}
              togglePending={toggle.isPending}
              deletePending={del.isPending}
            />

            {isPrivate ? (
              <p className="text-sm text-muted-foreground">{t("fx_watch.privacy_enabled")}</p>
            ) : (
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-[3fr_2fr]">
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

                <div className="space-y-3 text-xs">
                  <WatchCardMetrics
                    analysis={analysis}
                    analysisLoading={analysisLoading}
                    trendDirection={trendDirection}
                    signalStrength={signalStrength}
                    plainState={plainState}
                    showDetails={showDetails}
                    setShowDetails={setShowDetails}
                  />

                  <Separator />

                  <WatchCardInsights watch={watch} targetDirectionLabel={targetDirectionLabel} />
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
