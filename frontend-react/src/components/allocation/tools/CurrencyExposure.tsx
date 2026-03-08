import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useCurrencyExposure, useFxExposureAlert, useUpdateProfile } from "@/api/hooks/useAllocation"
import type { ProfileResponse } from "@/api/types/allocation"
import { DISPLAY_CURRENCIES, CHART_COLOR_PALETTE } from "@/lib/constants"
import { FINANCE_TEXT } from "@/lib/colors"
import { cn } from "@/lib/utils"
import { useRechartsTheme } from "@/hooks/useRechartsTheme"

interface Props {
  privacyMode: boolean
  profile: ProfileResponse
  enabled: boolean
}

const ALERT_TEXT_CLASSES: Record<string, string> = {
  daily_spike: FINANCE_TEXT.loss,
  short_term_swing: FINANCE_TEXT.warning,
  long_term_trend: "text-blue-600 dark:text-blue-400",
}

export function CurrencyExposure({ privacyMode, profile, enabled }: Props) {
  const { t } = useTranslation()
  const theme = useRechartsTheme()
  const { data, isLoading } = useCurrencyExposure(enabled)
  const alertMutation = useFxExposureAlert()
  const updateProfileMutation = useUpdateProfile()

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-6 w-40" />
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Skeleton className="h-52 rounded-lg" />
          <Skeleton className="h-52 rounded-lg" />
        </div>
        <Skeleton className="h-20 w-full" />
      </div>
    )
  }

  if (!data) {
    return <p className="text-sm text-muted-foreground">{t("common.error")}</p>
  }

  const cashData = data.cash_breakdown.map((b) => ({ name: b.currency, value: b.percentage }))
  const totalData = data.breakdown.map((b) => ({ name: b.currency, value: b.percentage }))

  const CURRENCY_COLORS = CHART_COLOR_PALETTE
  const tooltipStyle = theme.tooltipStyle

  return (
    <div className="space-y-4">
      {/* Home currency selector */}
      <div className="flex items-center gap-3">
        <span className="text-sm font-semibold">{t("allocation.fx.title")}</span>
        <div className="flex items-center gap-2 ml-auto">
          <label htmlFor="fx-home-currency" className="text-xs text-muted-foreground">{t("allocation.fx.home_currency")}</label>
          <select
            id="fx-home-currency"
            defaultValue={profile.home_currency}
            onChange={(e) => updateProfileMutation.mutate(
            { id: profile.id, payload: { home_currency: e.target.value } },
            {
              onSuccess: () => toast.success(t("common.success")),
              onError: () => toast.error(t("common.error_backend")),
            },
          )}
            className="text-xs border border-border rounded px-2 py-1 bg-background"
          >
            {DISPLAY_CURRENCIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
      </div>

      {/* Donut charts */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div>
          <p className="text-xs text-center text-muted-foreground mb-1">{t("allocation.fx.cash_chart")}</p>
          {!privacyMode ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={cashData} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius="40%" outerRadius="70%" paddingAngle={1}
                  label={({ name: n, value: v }) => `${n} ${(v as number).toFixed(1)}%`} labelLine={false}>
                  {cashData.map((entry, i) => <Cell key={entry.name} fill={CURRENCY_COLORS[i % CURRENCY_COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={tooltipStyle} formatter={(v: number | undefined) => [`${v != null ? v.toFixed(1) : ""}%`]} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-52 flex items-center justify-center border border-border rounded text-xs text-muted-foreground">
              ***
            </div>
          )}
        </div>
        <div>
          <p className="text-xs text-center text-muted-foreground mb-1">{t("allocation.fx.total_chart")}</p>
          {!privacyMode ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={totalData} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius="40%" outerRadius="70%" paddingAngle={1}
                  label={({ name: n, value: v }) => `${n} ${(v as number).toFixed(1)}%`} labelLine={false}>
                  {totalData.map((entry, i) => <Cell key={entry.name} fill={CURRENCY_COLORS[i % CURRENCY_COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={tooltipStyle} formatter={(v: number | undefined) => [`${v != null ? v.toFixed(1) : ""}%`]} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-52 flex items-center justify-center border border-border rounded text-xs text-muted-foreground">
              ***
            </div>
          )}
        </div>
      </div>

      {/* FX Movements */}
      {data.fx_movements.length > 0 && (
        <section className="space-y-1">
          <p className="text-sm font-semibold">{t("allocation.fx.movements_title")}</p>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-muted-foreground border-b border-border">
                  <th className="text-left py-0.5 pr-3">{t("allocation.fx.col_pair")}</th>
                  <th className="text-right py-0.5 pr-3">{t("allocation.fx.col_rate")}</th>
                  <th className="text-right py-0.5">{t("allocation.fx.col_change")}</th>
                </tr>
              </thead>
              <tbody>
                {data.fx_movements.map((m) => (
                  <tr key={m.pair} className="border-b border-border/50">
                    <td className="py-0.5 pr-3 font-medium">{m.pair}</td>
                    <td className="py-0.5 pr-3 text-right">
                      {privacyMode ? "***" : m.current_rate.toFixed(4)}
                    </td>
                    <td
                      className={cn(
                        "py-0.5 text-right",
                        !privacyMode && (m.change_pct >= 0 ? FINANCE_TEXT.gain : FINANCE_TEXT.loss),
                      )}
                    >
                      {privacyMode ? "***" : `${m.change_pct >= 0 ? "+" : ""}${m.change_pct.toFixed(2)}% ${m.direction === "up" ? "📈" : "📉"}`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Rate Alerts */}
      {data.fx_rate_alerts.length > 0 && (
        <section className="space-y-1">
          <p className="text-sm font-semibold">{t("allocation.fx.alerts_title")}</p>
          <div className="space-y-1">
            {data.fx_rate_alerts.map((a) => (
              <div
                key={`${a.pair}-${a.period_label}`}
                className={cn("text-xs flex items-center gap-2", ALERT_TEXT_CLASSES[a.alert_type] ?? FINANCE_TEXT.neutral)}
              >
                <span className="font-semibold">{a.pair}</span>
                <span>{a.period_label}</span>
                <span>{privacyMode ? "***" : `${a.change_pct >= 0 ? "+" : ""}${a.change_pct.toFixed(2)}%`}</span>
                <span className="text-muted-foreground">
                  {privacyMode ? "@ ***" : `@ ${a.current_rate.toFixed(4)}`}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Advice */}
      {data.advice.length > 0 && (
        <ul className="space-y-1">
          {data.advice.map((a) => (
            <li key={a} className="text-xs text-muted-foreground">• {a}</li>
          ))}
        </ul>
      )}

      {/* Alert button */}
      <div className="flex items-center gap-2">
        <Button
          size="sm"
          variant="outline"
          className="text-xs"
          onClick={() => alertMutation.mutate(undefined, {
            onSuccess: () => toast.success(t("common.success")),
            onError: () => toast.error(t("common.error_backend")),
          })}
          disabled={alertMutation.isPending}
        >
          {alertMutation.isPending ? t("common.loading") : t("allocation.fx.alert_button")}
        </Button>
        {alertMutation.isSuccess && <span className="text-xs text-muted-foreground">{t("common.success")}</span>}
        {alertMutation.isError && <span className="text-xs text-destructive">{t("common.error")}</span>}
      </div>
    </div>
  )
}
