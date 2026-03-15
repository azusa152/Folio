import { useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import {
  Bar,
  BarChart,
  Cell,
  LabelList,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import type { CurrencyExposureResponse } from "@/api/types/allocation"
import { CHART_COLOR_PALETTE, DISPLAY_CURRENCIES } from "@/lib/constants"
import { FINANCE_BADGE, FINANCE_SURFACE, FINANCE_TEXT } from "@/lib/colors"
import { cn } from "@/lib/utils"
import { useRechartsTheme } from "@/hooks/useRechartsTheme"

interface Props {
  exposure: CurrencyExposureResponse
  privacyMode: boolean
  selectedCurrency: string
  onCurrencyChange: (currency: string) => void
  showSaveDefault?: boolean
  onSaveDefault?: () => void
  isSavingDefault?: boolean
  showResetCurrency?: boolean
  onResetCurrency?: () => void
}

interface BreakdownItem {
  name: string
  value: number
}

interface AttributionRow {
  pair: string
  holdingsValue: number
  rateChangePct: number
  impactHomeValue: number
}

const ALERT_TEXT_CLASSES: Record<string, string> = {
  daily_spike: FINANCE_TEXT.loss,
  short_term_swing: FINANCE_TEXT.warning,
  long_term_trend: "text-blue-600 dark:text-blue-400",
}

const RISK_BADGE_CLASSES: Record<string, string> = {
  low: FINANCE_BADGE.gain,
  medium: FINANCE_BADGE.warning,
  high: FINANCE_BADGE.loss,
}

function formatAmount(value: number, currency: string, signed = true): string {
  const sign = value >= 0 ? "+" : "-"
  const absValue = Math.abs(value)
  const amount = new Intl.NumberFormat(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(absValue)
  return signed ? `${sign}${amount} ${currency}` : `${amount} ${currency}`
}

function riskLabelKey(riskLevel: string): string {
  if (riskLevel === "low") return "fx_watch.overview.risk_low"
  if (riskLevel === "high") return "fx_watch.overview.risk_high"
  return "fx_watch.overview.risk_medium"
}

function periodToLabel(period: string, t: (key: string) => string): string {
  if (period === "5d") return t("fx_watch.overview.period_5d")
  if (period === "1mo") return t("fx_watch.overview.period_1mo")
  if (period === "3mo") return t("fx_watch.overview.period_3mo")
  return t("fx_watch.overview.period_recent")
}

export function PortfolioImpactSnapshot({
  exposure,
  privacyMode,
  selectedCurrency,
  onCurrencyChange,
  showSaveDefault = false,
  onSaveDefault,
  isSavingDefault = false,
  showResetCurrency = false,
  onResetCurrency,
}: Props) {
  const { t } = useTranslation()
  const theme = useRechartsTheme()
  const [showAllAdvice, setShowAllAdvice] = useState(false)

  const netImpact = useMemo(
    () => exposure.fx_movements.reduce((sum, m) => sum + (m.impact_home_value ?? 0), 0),
    [exposure.fx_movements],
  )

  const topMovements = useMemo(
    () =>
      [...(exposure.fx_movements ?? [])]
        .sort((a, b) => Math.abs(b.impact_home_value ?? 0) - Math.abs(a.impact_home_value ?? 0))
        .slice(0, 5),
    [exposure.fx_movements],
  )

  const breakdownData = useMemo<BreakdownItem[]>(() => {
    const sorted = [...(exposure.breakdown ?? [])].sort((a, b) => b.percentage - a.percentage)
    const top = sorted.slice(0, 4).map((item) => ({ name: item.currency, value: item.percentage }))
    const rest = sorted.slice(4).reduce((sum, item) => sum + item.percentage, 0)
    if (rest > 0) top.push({ name: t("fx_watch.overview.other_currencies"), value: rest })
    return top
  }, [exposure.breakdown, t])
  const attributionRows = useMemo<AttributionRow[]>(() => {
    const valueByCurrency = new Map(
      (exposure.breakdown ?? []).map((item) => [item.currency, item.value] as const),
    )
    return topMovements.map((movement) => {
      const [baseCurrency] = movement.pair.split("/")
      return {
        pair: movement.pair,
        holdingsValue: valueByCurrency.get(baseCurrency) ?? 0,
        rateChangePct: movement.change_pct ?? 0,
        impactHomeValue: movement.impact_home_value ?? 0,
      }
    })
  }, [exposure.breakdown, topMovements])
  const movementPeriodLabel = periodToLabel(exposure.fx_movement_period || "5d", t)
  const calculatedAtLabel = exposure.calculated_at
    ? new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(new Date(exposure.calculated_at))
    : ""

  const netImpactSummaryKey =
    netImpact > 0
      ? "fx_watch.overview.net_impact_positive"
      : netImpact < 0
        ? "fx_watch.overview.net_impact_negative"
        : "fx_watch.overview.net_impact_neutral"

  const isPositiveImpact = netImpact > 0
  const isNegativeImpact = netImpact < 0
  const isNeutralImpact = !isPositiveImpact && !isNegativeImpact
  const netImpactClass = isPositiveImpact
    ? FINANCE_TEXT.gain
    : isNegativeImpact
      ? FINANCE_TEXT.loss
      : FINANCE_TEXT.neutral
  const netImpactSurfaceClass = isPositiveImpact
    ? FINANCE_SURFACE.gain
    : isNegativeImpact
      ? FINANCE_SURFACE.loss
      : "border-border bg-muted/30"
  const adviceRows = showAllAdvice ? exposure.advice : exposure.advice.slice(0, 2)
  const showAdviceToggle = exposure.advice.length > 2

  return (
    <section className="rounded-md border border-border p-3 space-y-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm font-semibold">{t("fx_watch.overview.portfolio_impact")}</p>
        <div className="flex items-center gap-2">
          <label htmlFor="fx-impact-currency" className="text-xs text-muted-foreground">
            {t("fx_watch.overview.display_currency")}
          </label>
          <select
            id="fx-impact-currency"
            value={selectedCurrency}
            onChange={(e) => onCurrencyChange(e.target.value)}
            className="h-7 rounded border border-border bg-background px-2 text-xs"
          >
            {DISPLAY_CURRENCIES.map((currency) => (
              <option key={currency} value={currency}>
                {currency}
              </option>
            ))}
          </select>
          {showSaveDefault && onSaveDefault ? (
            <button
              type="button"
              className="text-xs text-primary hover:underline disabled:opacity-60"
              onClick={onSaveDefault}
              disabled={isSavingDefault}
            >
              {t("fx_watch.overview.save_as_default")}
            </button>
          ) : null}
          {showResetCurrency && onResetCurrency ? (
            <button
              type="button"
              className="text-xs text-muted-foreground hover:text-foreground hover:underline"
              onClick={onResetCurrency}
            >
              {t("fx_watch.overview.reset_to_default")}
            </button>
          ) : null}
        </div>
      </div>
      <p className="text-xs text-muted-foreground">{t("fx_watch.overview.currency_scope_hint")}</p>

      <div className={cn("rounded-md border px-3 py-2", netImpactSurfaceClass)}>
        <p className="text-xs text-muted-foreground">{t("fx_watch.overview.net_impact_title")}</p>
        <p className={cn("mt-1 text-2xl font-bold", netImpactClass)}>
          {privacyMode ? "***" : formatAmount(netImpact, exposure.home_currency, !isNeutralImpact)}
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          {privacyMode
            ? t("fx_watch.overview.privacy_hidden")
            : t(netImpactSummaryKey, {
                amount: Math.abs(netImpact).toFixed(2),
                currency: exposure.home_currency,
              })}
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          {t("fx_watch.overview.impact_period", { period: movementPeriodLabel })}
        </p>
        {calculatedAtLabel ? (
          <p className="mt-1 text-xs text-muted-foreground">
            {t("fx_watch.overview.calculated_at_label", { time: calculatedAtLabel })}
          </p>
        ) : null}
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="space-y-2 rounded-md border border-border p-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-muted-foreground">{t("fx_watch.overview.risk_title")}</span>
            <span
              className={cn(
                "inline-flex rounded-full px-2 py-0.5 text-xs font-medium",
                RISK_BADGE_CLASSES[exposure.risk_level] ?? FINANCE_BADGE.warning,
              )}
            >
              {t(riskLabelKey(exposure.risk_level))}
            </span>
          </div>
          <p className="text-xs text-muted-foreground">
            {privacyMode
              ? t("fx_watch.overview.privacy_hidden")
              : t("fx_watch.overview.foreign_exposure", { pct: exposure.non_home_pct.toFixed(1) })}
          </p>
          <p className="text-xs text-muted-foreground">
            {privacyMode
              ? t("fx_watch.overview.privacy_hidden")
              : t("fx_watch.overview.cash_non_home", { pct: exposure.cash_non_home_pct.toFixed(1) })}
          </p>
        </div>

        <div className="space-y-2 rounded-md border border-border p-3">
          <p className="text-xs font-medium text-muted-foreground">{t("fx_watch.overview.currency_breakdown")}</p>
          {privacyMode ? (
            <div className="h-[180px] rounded border border-border flex items-center justify-center text-xs text-muted-foreground">
              ***
            </div>
          ) : (
            <div role="img" aria-label={t("fx_watch.overview.currency_breakdown")}>
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie
                    data={breakdownData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius="45%"
                    outerRadius="75%"
                    paddingAngle={2}
                    label={({ name: n, value: v }) => `${n} ${(v as number).toFixed(1)}%`}
                    labelLine={false}
                  >
                    {breakdownData.map((item, index) => (
                      <Cell key={item.name} fill={CHART_COLOR_PALETTE[index % CHART_COLOR_PALETTE.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={theme.tooltipStyle}
                    formatter={(v: number | undefined, _name: unknown, props: { payload?: { name?: string } }) => [
                      `${v != null ? v.toFixed(1) : ""}%`,
                      props.payload?.name ?? "",
                    ]}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>

      <div className="space-y-2 rounded-md border border-border p-3">
        <p className="text-xs font-medium text-muted-foreground">{t("fx_watch.overview.top_movements")}</p>
        {privacyMode ? (
          <div className="h-[220px] rounded border border-border flex items-center justify-center text-xs text-muted-foreground">
            ***
          </div>
        ) : topMovements.length > 0 ? (
          <div role="img" aria-label={t("fx_watch.overview.top_movements")}>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={topMovements} layout="vertical" margin={{ top: 8, right: 72, left: 0, bottom: 8 }}>
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
                    `${v != null ? formatAmount(v, exposure.home_currency, true) : ""}`,
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
                      return Number.isFinite(numeric) ? formatAmount(numeric, exposure.home_currency, true) : ""
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
            <p className="text-xs font-medium text-muted-foreground">{t("fx_watch.overview.impact_attribution_title")}</p>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-muted-foreground">
                    <th className="py-1 text-left font-medium">{t("fx_watch.overview.col_pair")}</th>
                    <th className="py-1 text-right font-medium">{t("fx_watch.overview.col_holdings_value")}</th>
                    <th className="py-1 text-right font-medium">{t("fx_watch.overview.col_rate_change")}</th>
                    <th className="py-1 text-right font-medium">{t("fx_watch.overview.col_impact")}</th>
                  </tr>
                </thead>
                <tbody>
                  {attributionRows.map((row) => (
                    <tr key={row.pair} className="border-t border-border/60">
                      <td className="py-1">{row.pair}</td>
                      <td className="py-1 text-right">
                        {privacyMode ? "***" : formatAmount(row.holdingsValue, exposure.home_currency, false)}
                      </td>
                      <td className="py-1 text-right">
                        {privacyMode ? "***" : `${row.rateChangePct >= 0 ? "+" : ""}${row.rateChangePct.toFixed(2)}%`}
                      </td>
                      <td className="py-1 text-right">
                        {privacyMode
                          ? "***"
                          : formatAmount(row.impactHomeValue, exposure.home_currency, row.impactHomeValue !== 0)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : null}
      </div>

      {exposure.advice.length > 0 && (
        <div className="space-y-2 rounded-md border border-border p-3">
          <p className="text-xs font-medium text-muted-foreground">{t("fx_watch.overview.advice_title")}</p>
          <ul className="space-y-1">
            {adviceRows.map((line) => (
              <li key={line} className="text-xs text-muted-foreground">
                • {line}
              </li>
            ))}
          </ul>
          {showAdviceToggle && (
            <button
              type="button"
              className="text-xs text-primary hover:underline"
              onClick={() => setShowAllAdvice((prev) => !prev)}
            >
              {showAllAdvice ? t("common.show_less") : t("fx_watch.overview.advice_show_more")}
            </button>
          )}
        </div>
      )}

      {exposure.fx_rate_alerts.length > 0 && (
        <div className="space-y-2 rounded-md border border-border p-3">
          <p className="text-xs font-medium text-muted-foreground">{t("fx_watch.overview.active_alerts")}</p>
          <div className="flex flex-wrap gap-2">
            {exposure.fx_rate_alerts.map((alert) => (
              <span
                key={`${alert.pair}-${alert.period_label}-${alert.alert_type}`}
                className={cn(
                  "inline-flex items-center gap-1 rounded-full border border-border px-2 py-0.5 text-xs",
                  ALERT_TEXT_CLASSES[alert.alert_type] ?? FINANCE_TEXT.neutral,
                )}
              >
                <span className="font-semibold">{alert.pair}</span>
                <span>{alert.period_label}</span>
                <span>{privacyMode ? "***" : `${alert.change_pct >= 0 ? "+" : ""}${alert.change_pct.toFixed(2)}%`}</span>
              </span>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}
