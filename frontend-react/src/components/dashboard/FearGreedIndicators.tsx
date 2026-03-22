import { useCallback, useMemo } from "react"
import { useTranslation } from "react-i18next"
import { AreaSeries, type IChartApi } from "lightweight-charts"
import { LightweightChartWrapper } from "@/components/LightweightChartWrapper"
import { FINANCE_TEXT } from "@/lib/colors"
import type { FearGreedResponse, Snapshot } from "@/api/types/dashboard"

export const FEAR_GREED_BANDS = [
  {
    range: [0, 25] as [number, number],
    color: "#dc2626",
    labelKey: "config.fear_greed.extreme_fear",
    emoji: "😱",
  },
  {
    range: [25, 45] as [number, number],
    color: "#f97316",
    labelKey: "config.fear_greed.fear",
    emoji: "😨",
  },
  {
    range: [45, 55] as [number, number],
    color: "#eab308",
    labelKey: "config.fear_greed.neutral",
    emoji: "😐",
  },
  {
    range: [55, 75] as [number, number],
    color: "#86efac",
    labelKey: "config.fear_greed.greed",
    emoji: "🤑",
  },
  {
    range: [75, 100] as [number, number],
    color: "#16a34a",
    labelKey: "config.fear_greed.extreme_greed",
    emoji: "🤯",
  },
]

export function stripLeadingEmoji(label: string): string {
  return label.replace(/^(?:\p{Extended_Pictographic}|\uFE0F|\u200D)+\s*/u, "").trim()
}

export function scoreToColor(score: number): string {
  if (!Number.isFinite(score)) return FEAR_GREED_BANDS[FEAR_GREED_BANDS.length - 1].color
  const clamped = Math.max(0, Math.min(100, score))
  for (const band of FEAR_GREED_BANDS) {
    if (clamped >= band.range[0] && clamped <= band.range[1]) return band.color
  }
  return FEAR_GREED_BANDS[FEAR_GREED_BANDS.length - 1].color
}

/** Semi-circle SVG gauge for Fear & Greed (0-100). */
export function FearGreedGauge({ score, level }: { score: number; level: string }) {
  const { t } = useTranslation()
  const cx = 100
  const cy = 100
  const r = 70
  const strokeW = 16

  function polarToCartesian(angleDeg: number) {
    const rad = (angleDeg * Math.PI) / 180
    return {
      x: cx + r * Math.cos(Math.PI - rad),
      y: cy - r * Math.sin(Math.PI - rad),
    }
  }

  function arcPath(pct1: number, pct2: number) {
    const a1 = (pct1 / 100) * 180
    const a2 = (pct2 / 100) * 180
    const p1 = polarToCartesian(a1)
    const p2 = polarToCartesian(a2)
    const largeArc = a2 - a1 > 180 ? 1 : 0
    return `M ${p1.x} ${p1.y} A ${r} ${r} 0 ${largeArc} 1 ${p2.x} ${p2.y}`
  }

  const needleAngleDeg = (score / 100) * 180
  const needleBase1 = polarToCartesian(needleAngleDeg - 5)
  const needleBase2 = polarToCartesian(needleAngleDeg + 5)
  const tipX = cx + (r - strokeW / 2 - 4) * Math.cos(Math.PI - (needleAngleDeg * Math.PI) / 180)
  const tipY = cy - (r - strokeW / 2 - 4) * Math.sin(Math.PI - (needleAngleDeg * Math.PI) / 180)

  const clampedScore = Math.max(0, Math.min(100, score))
  const currentBand = FEAR_GREED_BANDS.find(
    (band) => clampedScore >= band.range[0] && clampedScore <= band.range[1],
  )
  const gaugeTitle = stripLeadingEmoji(currentBand ? t(currentBand.labelKey) : level)
  const gaugeEmoji = currentBand?.emoji

  return (
    <svg viewBox="0 0 200 128" className="w-full" style={{ maxHeight: 170 }}>
      <path
        d={arcPath(0, 100)}
        fill="none"
        stroke="rgba(128,128,128,0.15)"
        strokeWidth={strokeW}
        strokeLinecap="butt"
      />
      {FEAR_GREED_BANDS.map((band) => (
        <path
          key={band.labelKey}
          d={arcPath(band.range[0], band.range[1])}
          fill="none"
          stroke={band.color}
          strokeWidth={strokeW}
          strokeLinecap="butt"
          opacity={0.85}
        />
      ))}
      <polygon
        points={`${tipX},${tipY} ${needleBase1.x},${needleBase1.y} ${cx},${cy} ${needleBase2.x},${needleBase2.y}`}
        fill="currentColor"
        opacity={0.7}
      />
      <circle cx={cx} cy={cy} r={5} fill="currentColor" opacity={0.7} />
      <text
        x={cx}
        y={cy - 18}
        textAnchor="middle"
        fontSize={22}
        fontWeight="bold"
        fill="currentColor"
      >
        {score}
      </text>
      <text x={cx} y={cy - 4} textAnchor="middle" fontSize={10} fill="currentColor" opacity={0.6}>
        /100
      </text>
      {gaugeEmoji && (
        <foreignObject x={cx - 14} y={cy + 1} width={28} height={24}>
          <div className="text-center text-base leading-none">{gaugeEmoji}</div>
        </foreignObject>
      )}
      <text x={cx} y={cy + 22} textAnchor="middle" fontSize={11} fill="currentColor" opacity={0.75}>
        {gaugeTitle}
      </text>
    </svg>
  )
}

interface ComponentBarsProps {
  components: FearGreedResponse["components"]
}

export function FearGreedComponentBars({ components }: ComponentBarsProps) {
  const { t } = useTranslation()
  if (!components || components.length === 0) return null

  return (
    <div className="mt-2 space-y-1">
      {components.map((c) => {
        const score = c.score
        const label = t(`config.fear_greed.components.${c.name}`, { defaultValue: c.name })
        const weightPct = Math.round(c.weight * 100)
        return (
          <div key={c.name} className="flex items-center gap-2">
            <span className="w-24 shrink-0 text-right text-[10px] text-muted-foreground leading-none">
              {label}
            </span>
            <div className="relative flex-1 h-2 rounded-full overflow-hidden bg-muted/40">
              {score != null ? (
                <div
                  className="absolute left-0 top-0 h-full rounded-full transition-all"
                  style={{ width: `${score}%`, backgroundColor: scoreToColor(score) }}
                />
              ) : (
                <div className="absolute left-0 top-0 h-full w-full bg-muted/20" />
              )}
            </div>
            <span className="w-7 shrink-0 text-[10px] text-muted-foreground tabular-nums">
              {score != null ? score : "–"}
            </span>
            <span className="w-7 shrink-0 text-[10px] text-muted-foreground/50 tabular-nums">
              {weightPct}%
            </span>
          </div>
        )
      })}
    </div>
  )
}

export function SparklineMini({ snapshots }: { snapshots: Snapshot[] }) {
  const { t } = useTranslation()
  const { recent, isUp } = useMemo(() => {
    const cutoff = new Date()
    cutoff.setDate(cutoff.getDate() - 30)
    const cutoffStr = cutoff.toISOString().slice(0, 10)
    const recentSnapshots = snapshots.filter((snapshot) => snapshot.snapshot_date >= cutoffStr)
    const vals = recentSnapshots.map((snapshot) => snapshot.total_value)
    return { recent: recentSnapshots, isUp: vals.length >= 2 && vals[vals.length - 1] >= vals[0] }
  }, [snapshots])

  const onInit = useCallback(
    (chart: IChartApi) => {
      chart.applyOptions({
        crosshair: { vertLine: { visible: false }, horzLine: { visible: false } },
        grid: { vertLines: { visible: false }, horzLines: { visible: false } },
        timeScale: { visible: false },
        rightPriceScale: { visible: false },
        handleScroll: false,
        handleScale: false,
      })

      const series = chart.addSeries(AreaSeries, {
        lineColor: isUp ? "#16a34a" : "#dc2626",
        topColor: isUp ? "rgba(22,163,74,0.25)" : "rgba(220,38,38,0.25)",
        bottomColor: "rgba(0,0,0,0)",
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      })

      series.setData(
        recent.map((s) => ({
          time: s.snapshot_date as `${number}-${number}-${number}`,
          value: s.total_value,
        })),
      )
    },
    [recent, isUp],
  )

  if (recent.length < 2) return null

  return (
    <LightweightChartWrapper
      height={60}
      onInit={onInit}
      ariaLabel={t("accessibility.chart_portfolio_sparkline")}
    />
  )
}

// Re-export FINANCE_TEXT for use in PortfolioPulse that previously used it after these helpers
export { FINANCE_TEXT }
