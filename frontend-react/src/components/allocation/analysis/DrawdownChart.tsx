import { useId } from "react"
import { useTranslation } from "react-i18next"
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { Skeleton } from "@/components/ui/skeleton"
import { useRechartsTheme } from "@/hooks/useRechartsTheme"
import type { DrawdownPoint } from "@/api/hooks/useAnalytics"

interface Props {
  data: DrawdownPoint[]
  isLoading?: boolean
}

export function DrawdownChart({ data, isLoading }: Props) {
  const { t } = useTranslation()
  const theme = useRechartsTheme()
  const gradientId = useId()

  if (isLoading) {
    return <Skeleton className="h-[220px] w-full" />
  }

  if (!data.length) return null

  return (
    <div className="space-y-2" role="img" aria-label={t("accessibility.chart_drawdown")}>
      <p className="text-sm font-semibold">{t("analytics.drawdown_title")}</p>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10, fill: theme.tickColor }}
            tickFormatter={(d: string) => d.slice(5)}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 10, fill: theme.tickColor }}
            tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
            domain={["dataMin", 0]}
            axisLine={false}
            tickLine={false}
            width={48}
          />
          <Tooltip
            contentStyle={theme.tooltipStyle}
            labelStyle={{ color: theme.tooltipText }}
            cursor={{ fill: "rgba(128,128,128,0.08)" }}
            formatter={(v: number | undefined) => [
              v != null ? `${(v * 100).toFixed(2)}%` : "—",
              t("analytics.max_drawdown"),
            ]}
          />
          <Area
            type="monotone"
            dataKey="drawdown_pct"
            stroke="#ef4444"
            fill={`url(#${gradientId})`}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
