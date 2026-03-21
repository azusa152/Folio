import { useTranslation } from "react-i18next"
import { formatShares } from "./formatters"
import { FINANCE_TEXT } from "@/lib/colors"
import type { QoQResponse } from "@/api/types/smartMoney"

const TREND_ICON: Record<string, string> = {
  increasing: "↑",
  decreasing: "↓",
  new: "★",
  exited: "✕",
  stable: "–",
}

const TREND_COLOR: Record<string, string> = {
  increasing: FINANCE_TEXT.gain,
  decreasing: FINANCE_TEXT.loss,
  new: "text-blue-600 dark:text-blue-400",
  exited: FINANCE_TEXT.neutral,
  stable: FINANCE_TEXT.neutral,
}

function TrendIndicator({ trend }: { trend: string }) {
  return (
    <span className={`text-xs font-bold ${TREND_COLOR[trend] ?? ""}`}>
      {TREND_ICON[trend] ?? "–"}
    </span>
  )
}

export function QoQTable({ data }: { data: QoQResponse }) {
  const { t } = useTranslation()

  if (!data.items.length) {
    return <p className="text-sm text-muted-foreground">{t("smart_money.qoq.no_data")}</p>
  }

  const quarterHeaders = data.items[0]?.quarters.map((q) => q.report_date) ?? []

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="text-muted-foreground border-b border-border">
            <th className="text-left py-1 pr-2">{t("smart_money.col.ticker")}</th>
            <th className="text-left py-1 pr-2">{t("smart_money.col.company")}</th>
            {quarterHeaders.map((qd) => (
              <th key={qd} className="text-right py-1 pr-2 whitespace-nowrap">
                {qd}
              </th>
            ))}
            <th className="text-center py-1">{t("smart_money.qoq.trend")}</th>
          </tr>
        </thead>
        <tbody>
          {data.items.map((item) => (
            <tr key={item.ticker} className="border-b border-border/50">
              <td className="py-0.5 pr-2 font-medium">{item.ticker ?? "—"}</td>
              <td className="py-0.5 pr-2 text-muted-foreground max-w-[120px] truncate">
                {item.company_name}
              </td>
              {quarterHeaders.map((qd) => {
                const quarter = item.quarters.find((qq) => qq.report_date === qd)
                return quarter ? (
                  <td key={qd} className="py-0.5 pr-2 text-right whitespace-nowrap">
                    <div>{formatShares(quarter.shares)}</div>
                    {quarter.weight_pct != null && (
                      <div className="text-muted-foreground">{quarter.weight_pct.toFixed(1)}%</div>
                    )}
                  </td>
                ) : (
                  <td key={qd} className="py-0.5 pr-2" />
                )
              })}
              <td className="py-0.5 text-center">
                <TrendIndicator trend={item.trend} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
