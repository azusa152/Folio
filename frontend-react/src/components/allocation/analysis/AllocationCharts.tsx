import { useState } from "react"
import { useTranslation } from "react-i18next"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
  LabelList,
  ResponsiveContainer,
} from "recharts"
import type { CategoryAllocation, HoldingDetail } from "@/api/types/allocation"
import {
  ALLOCATION_SMALL_THRESHOLD,
  CATEGORY_COLOR_MAP,
  CATEGORY_COLOR_FALLBACK,
} from "@/lib/constants"
import { useRechartsTheme } from "@/hooks/useRechartsTheme"
import { maskMoney } from "@/hooks/usePrivacyMode"
import { Button } from "@/components/ui/button"
import { HoldingsTable } from "../holdings/HoldingsTable"

const OTHER_COLOR = "#9CA3AF"

interface ChartRow {
  name: string
  target_pct: number
  current_pct: number
  drift_pct: number
  market_value: number
  color: string
  isOther: boolean
}

interface Props {
  categories: Record<string, CategoryAllocation>
  holdings?: HoldingDetail[]
  privacyMode?: boolean
  displayCurrency?: string
  drillValue?: string | null
  onDrillChange?: (value: string | null) => void
}

function getCategoryColor(name: string): string {
  return CATEGORY_COLOR_MAP[name] ?? CATEGORY_COLOR_FALLBACK
}

function driftColor(drift: number): string {
  const abs = Math.abs(drift)
  if (abs < 2) return "#22c55e"
  if (abs < 5) return "#f59e0b"
  return "#ef4444"
}

function driftSign(drift: number): string {
  return drift > 0 ? "+" : ""
}

function round1(v: number): number {
  return Math.round(v * 10) / 10
}

export function AllocationCharts({
  categories,
  holdings,
  privacyMode = false,
  displayCurrency = "USD",
  drillValue,
  onDrillChange,
}: Props) {
  const { t } = useTranslation()
  const theme = useRechartsTheme()
  const [localDrill, setLocalDrill] = useState<string | null>(null)
  const drillCategory = onDrillChange ? (drillValue ?? null) : localDrill
  const setDrillCategory = onDrillChange ?? setLocalDrill

  const entries = Object.entries(categories)
  const visible = entries.filter(
    ([, v]) =>
      v.target_pct >= ALLOCATION_SMALL_THRESHOLD || v.current_pct >= ALLOCATION_SMALL_THRESHOLD,
  )
  const hidden = entries.filter(
    ([, v]) =>
      v.target_pct < ALLOCATION_SMALL_THRESHOLD && v.current_pct < ALLOCATION_SMALL_THRESHOLD,
  )

  const otherCurrentPct = hidden.reduce((s, [, v]) => s + v.current_pct, 0)
  const otherTargetPct = hidden.reduce((s, [, v]) => s + v.target_pct, 0)
  const otherMarketValue = hidden.reduce((s, [, v]) => s + v.market_value, 0)
  const otherDrift = round1(otherCurrentPct - otherTargetPct)

  const otherLabel = t("allocation.charts.other")

  const chartData: ChartRow[] = [
    ...visible
      .map(([name, v]) => ({
        name,
        target_pct: v.target_pct,
        current_pct: v.current_pct,
        drift_pct: v.drift_pct,
        market_value: v.market_value,
        color: getCategoryColor(name),
        isOther: false,
      }))
      .sort((a, b) => b.current_pct - a.current_pct),
    ...(hidden.length > 0
      ? [
          {
            name: otherLabel,
            target_pct: round1(otherTargetPct),
            current_pct: round1(otherCurrentPct),
            drift_pct: otherDrift,
            market_value: otherMarketValue,
            color: OTHER_COLOR,
            isOther: true,
          },
        ]
      : []),
  ]

  const chartHeight = Math.max(160, chartData.length * 48 + 40)

  const handleBarClick = (_: unknown, index: number) => {
    const entry = chartData[index]
    if (!entry || entry.isOther) return
    setDrillCategory(entry.name === drillCategory ? null : entry.name)
  }

  return (
    <div className="space-y-4">
      {/* Title + legend */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <p className="text-sm font-semibold">{t("allocation.charts.title")}</p>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-2 w-4 rounded-sm bg-gray-400 opacity-70" />
            {t("allocation.charts.target")}
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-4 w-4 rounded-sm bg-primary" />
            {t("allocation.charts.actual")}
          </span>
        </div>
      </div>

      {/* Overlay bar chart — target (thin) + actual (thick) side-by-side per category */}
      <ResponsiveContainer width="100%" height={chartHeight}>
        <BarChart
          data={chartData}
          layout="vertical"
          barGap={3}
          barCategoryGap="35%"
          margin={{ top: 4, right: 56, left: 4, bottom: 4 }}
        >
          <XAxis
            type="number"
            domain={[0, 100]}
            tick={{ fontSize: 9, fill: theme.tickColor }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => `${v}%`}
          />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fontSize: 10, fill: theme.tickColor }}
            axisLine={false}
            tickLine={false}
            width={82}
          />
          <Tooltip
            contentStyle={theme.tooltipStyle}
            labelStyle={{ color: theme.tooltipText, fontWeight: 600, marginBottom: 4 }}
            cursor={{ fill: "rgba(128,128,128,0.06)" }}
            formatter={(
              value: unknown,
              name: string | undefined,
              props: { payload?: ChartRow },
            ) => {
              const row = props.payload
              const label = name ?? ""
              if (typeof value !== "number" || !row) return [`${value}`, label]
              if (name === t("allocation.charts.target")) {
                return [value > 0 ? `${value.toFixed(1)}%` : "—", label]
              }
              const drift = row.drift_pct
              return [
                `${value.toFixed(1)}%  (${driftSign(drift)}${drift.toFixed(1)}% drift)`,
                label,
              ]
            }}
          />

          {/* Target bar — thin, muted gray */}
          <Bar
            dataKey="target_pct"
            name={t("allocation.charts.target")}
            barSize={6}
            radius={[0, 2, 2, 0]}
          >
            {chartData.map((entry) => (
              <Cell key={entry.name} fill={OTHER_COLOR} opacity={0.65} />
            ))}
          </Bar>

          {/* Actual bar — thick, colored, clickable, with drift badge */}
          <Bar
            dataKey="current_pct"
            name={t("allocation.charts.actual")}
            barSize={20}
            radius={[0, 4, 4, 0]}
            cursor="pointer"
            onClick={handleBarClick}
          >
            {chartData.map((entry) => (
              <Cell
                key={entry.name}
                fill={entry.color}
                opacity={drillCategory && drillCategory !== entry.name ? 0.25 : 1}
              />
            ))}
            <LabelList
              dataKey="drift_pct"
              position="right"
              content={(props) => {
                const { x, y, width, height, value } = props as {
                  x?: number
                  y?: number
                  width?: number
                  height?: number
                  value?: unknown
                }
                if (typeof value !== "number") return null
                const xPos = (x ?? 0) + (width ?? 0) + 6
                const yPos = (y ?? 0) + (height ?? 0) / 2
                const sign = driftSign(value)
                return (
                  <text
                    x={xPos}
                    y={yPos}
                    fill={driftColor(value)}
                    fontSize={9}
                    dominantBaseline="middle"
                    fontWeight={500}
                  >
                    {`${sign}${value.toFixed(1)}%`}
                  </text>
                )
              }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Summary table */}
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-muted-foreground border-b border-border">
              <th className="text-left py-1.5 pr-2 font-medium">
                {t("allocation.charts.category")}
              </th>
              <th className="text-right py-1.5 px-2 font-medium">
                {t("allocation.charts.actual")}
              </th>
              <th className="text-right py-1.5 px-2 font-medium">
                {t("allocation.charts.target")}
              </th>
              <th className="text-right py-1.5 px-2 font-medium">
                {t("allocation.charts.drift_label")}
              </th>
              <th className="text-right py-1.5 pl-2 font-medium">{t("allocation.charts.value")}</th>
            </tr>
          </thead>
          <tbody>
            {chartData.map((row) => (
              <tr
                key={row.name}
                title={row.isOther ? t("allocation.charts.other_tooltip") : undefined}
                className={[
                  "border-b border-border/40 transition-colors",
                  !row.isOther ? "cursor-pointer hover:bg-muted/30" : "opacity-70",
                  drillCategory === row.name ? "bg-muted/40" : "",
                ]
                  .filter(Boolean)
                  .join(" ")}
                onClick={() => {
                  if (!row.isOther) {
                    setDrillCategory(row.name === drillCategory ? null : row.name)
                  }
                }}
              >
                <td className="py-1.5 pr-2">
                  <span className="flex items-center gap-1.5">
                    <span
                      className="inline-block h-2.5 w-2.5 rounded-sm flex-shrink-0"
                      style={{ background: row.color }}
                    />
                    {row.name}
                  </span>
                </td>
                <td className="text-right py-1.5 px-2 tabular-nums">
                  {row.current_pct.toFixed(1)}%
                </td>
                <td className="text-right py-1.5 px-2 tabular-nums text-muted-foreground">
                  {row.target_pct > 0 ? `${row.target_pct.toFixed(1)}%` : "—"}
                </td>
                <td
                  className="text-right py-1.5 px-2 tabular-nums font-medium"
                  style={{ color: driftColor(row.drift_pct) }}
                >
                  {`${driftSign(row.drift_pct)}${row.drift_pct.toFixed(1)}%`}
                </td>
                <td className="text-right py-1.5 pl-2 tabular-nums text-muted-foreground">
                  {maskMoney(row.market_value, displayCurrency)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Drill-down holdings (used when this component manages its own drill state) */}
      {drillCategory && holdings && !onDrillChange && (
        <div className="space-y-2 pt-2">
          <Button
            variant="ghost"
            size="sm"
            className="text-xs"
            onClick={() => setDrillCategory(null)}
          >
            {t("allocation.clear_filter")}
          </Button>
          <HoldingsTable
            holdings={holdings.filter((h) => h.category === drillCategory)}
            privacyMode={privacyMode}
            displayCurrency={displayCurrency}
          />
        </div>
      )}
    </div>
  )
}
