import { useState } from "react"
import { useTranslation } from "react-i18next"
import {
  Bar,
  BarChart,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { CURRENCY_TO_REGION, GEOGRAPHIC_COLOR_MAP, GEOGRAPHIC_LABELS } from "@/lib/constants"
import { useRechartsTheme } from "@/hooks/useRechartsTheme"
import { maskMoney } from "@/hooks/usePrivacyMode"
import { Button } from "@/components/ui/button"
import { HoldingsTable } from "../holdings/HoldingsTable"
import type { HoldingDetail } from "@/api/types/allocation"

interface Props {
  data: Record<string, number>
  holdings?: HoldingDetail[]
  privacyMode?: boolean
  displayCurrency?: string
  drillValue?: string | null
  onDrillChange?: (value: string | null) => void
}

function holdingRegion(h: HoldingDetail): string {
  return CURRENCY_TO_REGION[h.currency] ?? "Other"
}

export function GeographicAllocation({ data, holdings, privacyMode = false, displayCurrency, drillValue, onDrillChange }: Props) {
  const { t } = useTranslation()
  const theme = useRechartsTheme()
  const [localDrill, setLocalDrill] = useState<string | null>(null)
  const drillRegion = onDrillChange ? (drillValue ?? null) : localDrill
  const setDrillRegion = onDrillChange ?? setLocalDrill

  const total = Object.values(data).reduce((a, b) => a + b, 0)
  if (total === 0) return null

  const chartData = Object.entries(data)
    .map(([region, value]) => ({
      region,
      label: t(GEOGRAPHIC_LABELS[region] ?? `allocation.geo.${region.toLowerCase()}`),
      value,
      pct: ((value / total) * 100).toFixed(1),
    }))
    .sort((a, b) => b.value - a.value)

  const height = Math.max(120, chartData.length * 36 + 20)

  const filteredHoldings = drillRegion && holdings
    ? holdings.filter((h) => holdingRegion(h) === drillRegion)
    : []

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold">{t("allocation.geo.title")}</h3>
      <ResponsiveContainer width="100%" height={height}>
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 4, right: 60, left: 8, bottom: 4 }}
          role="img"
          aria-label={t("allocation.geo.title")}
        >
          <XAxis type="number" hide />
          <YAxis
            type="category"
            dataKey="label"
            width={70}
            tick={{ fontSize: 11, fill: theme.tickColor }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            contentStyle={theme.tooltipStyle}
            formatter={(v: number | undefined, _name: unknown, props: { payload?: { label?: string } }) => [
              v != null ? maskMoney(v, displayCurrency ?? "USD") : "",
              props.payload?.label ?? "",
            ]}
            labelStyle={{ color: theme.tooltipText }}
            cursor={{ fill: "rgba(128,128,128,0.08)" }}
          />
          <Bar
            dataKey="value"
            radius={[0, 4, 4, 0]}
            cursor="pointer"
            onClick={(_data: unknown, index: number) => {
              const entry = chartData[index]
              if (entry) setDrillRegion(entry.region === drillRegion ? null : entry.region)
            }}
          >
            {chartData.map((entry) => (
              <Cell
                key={entry.region}
                fill={GEOGRAPHIC_COLOR_MAP[entry.region] ?? "#9CA3AF"}
                opacity={drillRegion && drillRegion !== entry.region ? 0.4 : 1}
              />
            ))}
            <LabelList
              dataKey="pct"
              position="right"
              formatter={(v: unknown) => `${v}%`}
              style={{ fontSize: 10, fill: theme.tickColor }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {drillRegion && holdings && !onDrillChange && (
        <div className="space-y-2 pt-2">
          <Button
            variant="ghost"
            size="sm"
            className="text-xs"
            onClick={() => setDrillRegion(null)}
          >
            {t("allocation.clear_filter")}
          </Button>
          <HoldingsTable
            holdings={filteredHoldings}
            privacyMode={privacyMode}
            displayCurrency={displayCurrency}
          />
        </div>
      )}
    </div>
  )
}
