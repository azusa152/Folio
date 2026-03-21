import { useState } from "react"
import { useTranslation } from "react-i18next"
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useWithdraw } from "@/api/hooks/useAllocation"
import type { WithdrawResponse } from "@/api/types/allocation"
import { DISPLAY_CURRENCIES, CHART_COLOR_PALETTE } from "@/lib/constants"
import { useRechartsTheme } from "@/hooks/useRechartsTheme"
import { maskMoney } from "@/hooks/usePrivacyMode"
import { FINANCE_TEXT } from "@/lib/colors"
import { getErrorMessage } from "@/lib/utils"

interface Props {
  privacyMode: boolean
}

export function SmartWithdrawal({ privacyMode }: Props) {
  const { t } = useTranslation()
  const theme = useRechartsTheme()
  const DRIFT_COLORS = CHART_COLOR_PALETTE
  const [amount, setAmount] = useState("")
  const [currency, setCurrency] = useState("USD")
  const [notify, setNotify] = useState(false)
  const [result, setResult] = useState<WithdrawResponse | null>(null)

  const withdrawMutation = useWithdraw()

  const handleCalculate = () => {
    if (!amount.trim() || isNaN(Number(amount)) || Number(amount) <= 0) return
    withdrawMutation.mutate(
      { target_amount: Number(amount), display_currency: currency, notify },
      {
        onSuccess: (data) => setResult(data),
        onError: (err: unknown) => toast.error(getErrorMessage(err) || t("common.error")),
      },
    )
  }

  return (
    <div className="space-y-4">
      <p className="text-sm font-semibold">{t("allocation.withdraw.title")}</p>

      {/* Input form */}
      <div className="space-y-3 max-w-sm">
        <div className="space-y-1">
          <label htmlFor="withdraw-amount" className="text-xs font-medium">
            {t("allocation.withdraw.amount_label")}
          </label>
          <Input
            id="withdraw-amount"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            type="number"
            placeholder="e.g. 10000"
            className="text-sm"
          />
        </div>
        <div className="space-y-1">
          <label htmlFor="withdraw-currency" className="text-xs font-medium">
            {t("allocation.withdraw.currency_label")}
          </label>
          <select
            id="withdraw-currency"
            value={currency}
            onChange={(e) => setCurrency(e.target.value)}
            className="w-full text-xs border border-border rounded px-2 py-1.5 bg-background"
          >
            {DISPLAY_CURRENCIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
        <label className="flex items-center gap-2 text-xs">
          <input
            type="checkbox"
            checked={notify}
            onChange={(e) => setNotify(e.target.checked)}
            className="rounded"
          />
          {t("allocation.withdraw.notify_label")}
        </label>
        <Button
          onClick={handleCalculate}
          disabled={withdrawMutation.isPending || !amount.trim()}
          size="sm"
        >
          {withdrawMutation.isPending
            ? t("common.loading")
            : t("allocation.withdraw.calculate_button")}
        </Button>
        {withdrawMutation.isError && (
          <p className="text-xs text-destructive">{t("common.error")}</p>
        )}
      </div>

      {/* Results */}
      {result && (
        <div className="space-y-4 mt-2">
          {/* Summary */}
          <div className="rounded-md border border-border p-3 text-sm space-y-1">
            <p className="font-semibold">{result.message}</p>
            <div className="grid grid-cols-1 gap-3 text-xs mt-2 sm:grid-cols-3">
              <div>
                <p className="text-muted-foreground">{t("allocation.withdraw.target")}</p>
                <p className="font-semibold">{maskMoney(result.target_amount, currency)}</p>
              </div>
              <div>
                <p className="text-muted-foreground">{t("allocation.withdraw.total_sell")}</p>
                <p className="font-semibold">{maskMoney(result.total_sell_value, currency)}</p>
              </div>
              {result.shortfall > 0 && (
                <div>
                  <p className="text-muted-foreground">{t("allocation.withdraw.shortfall")}</p>
                  <p className={`font-semibold ${FINANCE_TEXT.loss}`}>
                    {maskMoney(result.shortfall, currency)}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Sell recommendations table */}
          {result.recommendations.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-muted-foreground border-b border-border">
                    <th className="text-left py-0.5 pr-2">{t("allocation.col.ticker")}</th>
                    <th className="text-left py-0.5 pr-2">{t("allocation.col.category")}</th>
                    <th className="text-right py-0.5 pr-2">{t("allocation.withdraw.col_qty")}</th>
                    <th className="text-right py-0.5 pr-2">{t("allocation.withdraw.col_value")}</th>
                    <th className="text-left py-0.5">{t("allocation.withdraw.col_reason")}</th>
                  </tr>
                </thead>
                <tbody>
                  {result.recommendations.map((r) => (
                    <tr key={r.ticker} className="border-b border-border/50">
                      <td className="py-0.5 pr-2 font-medium">{r.ticker}</td>
                      <td className="py-0.5 pr-2 text-muted-foreground">{r.category}</td>
                      <td className="py-0.5 pr-2 text-right">
                        {privacyMode ? "***" : r.quantity_to_sell.toFixed(2)}
                      </td>
                      <td className="py-0.5 pr-2 text-right">
                        {maskMoney(r.sell_value, currency)}
                      </td>
                      <td className="py-0.5 text-muted-foreground">{r.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Post-sell drift mini pie */}
          {Object.keys(result.post_sell_drifts).length > 0 && (
            <div>
              <p className="text-xs font-semibold mb-1">
                {t("allocation.withdraw.post_drift_title")}
              </p>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={Object.entries(result.post_sell_drifts).map(([name, v]) => ({
                      name,
                      value: v.current_pct,
                    }))}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius="30%"
                    outerRadius="70%"
                    paddingAngle={1}
                    label={({ name: n, value: v }) => `${n} ${(v as number).toFixed(1)}%`}
                    labelLine={false}
                  >
                    {Object.keys(result.post_sell_drifts).map((name, i) => (
                      <Cell key={name} fill={DRIFT_COLORS[i % DRIFT_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={theme.tooltipStyle}
                    formatter={(v: number | undefined) => [`${v != null ? v.toFixed(1) : ""}%`]}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
