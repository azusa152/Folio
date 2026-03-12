import { useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { useTerminology } from "@/hooks/useTerminology"
import { Skeleton } from "@/components/ui/skeleton"
import { Button } from "@/components/ui/button"
import { useAllocRebalance } from "@/api/hooks/useAllocation"
import { useDrawdown, useRiskMetrics } from "@/api/hooks/useAnalytics"
import { CATEGORY_TO_ASSET_CLASS, CURRENCY_TO_REGION } from "@/lib/constants"
import type { HoldingDetail } from "@/api/types/allocation"
import { HealthScore } from "./HealthScore"
import { AllocationCharts } from "./AllocationCharts"
import { GeographicAllocation } from "./GeographicAllocation"
import { AssetClassDonut } from "./AssetClassDonut"
import { DrawdownChart } from "./DrawdownChart"
import { RiskMetricsCards } from "./RiskMetricsCards"
import { ANALYTICS_TIMEFRAMES, type AnalyticsTimeframe } from "./timeframe"
import { DriftChart } from "./DriftChart"
import { HoldingsTable } from "../holdings/HoldingsTable"
import { XRayOverlap } from "./XRayOverlap"
import { SectorHeatmap } from "./SectorHeatmap"

interface Props {
  displayCurrency: string
  privacyMode: boolean
  enabled: boolean
}

type DrillSource = "category" | "geo" | "asset_class"

function formatDateYYYYMMDD(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const day = String(date.getDate()).padStart(2, "0")
  return `${year}-${month}-${day}`
}

function filterHoldingsByDrill(
  holdings: HoldingDetail[],
  source: DrillSource,
  value: string,
): HoldingDetail[] {
  switch (source) {
    case "category":
      return holdings.filter((h) => h.category === value)
    case "geo":
      return holdings.filter((h) => (CURRENCY_TO_REGION[h.currency] ?? "Other") === value)
    case "asset_class":
      return holdings.filter((h) => (CATEGORY_TO_ASSET_CLASS[h.category] ?? "Equity") === value)
  }
}

export function RebalanceAnalysis({ displayCurrency, privacyMode, enabled }: Props) {
  const { t } = useTranslation()
  const { term } = useTerminology()
  const { data, isLoading } = useAllocRebalance(displayCurrency, enabled)
  const [analyticsTimeframe, setAnalyticsTimeframe] = useState<AnalyticsTimeframe>(365)
  const [drill, setDrill] = useState<{ source: DrillSource; value: string } | null>(null)

  const drillHandlers = useMemo(() => ({
    category: (v: string | null) => setDrill(v ? { source: "category" as const, value: v } : null),
    geo: (v: string | null) => setDrill(v ? { source: "geo" as const, value: v } : null),
    asset_class: (v: string | null) => setDrill(v ? { source: "asset_class" as const, value: v } : null),
  }), [])
  const analyticsRange = useMemo(() => {
    if (analyticsTimeframe === 0) return { start: undefined, end: undefined }

    const endDate = new Date()
    const startDate = new Date()
    startDate.setDate(endDate.getDate() - analyticsTimeframe)
    return {
      start: formatDateYYYYMMDD(startDate),
      end: formatDateYYYYMMDD(endDate),
    }
  }, [analyticsTimeframe])
  const {
    data: drawdownData,
    isLoading: drawdownLoading,
    isError: drawdownError,
  } = useDrawdown(
    analyticsRange.start,
    analyticsRange.end,
    enabled,
  )
  const {
    data: riskData,
    isLoading: riskLoading,
    isError: riskError,
  } = useRiskMetrics(
    analyticsRange.start,
    analyticsRange.end,
    enabled,
  )

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    )
  }

  if (!data) {
    return <p className="text-sm text-muted-foreground">{t("allocation.loading")}</p>
  }

  return (
    <div className="space-y-6">
      {/* Health score */}
      <HealthScore
        score={data.health_score}
        level={data.health_level}
        calculatedAt={data.calculated_at}
      />

      {/* Rebalance advice */}
      {data.advice && data.advice.length > 0 && (
        <section className="space-y-1">
          <p className="text-sm font-semibold">{term("rebalance", t("allocation.health.advice_title"))}</p>
          <ul className="space-y-1">
            {data.advice.map((a) => (
              <li key={a} className="text-xs text-muted-foreground">• {a}</li>
            ))}
          </ul>
        </section>
      )}

      <hr className="border-border" />

      {/* Allocation charts */}
      <AllocationCharts
        categories={data.categories}
        holdings={data.holdings_detail}
        privacyMode={privacyMode}
        displayCurrency={displayCurrency}
        drillValue={drill?.source === "category" ? drill.value : null}
        onDrillChange={drillHandlers.category}
      />

      {drill?.source === "category" && (
        <div className="space-y-2">
          <Button variant="ghost" size="sm" className="text-xs" onClick={() => setDrill(null)}>
            {t("allocation.clear_filter")}
          </Button>
          <HoldingsTable
            holdings={filterHoldingsByDrill(data.holdings_detail, drill.source, drill.value)}
            privacyMode={privacyMode}
            displayCurrency={displayCurrency}
          />
        </div>
      )}

      <hr className="border-border" />

      {/* Geographic + Asset class charts */}
      {(data.geographic_allocation || data.asset_class_allocation) && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {data.geographic_allocation && (
              <GeographicAllocation
                data={data.geographic_allocation}
                holdings={data.holdings_detail}
                privacyMode={privacyMode}
                displayCurrency={displayCurrency}
                drillValue={drill?.source === "geo" ? drill.value : null}
                onDrillChange={drillHandlers.geo}
              />
            )}
            {data.asset_class_allocation && (
              <AssetClassDonut
                data={data.asset_class_allocation}
                holdings={data.holdings_detail}
                privacyMode={privacyMode}
                displayCurrency={displayCurrency}
                drillValue={drill?.source === "asset_class" ? drill.value : null}
                onDrillChange={drillHandlers.asset_class}
              />
            )}
          </div>

          {drill && (drill.source === "geo" || drill.source === "asset_class") && (
            <div className="space-y-2">
              <Button variant="ghost" size="sm" className="text-xs" onClick={() => setDrill(null)}>
                {t("allocation.clear_filter")}
              </Button>
              <HoldingsTable
                holdings={filterHoldingsByDrill(data.holdings_detail, drill.source, drill.value)}
                privacyMode={privacyMode}
                displayCurrency={displayCurrency}
              />
            </div>
          )}

          <hr className="border-border" />
        </>
      )}

      {/* Drift chart */}
      <DriftChart categories={data.categories} />

      <hr className="border-border" />

      {/* Holdings detail table */}
      <HoldingsTable
        holdings={data.holdings_detail}
        privacyMode={privacyMode}
        displayCurrency={displayCurrency}
      />

      <hr className="border-border" />

      {/* X-Ray overlap */}
      <XRayOverlap
        xray={data.xray ?? []}
        coveragePct={data.xray_coverage_pct ?? 0}
        skippedEtfs={data.xray_skipped_etfs ?? []}
      />

      <hr className="border-border" />

      {/* Sector heatmap */}
      {data.sector_exposure && (
        <SectorHeatmap data={data.sector_exposure} />
      )}

      <hr className="border-border" />

      {/* Risk metrics + Drawdown — shared timeframe selector */}
      <section className="space-y-4">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div>
            <p className="text-sm font-semibold">{t("analytics.risk_section_title")}</p>
            <p className="text-xs text-muted-foreground">{t("analytics.risk_section_subtitle")}</p>
          </div>
          <div className="flex items-center gap-1">
            {ANALYTICS_TIMEFRAMES.map((option) => (
              <Button
                key={option.value}
                type="button"
                size="sm"
                variant={analyticsTimeframe === option.value ? "default" : "outline"}
                aria-pressed={analyticsTimeframe === option.value}
                onClick={() => setAnalyticsTimeframe(option.value)}
                className="min-h-[32px] px-2 text-[11px]"
              >
                {t(`analytics.timeframe.${option.key}`)}
              </Button>
            ))}
          </div>
        </div>
        <RiskMetricsCards data={riskData} isLoading={riskLoading} />
        <DrawdownChart data={drawdownData ?? []} isLoading={drawdownLoading} />
        {(drawdownError || riskError) && (
          <p className="text-xs text-destructive">{t("common.error")}</p>
        )}
      </section>
    </div>
  )
}
