import { useState, useCallback, useMemo } from "react"
import { useTranslation } from "react-i18next"
import {
  AreaSeries,
  BaselineSeries,
  CrosshairMode,
  LineStyle,
  type IChartApi,
} from "lightweight-charts"
import { LightweightChartWrapper } from "@/components/LightweightChartWrapper"
import { FINANCE_TEXT } from "@/lib/colors"
import { formatSignedPct } from "@/lib/format"
import type { FxHistoryPoint } from "@/api/types/fxWatch"

const PERIOD_OPTIONS = [
  { key: "1W", labelKey: "fx_watch.period.1w", days: 7 },
  { key: "1M", labelKey: "fx_watch.period.1m", days: 30 },
  { key: "2M", labelKey: "fx_watch.period.2m", days: 60 },
  { key: "3M", labelKey: "fx_watch.period.3m", days: 90 },
  { key: "6M", labelKey: "fx_watch.period.6m", days: 180 },
  { key: "1Y", labelKey: "fx_watch.period.1y", days: 365 },
]

interface Props {
  data: FxHistoryPoint[]
  recentHighDays: number
  targetRate?: number | null
}

function computeChangePct(slice: FxHistoryPoint[]): number | null {
  if (slice.length < 2) return null
  const first = slice[0].close
  const last = slice[slice.length - 1].close
  if (first <= 0) return null
  return ((last - first) / first) * 100
}

export function FxChart({ data, recentHighDays, targetRate = null }: Props) {
  const { t } = useTranslation()
  const [period, setPeriod] = useState("1M")

  const sliced = useMemo(() => {
    const n = PERIOD_OPTIONS.find((p) => p.key === period)?.days ?? 90
    return data.length >= n ? data.slice(-n) : data
  }, [data, period])

  const periodChangePct = useMemo(() => computeChangePct(sliced), [sliced])

  const onInit = useCallback(
    (chart: IChartApi) => {
      chart.applyOptions({
        crosshair: { mode: CrosshairMode.Normal },
        grid: { vertLines: { visible: false } },
        timeScale: { borderVisible: false, fixLeftEdge: true, fixRightEdge: true },
        rightPriceScale: { borderVisible: false },
      })

      const rates = sliced.map((d) => d.close)
      const isUp = rates.length >= 2 && rates[rates.length - 1] >= rates[0]

      const series = chart.addSeries(AreaSeries, {
        lineColor: isUp ? "#22c55e" : "#ef4444",
        topColor: isUp ? "rgba(34,197,94,0.18)" : "rgba(239,68,68,0.18)",
        bottomColor: "rgba(0,0,0,0)",
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: true,
        crosshairMarkerVisible: true,
        crosshairMarkerRadius: 4,
        priceFormat: { type: "price", precision: 4, minMove: 0.0001 },
      })

      series.setData(
        sliced.map((d) => ({
          time: d.date as `${number}-${number}-${number}`,
          value: d.close,
        })),
      )

      const recentSlice = sliced.slice(-recentHighDays)
      if (recentSlice.length > 0) {
        const recentHigh = Math.max(...recentSlice.map((d) => d.close))
        series.createPriceLine({
          price: recentHigh,
          color: "#f59e0b",
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title: t("fx_watch.chart.high_annotation", {
            days: recentHighDays,
            high: recentHigh.toFixed(4),
          }),
          lineVisible: true,
          axisLabelColor: "#f59e0b",
          axisLabelTextColor: "#fff",
        })
      }

      if (typeof targetRate === "number" && Number.isFinite(targetRate) && targetRate > 0) {
        const currentRate = sliced[sliced.length - 1]?.close ?? 0
        const distancePct =
          targetRate > 0 ? Math.abs(((targetRate - currentRate) / targetRate) * 100) : 0
        series.createPriceLine({
          price: targetRate,
          color: "#2563eb",
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title: t("fx_watch.chart.target_annotation", {
            target: targetRate.toFixed(4),
            distance: distancePct.toFixed(2),
          }),
          lineVisible: true,
          axisLabelColor: "#2563eb",
          axisLabelTextColor: "#fff",
        })

        if (currentRate > 0 && distancePct > 0) {
          const proximityBand = chart.addSeries(BaselineSeries, {
            baseValue: { type: "price", price: targetRate },
            topLineColor: "rgba(37,99,235,0)",
            topFillColor1: "rgba(37,99,235,0.14)",
            topFillColor2: "rgba(37,99,235,0.04)",
            bottomLineColor: "rgba(37,99,235,0)",
            bottomFillColor1: "rgba(37,99,235,0.14)",
            bottomFillColor2: "rgba(37,99,235,0.04)",
            priceLineVisible: false,
            lastValueVisible: false,
            crosshairMarkerVisible: false,
          })
          proximityBand.setData(
            sliced.map((d) => ({
              time: d.date as `${number}-${number}-${number}`,
              value: currentRate,
            })),
          )
        }
      }

      const trailingYear = data.slice(-365)
      if (trailingYear.length > 0) {
        const trailingYearHigh = Math.max(...trailingYear.map((d) => d.close))
        const trailingYearLow = Math.min(...trailingYear.map((d) => d.close))
        series.createPriceLine({
          price: trailingYearHigh,
          color: "#7c3aed",
          lineWidth: 1,
          lineStyle: LineStyle.Dotted,
          axisLabelVisible: false,
          title: "",
          lineVisible: true,
        })
        series.createPriceLine({
          price: trailingYearLow,
          color: "#64748b",
          lineWidth: 1,
          lineStyle: LineStyle.Dotted,
          axisLabelVisible: false,
          title: "",
          lineVisible: true,
        })
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [sliced, recentHighDays, targetRate, data],
  )

  if (!data || data.length < 5) {
    return <p className="text-xs text-muted-foreground">{t("fx_watch.chart.insufficient_data")}</p>
  }

  const changePctFormatted = periodChangePct !== null ? formatSignedPct(periodChangePct, 2) : null

  return (
    <div>
      <div className="flex items-center gap-2 mb-1.5 flex-wrap">
        <div className="flex gap-1">
          {PERIOD_OPTIONS.map((p) => (
            <button
              key={p.key}
              onClick={() => setPeriod(p.key)}
              className={`rounded px-2 py-0.5 text-xs border transition-colors ${
                period === p.key
                  ? "bg-primary text-primary-foreground border-primary"
                  : "border-border text-muted-foreground hover:text-foreground"
              }`}
            >
              {t(p.labelKey)}
            </button>
          ))}
        </div>
        {changePctFormatted && (
          <span
            className={`text-xs font-medium tabular-nums ${
              (periodChangePct ?? 0) >= 0 ? FINANCE_TEXT.gain : FINANCE_TEXT.loss
            }`}
          >
            {changePctFormatted}
          </span>
        )}
      </div>
      <LightweightChartWrapper
        key={period}
        height={220}
        onInit={onInit}
        ariaLabel={t("accessibility.chart_fx_rate")}
      />
    </div>
  )
}
