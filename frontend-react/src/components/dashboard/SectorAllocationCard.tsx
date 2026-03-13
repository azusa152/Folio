import { useTranslation } from "react-i18next"
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts"
import type { SectorExposureItem } from "@/api/types/allocation"
import { CHART_COLOR_PALETTE } from "@/lib/constants"
import { useRechartsTheme } from "@/hooks/useRechartsTheme"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface Props {
  sectorExposure: SectorExposureItem[]
}

const MAX_SECTORS = 8
const COLORS = [...CHART_COLOR_PALETTE, "#14b8a6", "#f43f5e", "#6366f1"]

function localizeSector(sector: string, t: (key: string) => string): string {
  if (sector === "ETF") return t("allocation.sector.etf_unresolved")
  if (sector === "Unknown") return t("allocation.sector.unknown")
  return sector
}

export function SectorAllocationCard({ sectorExposure }: Props) {
  const { t } = useTranslation()
  const theme = useRechartsTheme()

  if (!sectorExposure || sectorExposure.length === 0) return null

  const sorted = [...sectorExposure].sort((a, b) => b.value - a.value)
  const top = sorted.slice(0, MAX_SECTORS)
  const rest = sorted.slice(MAX_SECTORS)

  const chartData = top.map((s) => ({
    name: localizeSector(s.sector, t),
    value: s.value,
    pct: s.equity_pct,
  }))

  if (rest.length > 0) {
    const otherValue = rest.reduce((sum, s) => sum + s.value, 0)
    const otherPct = rest.reduce((sum, s) => sum + s.equity_pct, 0)
    chartData.push({ name: t("allocation.sector_standalone.other"), value: otherValue, pct: otherPct })
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-semibold">
          {t("allocation.sector_standalone.title")}
        </CardTitle>
      </CardHeader>
      <CardContent className="pb-4">
        <ResponsiveContainer width="100%" height={200}>
          <PieChart role="img" aria-label={t("allocation.sector_standalone.title")}>
            <Pie
              data={chartData}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius={40}
              outerRadius={75}
              paddingAngle={1}
            >
              {chartData.map((entry, i) => (
                <Cell key={entry.name} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={theme.tooltipStyle}
              formatter={(_v: number | undefined, _name: unknown, props: { payload?: { pct?: number; name?: string } }) => [
                `${typeof props.payload?.pct === "number" ? props.payload.pct.toFixed(1) : ""}%`,
                props.payload?.name ?? "",
              ]}
            />
          </PieChart>
        </ResponsiveContainer>

        <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs mt-2">
          {chartData.map((entry, i) => (
            <span key={entry.name} className="flex items-center gap-1">
              <span
                className="inline-block h-2 w-2 rounded-full"
                style={{ background: COLORS[i % COLORS.length] }}
              />
              {entry.name} ({entry.pct.toFixed(1)}%)
            </span>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
