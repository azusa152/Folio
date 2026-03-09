import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts"
import { ASSET_CLASS_COLOR_MAP, CATEGORY_TO_ASSET_CLASS } from "@/lib/constants"
import { useRechartsTheme } from "@/hooks/useRechartsTheme"
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

function holdingAssetClass(h: HoldingDetail): string {
  return CATEGORY_TO_ASSET_CLASS[h.category] ?? "Equity"
}

export function AssetClassDonut({ data, holdings, privacyMode = false, displayCurrency, drillValue, onDrillChange }: Props) {
  const { t } = useTranslation()
  const theme = useRechartsTheme()
  const [localDrill, setLocalDrill] = useState<string | null>(null)
  const drillClass = onDrillChange ? (drillValue ?? null) : localDrill
  const setDrillClass = onDrillChange ?? setLocalDrill

  const total = Object.values(data).reduce((a, b) => a + b, 0)
  if (total === 0) return null

  const keys = Object.keys(data)
  const chartData = keys.map((cls) => ({
    key: cls,
    name: t(`allocation.asset_class.${cls.toLowerCase().replace(/ /g, "_")}`),
    value: data[cls],
    pct: ((data[cls] / total) * 100).toFixed(1),
    fill: ASSET_CLASS_COLOR_MAP[cls] ?? "#6B7280",
  }))

  const filteredHoldings = drillClass && holdings
    ? holdings.filter((h) => holdingAssetClass(h) === drillClass)
    : []

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold">{t("allocation.asset_class.title")}</h3>
      <ResponsiveContainer width="100%" height={200}>
        <PieChart>
          <Pie
            data={chartData}
            dataKey="value"
            nameKey="name"
            innerRadius={50}
            outerRadius={80}
            paddingAngle={2}
            cursor="pointer"
            onClick={(_data: unknown, index: number) => {
              const entry = chartData[index]
              if (entry) setDrillClass(entry.key === drillClass ? null : entry.key)
            }}
          >
            {chartData.map((entry) => (
              <Cell
                key={entry.key}
                fill={entry.fill}
                opacity={drillClass && drillClass !== entry.key ? 0.4 : 1}
              />
            ))}
          </Pie>
          <Tooltip
            contentStyle={theme.tooltipStyle}
            formatter={(v: number | undefined, _name: unknown, props: { payload?: { name?: string; pct?: string } }) => [
              v != null ? v.toLocaleString() : "",
              props.payload?.name ? `${props.payload.name} (${props.payload.pct ?? ""}%)` : "",
            ]}
          />
        </PieChart>
      </ResponsiveContainer>

      <div className="flex flex-wrap gap-3 text-xs">
        {chartData.map((entry) => (
          <span key={entry.key} className="flex items-center gap-1">
            <span
              className="inline-block h-2.5 w-2.5 rounded-full"
              style={{ background: entry.fill }}
            />
            {entry.name} ({entry.pct}%)
          </span>
        ))}
      </div>

      {drillClass && holdings && !onDrillChange && (
        <div className="space-y-2 pt-2">
          <Button
            variant="ghost"
            size="sm"
            className="text-xs"
            onClick={() => setDrillClass(null)}
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
