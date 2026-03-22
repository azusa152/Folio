import { useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { ArrowUpDown, ChevronDown, ChevronUp, Info } from "lucide-react"
import { useTerminology } from "@/hooks/useTerminology"
import type { HoldingDetail } from "@/api/types/allocation"
import { formatSignedMoneyWithPrivacy } from "@/lib/format"
import { maskMoney } from "@/hooks/usePrivacyMode"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import {
  buildNonCashGroupKey,
  compareNullableNumber,
  fmtPct,
  getValueClass,
  roundTo2,
  type GroupedHolding,
  type SortDirection,
  type SortKey,
} from "./HoldingsTableUtils"
import { HoldingRow } from "./HoldingRow"

interface Props {
  holdings: HoldingDetail[]
  privacyMode: boolean
  displayCurrency?: string
  portfolioTodayChangeValue?: number | null
  portfolioTodayChangePct?: number | null
}

export function HoldingsTable({
  holdings,
  privacyMode,
  displayCurrency,
  portfolioTodayChangeValue,
  portfolioTodayChangePct,
}: Props) {
  const { t } = useTranslation()
  const { term, isSimplified } = useTerminology()
  const totalReturnTooltip = isSimplified
    ? t("allocation.col.unrealized_pl_tooltip")
    : t("allocation.col.total_return_tooltip")
  const [sort, setSort] = useState<{ key: SortKey; dir: SortDirection }>({
    key: "weight_pct",
    dir: "desc",
  })

  const groupedHoldings = useMemo<GroupedHolding[]>(() => {
    const rows: GroupedHolding[] = []
    const nonCashMap = new Map<
      string,
      {
        row: GroupedHolding
        allHaveCost: boolean
        hasAnyChangeData: boolean
        previousMarketValue: number
        purchaseFxRates: Set<number>
      }
    >()

    for (const h of holdings) {
      const accountLabel = h.account_name ?? "—"
      const isCash = h.category === "Cash"

      if (isCash) {
        rows.push({
          ...h,
          accounts: [accountLabel],
          row_key: `${h.account_id ?? "na"}-${h.ticker}`,
        })
        continue
      }

      const groupKey = buildNonCashGroupKey(h)
      const existing = nonCashMap.get(groupKey)
      if (!existing) {
        const purchaseFxRates = new Set<number>()
        if (h.purchase_fx_rate != null) purchaseFxRates.add(h.purchase_fx_rate)
        const firstRow: GroupedHolding = {
          ...h,
          account_id: null,
          account_name: accountLabel,
          accounts: [accountLabel],
          row_key: `group-${groupKey}`,
        }
        nonCashMap.set(groupKey, {
          row: firstRow,
          allHaveCost: h.cost_total != null,
          hasAnyChangeData: h.change_value != null || h.change_pct != null,
          previousMarketValue: (h.market_value ?? 0) - (h.change_value ?? 0),
          purchaseFxRates,
        })
        continue
      }

      const acc = existing.row
      const accountSet = new Set([...acc.accounts, accountLabel])
      acc.accounts = [...accountSet].sort((a, b) => a.localeCompare(b))
      acc.account_name = acc.accounts.join(", ")
      acc.quantity = (acc.quantity ?? 0) + (h.quantity ?? 0)
      acc.market_value = (acc.market_value ?? 0) + (h.market_value ?? 0)
      acc.weight_pct = (acc.weight_pct ?? 0) + (h.weight_pct ?? 0)

      if (acc.cost_total != null && h.cost_total != null) {
        acc.cost_total += h.cost_total
      } else if (acc.cost_total == null && h.cost_total != null) {
        acc.cost_total = h.cost_total
      }
      existing.allHaveCost = existing.allHaveCost && h.cost_total != null

      existing.hasAnyChangeData =
        existing.hasAnyChangeData || h.change_value != null || h.change_pct != null
      existing.previousMarketValue += (h.market_value ?? 0) - (h.change_value ?? 0)

      if (h.purchase_fx_rate != null) existing.purchaseFxRates.add(h.purchase_fx_rate)
    }

    for (const {
      row,
      allHaveCost,
      hasAnyChangeData,
      previousMarketValue,
      purchaseFxRates,
    } of nonCashMap.values()) {
      const currentMarketValue = row.market_value ?? 0
      const recomputedChangeValue = roundTo2(currentMarketValue - previousMarketValue)
      row.change_value = hasAnyChangeData ? recomputedChangeValue : null
      row.change_pct =
        hasAnyChangeData && previousMarketValue > 0
          ? roundTo2((recomputedChangeValue / previousMarketValue) * 100)
          : null

      if (allHaveCost && row.cost_total != null) {
        const gain = roundTo2(currentMarketValue - row.cost_total)
        row.total_gain_value = gain
        row.total_gain_pct = row.cost_total > 0 ? roundTo2((gain / row.cost_total) * 100) : null
      } else {
        row.cost_total = null
        row.total_gain_value = null
        row.total_gain_pct = null
      }

      if (purchaseFxRates.size > 1) {
        // Mixed purchase FX rates across accounts: hide FX-return breakdown to avoid misleading math.
        row.purchase_fx_rate = null
      }

      rows.push(row)
    }

    return rows
  }, [holdings])

  const sortedHoldings = useMemo(() => {
    const rows = [...groupedHoldings]
    rows.sort((a, b) => {
      switch (sort.key) {
        case "ticker":
          return sort.dir === "asc"
            ? a.ticker.localeCompare(b.ticker)
            : b.ticker.localeCompare(a.ticker)
        case "account_name":
          return sort.dir === "asc"
            ? (a.account_name ?? "").localeCompare(b.account_name ?? "")
            : (b.account_name ?? "").localeCompare(a.account_name ?? "")
        case "market_value":
          return compareNullableNumber(a.market_value, b.market_value, sort.dir)
        case "weight_pct":
          return compareNullableNumber(a.weight_pct, b.weight_pct, sort.dir)
        case "cost_total":
          return compareNullableNumber(a.cost_total, b.cost_total, sort.dir)
        case "change_value":
          return compareNullableNumber(a.change_value, b.change_value, sort.dir)
        case "total_gain_value":
          return compareNullableNumber(a.total_gain_value, b.total_gain_value, sort.dir)
      }
    })
    return rows
  }, [groupedHoldings, sort])

  const totals = useMemo(() => {
    let marketValue = 0
    let weight = 0
    let costTotal = 0
    let allHaveCost = true
    let todayChange = 0
    let hasTodayChange = false
    let todayCurrentKnown = 0
    let todayPreviousKnown = 0
    let totalGainValue = 0
    let hasTotalGain = false

    for (const h of groupedHoldings) {
      marketValue += h.market_value ?? 0
      weight += h.weight_pct ?? 0
      if (h.cost_total != null) {
        costTotal += h.cost_total
      } else {
        allHaveCost = false
      }
      if (h.change_value != null && h.market_value != null) {
        todayChange += h.change_value
        todayCurrentKnown += h.market_value
        todayPreviousKnown += h.market_value - h.change_value
        hasTodayChange = true
      }
      if (h.total_gain_value != null) {
        totalGainValue += h.total_gain_value
        hasTotalGain = true
      }
    }

    const todayChangePct =
      todayPreviousKnown > 0
        ? roundTo2(((todayCurrentKnown - todayPreviousKnown) / todayPreviousKnown) * 100)
        : null
    const totalGainPct =
      allHaveCost && costTotal > 0 ? roundTo2((totalGainValue / costTotal) * 100) : null

    return {
      marketValue: roundTo2(marketValue),
      weight: roundTo2(weight),
      costTotal: allHaveCost ? roundTo2(costTotal) : null,
      todayChange: hasTodayChange ? roundTo2(todayChange) : null,
      todayChangePct,
      totalGainValue: allHaveCost && hasTotalGain ? roundTo2(totalGainValue) : null,
      totalGainPct,
    }
  }, [groupedHoldings])

  const toggleSort = (key: SortKey): void => {
    setSort((current) =>
      current.key === key
        ? { key, dir: current.dir === "asc" ? "desc" : "asc" }
        : { key, dir: key === "weight_pct" ? "desc" : "asc" },
    )
  }

  const renderSortIcon = (key: SortKey) => {
    if (sort.key !== key) return <ArrowUpDown className="h-3 w-3 text-muted-foreground" />
    return sort.dir === "asc" ? (
      <ChevronUp className="h-3 w-3" />
    ) : (
      <ChevronDown className="h-3 w-3" />
    )
  }

  const getAriaSort = (key: SortKey): "ascending" | "descending" | "none" => {
    if (sort.key !== key) return "none"
    return sort.dir === "asc" ? "ascending" : "descending"
  }

  if (!groupedHoldings || groupedHoldings.length === 0) {
    return <p className="text-sm text-muted-foreground">{t("allocation.holdings.empty")}</p>
  }

  return (
    <div className="space-y-1">
      <p className="text-sm font-semibold">{t("allocation.holdings.title")}</p>
      <div className="text-xs text-muted-foreground bg-muted/50 rounded px-3 py-2 mb-2">
        {t("allocation.holdings_read_only_hint")}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-muted-foreground border-b border-border">
              <th className="text-left py-0.5 pr-2" aria-sort={getAriaSort("ticker")}>
                <button
                  type="button"
                  className="inline-flex items-center gap-1 hover:text-foreground"
                  onClick={() => toggleSort("ticker")}
                >
                  <span>{t("allocation.col.ticker")}</span>
                  {renderSortIcon("ticker")}
                </button>
              </th>
              <th className="text-left py-0.5 pr-2" aria-sort={getAriaSort("account_name")}>
                <button
                  type="button"
                  className="inline-flex items-center gap-1 hover:text-foreground"
                  onClick={() => toggleSort("account_name")}
                >
                  <span>{t("allocation.col.account")}</span>
                  {renderSortIcon("account_name")}
                </button>
              </th>
              <th className="text-left py-0.5 pr-2">{t("allocation.col.category")}</th>
              <th className="text-right py-0.5 pr-2">{t("allocation.col.qty")}</th>
              <th className="text-right py-0.5 pr-2" aria-sort={getAriaSort("market_value")}>
                <button
                  type="button"
                  className="inline-flex items-center justify-end gap-1 hover:text-foreground"
                  onClick={() => toggleSort("market_value")}
                >
                  <span>{t("allocation.col.value")}</span>
                  {renderSortIcon("market_value")}
                </button>
              </th>
              <th className="text-right py-0.5 pr-2" aria-sort={getAriaSort("weight_pct")}>
                <button
                  type="button"
                  className="inline-flex items-center justify-end gap-1 hover:text-foreground"
                  onClick={() => toggleSort("weight_pct")}
                >
                  <span>{t("allocation.col.weight_pct")}</span>
                  {renderSortIcon("weight_pct")}
                </button>
              </th>
              <th className="text-right py-0.5 pr-2" aria-sort={getAriaSort("cost_total")}>
                <button
                  type="button"
                  className="inline-flex items-center justify-end gap-1 hover:text-foreground"
                  onClick={() => toggleSort("cost_total")}
                >
                  <span>{term("cost_basis", t("allocation.col.cost_basis"))}</span>
                  {renderSortIcon("cost_total")}
                </button>
              </th>
              <th className="text-right py-0.5 pr-2" aria-sort={getAriaSort("change_value")}>
                <div className="inline-flex items-center justify-end gap-1">
                  <button
                    type="button"
                    className="inline-flex items-center justify-end gap-1 hover:text-foreground"
                    onClick={() => toggleSort("change_value")}
                  >
                    <span>{t("allocation.col.today")}</span>
                    {renderSortIcon("change_value")}
                  </button>
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Info
                          className="h-3 w-3 cursor-help text-muted-foreground"
                          aria-label={t("allocation.col.today_tooltip")}
                        />
                      </TooltipTrigger>
                      <TooltipContent>
                        <p className="max-w-[220px]">{t("allocation.col.today_tooltip")}</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>
              </th>
              <th className="text-right py-0.5" aria-sort={getAriaSort("total_gain_value")}>
                <div className="inline-flex items-center justify-end gap-1">
                  <button
                    type="button"
                    className="inline-flex items-center justify-end gap-1 hover:text-foreground"
                    onClick={() => toggleSort("total_gain_value")}
                  >
                    <span>{term("unrealized_pl", t("allocation.col.total_return"))}</span>
                    {renderSortIcon("total_gain_value")}
                  </button>
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Info
                          className="h-3 w-3 cursor-help text-muted-foreground"
                          aria-label={totalReturnTooltip}
                        />
                      </TooltipTrigger>
                      <TooltipContent>
                        <p className="max-w-[220px]">{totalReturnTooltip}</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>
              </th>
            </tr>
          </thead>
          <tbody>
            {sortedHoldings.map((h) => (
              <HoldingRow
                key={h.row_key}
                holding={h}
                privacyMode={privacyMode}
                displayCurrency={displayCurrency}
              />
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t border-border font-medium">
              <td className="py-1 pr-2">{t("allocation.holdings.total_row")}</td>
              <td className="py-1 pr-2" />
              <td className="py-1 pr-2" />
              <td className="py-1 pr-2" />
              <td className="py-1 pr-2 text-right">
                {maskMoney(totals.marketValue, displayCurrency ?? groupedHoldings[0].currency)}
              </td>
              <td className="py-1 pr-2 text-right">{`${totals.weight.toFixed(1)}%`}</td>
              <td className="py-1 pr-2 text-right">
                {totals.costTotal != null
                  ? maskMoney(totals.costTotal, displayCurrency ?? groupedHoldings[0].currency)
                  : "—"}
              </td>
              <td className="py-1 pr-2 text-right">
                <div
                  className={`font-medium ${getValueClass(portfolioTodayChangeValue ?? totals.todayChange)}`}
                >
                  {formatSignedMoneyWithPrivacy(
                    portfolioTodayChangeValue ?? totals.todayChange,
                    displayCurrency ?? groupedHoldings[0].currency,
                    privacyMode,
                  )}
                </div>
                <div className={getValueClass(portfolioTodayChangePct ?? totals.todayChangePct)}>
                  {portfolioTodayChangePct != null || totals.todayChangePct != null
                    ? `${t("allocation.col.today")}: ${fmtPct(portfolioTodayChangePct ?? totals.todayChangePct ?? 0)}`
                    : "—"}
                </div>
              </td>
              <td className="py-1 text-right">
                <div className={`font-medium ${getValueClass(totals.totalGainValue)}`}>
                  {formatSignedMoneyWithPrivacy(
                    totals.totalGainValue,
                    displayCurrency ?? groupedHoldings[0].currency,
                    privacyMode,
                  )}
                </div>
                <div className={getValueClass(totals.totalGainPct)}>
                  {totals.totalGainPct != null
                    ? `${term("unrealized_pl", t("allocation.col.total_return"))}: ${fmtPct(totals.totalGainPct)}`
                    : "—"}
                </div>
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  )
}
