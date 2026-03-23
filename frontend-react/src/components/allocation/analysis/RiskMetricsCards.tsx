import { Info } from "lucide-react"
import { useTranslation } from "react-i18next"
import { useTerminology } from "@/hooks/useTerminology"
import { Skeleton } from "@/components/ui/skeleton"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import type { RiskMetrics } from "@/api/hooks/useAnalytics"

interface Props {
  data: RiskMetrics | undefined
  isLoading?: boolean
}

function ratingColor(
  value: number | null | undefined,
  thresholds: { good: number; moderate: number },
): string {
  if (value == null) return "text-muted-foreground"
  if (value >= thresholds.good) return "text-green-500"
  if (value >= thresholds.moderate) return "text-yellow-500"
  return "text-red-500"
}

function drawdownColor(pct: number): string {
  const abs = Math.abs(pct)
  if (abs < 0.1) return "text-green-500"
  if (abs < 0.2) return "text-yellow-500"
  return "text-red-500"
}

function MetricCard({
  label,
  value,
  tooltip,
  colorClass,
  unavailableHint,
}: {
  label: string
  value: string
  tooltip: string
  colorClass?: string
  unavailableHint?: string
}) {
  const { t } = useTranslation()
  const isUnavailable = value === t("common.unavailable")
  return (
    <div className="rounded-lg border bg-card p-3 space-y-1">
      <div className="flex items-center gap-1">
        <span className="text-xs text-muted-foreground">{label}</span>
        <Tooltip>
          <TooltipTrigger asChild>
            <Info className="h-3 w-3 text-muted-foreground cursor-help" aria-label={tooltip} />
          </TooltipTrigger>
          <TooltipContent>
            <p className="max-w-[200px]">{tooltip}</p>
          </TooltipContent>
        </Tooltip>
      </div>
      {isUnavailable && unavailableHint ? (
        <Tooltip>
          <TooltipTrigger asChild>
            <p className="text-lg font-semibold tabular-nums text-muted-foreground cursor-help">
              {value}
            </p>
          </TooltipTrigger>
          <TooltipContent>
            <p className="max-w-[220px]">{unavailableHint}</p>
          </TooltipContent>
        </Tooltip>
      ) : (
        <p className={`text-lg font-semibold tabular-nums ${colorClass ?? ""}`}>{value}</p>
      )}
    </div>
  )
}

export function RiskMetricsCards({ data, isLoading }: Props) {
  const { t } = useTranslation()
  const { term } = useTerminology()
  const unavailableValue = t("common.unavailable")

  if (isLoading) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-5 w-32" />
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-[72px]" />
          ))}
        </div>
      </div>
    )
  }

  if (!data) return null

  const fmtPct = (v: number) => {
    if (!Number.isFinite(v) || Math.abs(v) > 100) return unavailableValue
    return `${(v * 100).toFixed(2)}%`
  }
  const fmtRatio = (v: number | null | undefined) => {
    if (v == null || !Number.isFinite(v) || Math.abs(v) > 1000) {
      return unavailableValue
    }
    return v.toFixed(2)
  }

  const unavailableHint = t("analytics.metric_unavailable_hint")

  return (
    <div className="space-y-2" role="img" aria-label={t("accessibility.chart_risk_metrics")}>
      <p className="text-sm font-semibold">{t("analytics.risk_metrics_title")}</p>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <MetricCard
          label={t("analytics.annualized_return")}
          value={fmtPct(data.annualized_return)}
          tooltip={t("analytics.annualized_return_tooltip")}
          colorClass={data.annualized_return >= 0 ? "text-green-500" : "text-red-500"}
          unavailableHint={unavailableHint}
        />
        <MetricCard
          label={term("volatility", t("analytics.volatility"))}
          value={fmtPct(data.annualized_volatility)}
          tooltip={t("analytics.volatility_tooltip")}
          unavailableHint={unavailableHint}
        />
        <MetricCard
          label={term("sharpe", t("analytics.sharpe_ratio"))}
          value={fmtRatio(data.sharpe_ratio)}
          tooltip={t("analytics.sharpe_tooltip")}
          colorClass={ratingColor(data.sharpe_ratio, { good: 1, moderate: 0.5 })}
          unavailableHint={unavailableHint}
        />
        <MetricCard
          label={term("sortino", t("analytics.sortino_ratio"))}
          value={fmtRatio(data.sortino_ratio)}
          tooltip={t("analytics.sortino_tooltip")}
          colorClass={ratingColor(data.sortino_ratio, { good: 1.5, moderate: 0.5 })}
          unavailableHint={unavailableHint}
        />
        <MetricCard
          label={term("max_drawdown", t("analytics.max_drawdown"))}
          value={fmtPct(data.max_drawdown_pct)}
          tooltip={t("analytics.max_drawdown_tooltip")}
          colorClass={drawdownColor(data.max_drawdown_pct)}
          unavailableHint={unavailableHint}
        />
        <MetricCard
          label={term("calmar", t("analytics.calmar_ratio"))}
          value={fmtRatio(data.calmar_ratio)}
          tooltip={t("analytics.calmar_tooltip")}
          colorClass={ratingColor(data.calmar_ratio, { good: 2, moderate: 1 })}
          unavailableHint={unavailableHint}
        />
      </div>
    </div>
  )
}
