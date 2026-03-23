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
import { formatSignedPct } from "@/lib/format"
import { useRechartsTheme } from "@/hooks/useRechartsTheme"
import type { AttributionRow } from "./portfolioImpactUtils"
import { formatAmount } from "./portfolioImpactUtils"

interface FxMovement {
  pair: string
  impact_home_value?: number | null
  change_pct?: number | null
}

interface ImpactMovementsPanelProps {
  topMovements: FxMovement[]
  attributionRows: AttributionRow[]
  homeCurrency: string
  privacyMode: boolean
}

export function ImpactMovementsPanel({
  topMovements,
  attributionRows,
  homeCurrency,
  privacyMode,
}: ImpactMovementsPanelProps) {
  const { t } = useTranslation()
  const theme = useRechartsTheme()

  return (
    <div className="space-y-2 rounded-md border border-border p-3">
      <p className="text-xs font-medium text-muted-foreground">
        {t("fx_watch.overview.top_movements")}
      </p>
      {privacyMode ? (
        <div className="h-[220px] rounded border border-border flex items-center justify-center text-xs text-muted-foreground">
          ***
        </div>
      ) : topMovements.length > 0 ? (
        <div role="img" aria-label={t("fx_watch.overview.top_movements")}>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart
              data={topMovements}
              layout="vertical"
              margin={{ top: 8, right: 72, left: 0, bottom: 8 }}
            >
              <XAxis type="number" hide />
              <YAxis
                type="category"
                dataKey="pair"
                width={80}
                tick={{ fontSize: 11, fill: theme.tickColor }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                contentStyle={theme.tooltipStyle}
                formatter={(v: number | undefined) => [
                  `${v != null ? formatAmount(v, homeCurrency, true) : ""}`,
                  t("fx_watch.overview.net_impact_title"),
                ]}
                labelFormatter={(label) => String(label)}
              />
              <Bar dataKey="impact_home_value" radius={[0, 4, 4, 0]}>
                {topMovements.map((item) => (
                  <Cell
                    key={item.pair}
                    fill={(item.impact_home_value ?? 0) >= 0 ? "#16a34a" : "#dc2626"}
                    fillOpacity={0.9}
                  />
                ))}
                <LabelList
                  dataKey="impact_home_value"
                  position="right"
                  formatter={(v: unknown) => {
                    const numeric = typeof v === "number" ? v : Number(v)
                    return Number.isFinite(numeric) ? formatAmount(numeric, homeCurrency, true) : ""
                  }}
                  style={{ fontSize: 10, fill: theme.tickColor }}
                />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <p className="text-xs text-muted-foreground">{t("allocation.fx.empty_movements")}</p>
      )}
      {!privacyMode && attributionRows.length > 0 ? (
        <div className="space-y-1 pt-1">
          <p className="text-xs font-medium text-muted-foreground">
            {t("fx_watch.overview.impact_attribution_title")}
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-muted-foreground">
                  <th className="py-1 text-left font-medium">{t("fx_watch.overview.col_pair")}</th>
                  <th className="py-1 text-right font-medium">
                    {t("fx_watch.overview.col_holdings_value")}
                  </th>
                  <th className="py-1 text-right font-medium">
                    {t("fx_watch.overview.col_rate_change")}
                  </th>
                  <th className="py-1 text-right font-medium">
                    {t("fx_watch.overview.col_cash_impact")}
                  </th>
                  <th className="py-1 text-right font-medium">
                    {t("fx_watch.overview.col_investment_impact")}
                  </th>
                  <th className="py-1 text-right font-medium">
                    {t("fx_watch.overview.col_impact")}
                  </th>
                </tr>
              </thead>
              <tbody>
                {attributionRows.map((row) => (
                  <tr key={row.pair} className="border-t border-border/60">
                    <td className="py-1">{row.pair}</td>
                    <td className="py-1 text-right">
                      {formatAmount(row.holdingsValue, homeCurrency, false)}
                    </td>
                    <td className="py-1 text-right">{formatSignedPct(row.rateChangePct, 2)}</td>
                    <td className="py-1 text-right">
                      {formatAmount(
                        row.cashImpactHomeValue,
                        homeCurrency,
                        row.cashImpactHomeValue !== 0,
                      )}
                    </td>
                    <td className="py-1 text-right">
                      {formatAmount(
                        row.investmentImpactHomeValue,
                        homeCurrency,
                        row.investmentImpactHomeValue !== 0,
                      )}
                    </td>
                    <td className="py-1 text-right">
                      {formatAmount(row.impactHomeValue, homeCurrency, row.impactHomeValue !== 0)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
    </div>
  )
}
