import { useTranslation } from "react-i18next"
import { useHoldings } from "@/api/hooks/useDashboard"
import { formatPrice, formatQuantity } from "@/lib/format"

interface Props {
  privacyMode: boolean
}

export function HoldingsManager({ privacyMode }: Props) {
  const { t } = useTranslation()
  const { data: holdings } = useHoldings()

  if (!holdings || holdings.length === 0) {
    return (
      <div className="space-y-1">
        <p className="text-sm font-semibold">{t("allocation.holdings.title")}</p>
        <p className="text-sm text-muted-foreground">{t("allocation.holdings.empty")}</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <p className="text-sm font-semibold">{t("allocation.holdings.title")}</p>
      <div className="text-xs text-muted-foreground bg-muted/50 rounded px-3 py-2">
        {t("allocation.holdings_read_only_hint")}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-muted-foreground border-b border-border">
              <th className="text-left py-0.5 pr-2">{t("allocation.col.ticker")}</th>
              <th className="text-left py-0.5 pr-2">{t("allocation.col.category")}</th>
              <th className="text-right py-0.5 pr-2">{t("allocation.col.qty")}</th>
              <th className="text-right py-0.5 pr-2">{t("allocation.col.cost")}</th>
              <th className="text-left py-0.5 pr-2">{t("allocation.manager.col_broker")}</th>
            </tr>
          </thead>
          <tbody>
            {holdings.map((holding) => (
              <tr key={holding.id} className="border-b border-border/50">
                <td className="py-0.5 pr-2 font-medium">{holding.ticker}</td>
                <td className="py-0.5 pr-2 text-muted-foreground">{holding.category}</td>
                <td className="py-0.5 pr-2 text-right">
                  {privacyMode
                    ? "***"
                    : formatQuantity(holding.quantity, {
                        category: holding.category,
                        ticker: holding.ticker,
                      })}
                </td>
                <td className="py-0.5 pr-2 text-right">
                  {privacyMode
                    ? "***"
                    : (holding.cost_basis != null ? formatPrice(holding.cost_basis, holding.currency) : "—")}
                </td>
                <td className="py-0.5 pr-2 text-muted-foreground">{holding.broker ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
