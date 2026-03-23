import { useTranslation } from "react-i18next"
import { useNavigate } from "react-router-dom"
import { useTerminology } from "@/hooks/useTerminology"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { useIsPrivate, maskMoney } from "@/hooks/usePrivacyMode"
import { CATEGORY_ICON_SHORT } from "@/lib/constants"
import { FINANCE_TEXT } from "@/lib/colors"
import { getDisplayName } from "@/lib/stock-display"
import type { RebalanceResponse, HoldingDetail } from "@/api/types/dashboard"

const TOP_LIMIT = 10

interface Props {
  rebalance?: RebalanceResponse | null
}

function aggregateHoldingsByTicker(holdings: HoldingDetail[]): HoldingDetail[] {
  const byTicker = new Map<
    string,
    {
      holding: HoldingDetail
      changeWeightedSum: number
      changeWeight: number
    }
  >()

  for (const holding of holdings) {
    const key = holding.ticker.toUpperCase()
    const existing = byTicker.get(key)
    const weight = Math.max(holding.market_value ?? 0, 0)
    const changeWeighted = holding.change_pct != null ? holding.change_pct * weight : 0
    const changeWeight = holding.change_pct != null ? weight : 0

    if (!existing) {
      byTicker.set(key, {
        holding: { ...holding },
        changeWeightedSum: changeWeighted,
        changeWeight,
      })
      continue
    }

    existing.holding.quantity += holding.quantity
    existing.holding.market_value += holding.market_value
    existing.holding.weight_pct += holding.weight_pct
    if (holding.cost_total != null) {
      existing.holding.cost_total = (existing.holding.cost_total ?? 0) + holding.cost_total
    }
    existing.changeWeightedSum += changeWeighted
    existing.changeWeight += changeWeight
  }

  return Array.from(byTicker.values()).map((item) => {
    const merged = { ...item.holding }
    if (item.changeWeight > 0) {
      merged.change_pct = item.changeWeightedSum / item.changeWeight
    } else {
      merged.change_pct = null
    }
    return merged
  })
}

function ChangeCell({
  value,
  category,
  change24hLabel,
}: {
  value?: number | null
  category: string
  change24hLabel: string
}) {
  if (value == null) return <td className="text-right px-3 py-2 text-sm">N/A</td>
  const isPos = value >= 0
  const isCrypto = category === "Crypto"
  return (
    <td
      className={`text-right px-3 py-2 text-sm font-medium ${isPos ? FINANCE_TEXT.gain : FINANCE_TEXT.loss}`}
    >
      {isPos ? "▲" : "▼"}
      {Math.abs(value).toFixed(2)}%
      {isCrypto ? (
        <span className="ml-1 text-[10px] text-muted-foreground">({change24hLabel})</span>
      ) : null}
    </td>
  )
}

function ReturnCells({
  holding,
  isPrivate,
  displayCurrency,
}: {
  holding: HoldingDetail
  isPrivate: boolean
  displayCurrency: string
}) {
  const { cost_total, market_value } = holding
  if (!cost_total || cost_total <= 0) {
    return (
      <>
        <td className="text-right px-3 py-2 text-sm text-muted-foreground">—</td>
        <td className="text-right px-3 py-2 text-sm text-muted-foreground">—</td>
      </>
    )
  }
  const gainLoss = market_value - cost_total
  const returnPct = (gainLoss / cost_total) * 100
  const isPos = returnPct >= 0
  const colorClass = isPos ? FINANCE_TEXT.gain : FINANCE_TEXT.loss
  return (
    <>
      <td className={`text-right px-3 py-2 text-sm font-medium ${colorClass}`}>
        {isPos ? "▲" : "▼"}
        {Math.abs(returnPct).toFixed(1)}%
      </td>
      <td className={`text-right px-3 py-2 text-sm ${colorClass}`}>
        {isPrivate
          ? "***"
          : `${isPos ? "+" : "-"}${maskMoney(Math.abs(gainLoss), displayCurrency, 0)}`}
      </td>
    </>
  )
}

export function TopHoldings({ rebalance }: Props) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const isPrivate = useIsPrivate()
  const { term } = useTerminology()
  const displayCurrency = rebalance?.display_currency ?? "USD"

  if (!rebalance?.holdings_detail?.length) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-sm text-muted-foreground">{t("dashboard.no_holdings_data")}</p>
          <Button
            size="sm"
            variant="outline"
            className="mt-3"
            onClick={() => navigate("/allocation")}
          >
            {t("dashboard.button_add_holdings")}
          </Button>
        </CardContent>
      </Card>
    )
  }

  const aggregated = aggregateHoldingsByTicker(rebalance.holdings_detail)
  const sorted = [...aggregated].sort((a, b) => b.weight_pct - a.weight_pct)
  const top = sorted.slice(0, TOP_LIMIT)

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">
          {t("dashboard.top_holdings_title", { limit: TOP_LIMIT })}
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="text-xs text-muted-foreground">
                <th className="text-left px-3 py-2">{t("dashboard.holdings_table.ticker")}</th>
                <th className="text-left px-3 py-2">{t("dashboard.holdings_table.category")}</th>
                <th className="text-right px-3 py-2">{t("dashboard.holdings_table.weight")}</th>
                <th className="text-right px-3 py-2">
                  {t("dashboard.holdings_table.market_value")}
                </th>
                <th className="text-right px-3 py-2">
                  {t("dashboard.holdings_table.daily_change")}
                </th>
                <th className="text-right px-3 py-2">
                  {t("dashboard.holdings_table.total_return")}
                </th>
                <th className="text-right px-3 py-2">
                  {term("unrealized_pl", t("dashboard.holdings_table.gain_loss"))}
                </th>
              </tr>
            </thead>
            <tbody>
              {top.map((h) => {
                const displayName = getDisplayName(h.name)
                return (
                  <tr key={h.ticker} className="border-t border-border/50 hover:bg-muted/30">
                    <td className="px-3 py-2">
                      {displayName ? (
                        <div className="flex flex-col leading-tight min-w-0">
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <span className="truncate font-semibold text-sm max-w-[140px] block">
                                  {displayName}
                                </span>
                              </TooltipTrigger>
                              <TooltipContent sideOffset={4} className="max-w-60 text-xs">
                                {displayName}
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                          <span className="text-[10px] text-muted-foreground">{h.ticker}</span>
                        </div>
                      ) : (
                        <span className="font-semibold">{h.ticker}</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-muted-foreground">
                      {CATEGORY_ICON_SHORT[h.category] ?? ""}{" "}
                      {t(`config.category.${h.category.toLowerCase()}`, h.category)}
                    </td>
                    <td className="text-right px-3 py-2">{h.weight_pct.toFixed(1)}%</td>
                    <td className="text-right px-3 py-2">
                      {maskMoney(h.market_value, displayCurrency)}
                    </td>
                    <ChangeCell
                      value={h.change_pct}
                      category={h.category}
                      change24hLabel={t("allocation.crypto.change_24h_short")}
                    />
                    <ReturnCells
                      holding={h}
                      isPrivate={isPrivate}
                      displayCurrency={displayCurrency}
                    />
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}
