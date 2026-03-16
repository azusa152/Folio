import { useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { ArrowUpDown, ChevronDown, ChevronUp, Info } from "lucide-react"
import { useTerminology } from "@/hooks/useTerminology"
import type { HoldingDetail } from "@/api/types/allocation"
import { FINANCE_TEXT } from "@/lib/colors"
import { formatQuantity, getQuantityUnitKey } from "@/lib/format"
import { maskMoney } from "@/hooks/usePrivacyMode"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

interface Props {
  holdings: HoldingDetail[]
  privacyMode: boolean
  displayCurrency?: string
  portfolioTodayChangeValue?: number | null
  portfolioTodayChangePct?: number | null
}

type SortDirection = "asc" | "desc"
type SortKey =
  | "ticker"
  | "account_name"
  | "market_value"
  | "weight_pct"
  | "cost_total"
  | "change_value"
  | "total_gain_value"

function fmtPct(v: number, showSign = true): string {
  const sign = showSign && v >= 0 ? "+" : ""
  return `${sign}${v.toFixed(2)}%`
}

function getValueClass(v: number | null | undefined): string {
  if (v == null) return FINANCE_TEXT.neutral
  if (v > 0) return FINANCE_TEXT.gain
  if (v < 0) return FINANCE_TEXT.loss
  return FINANCE_TEXT.neutral
}

function formatSignedMoney(
  value: number | null | undefined,
  currency: string,
  privacyMode: boolean,
): string {
  if (value == null) return "—"
  if (privacyMode) return "***"

  const amount = maskMoney(Math.abs(value), currency)
  if (value > 0) return `+${amount}`
  if (value < 0) return `-${amount}`
  return amount
}

function compareNullableNumber(a: number | null | undefined, b: number | null | undefined, direction: SortDirection): number {
  const aNull = a == null
  const bNull = b == null
  if (aNull && bNull) return 0
  if (aNull) return 1
  if (bNull) return -1
  const diff = a - b
  return direction === "asc" ? diff : -diff
}

/** Compute FX return % given purchase and current FX rate */
function computeFxReturn(purchaseFx: number | null | undefined, currentFx: number | null | undefined): number | null {
  if (purchaseFx == null || currentFx == null || purchaseFx === 0) return null
  return (currentFx / purchaseFx - 1) * 100
}

export function HoldingsTable({
  holdings,
  privacyMode,
  displayCurrency,
  portfolioTodayChangeValue,
  portfolioTodayChangePct,
}: Props) {
  const { t } = useTranslation()
  const { term } = useTerminology()
  const [sort, setSort] = useState<{ key: SortKey; dir: SortDirection }>({
    key: "weight_pct",
    dir: "desc",
  })

  const sortedHoldings = useMemo(() => {
    const rows = [...holdings]
    rows.sort((a, b) => {
      switch (sort.key) {
        case "ticker":
          return sort.dir === "asc" ? a.ticker.localeCompare(b.ticker) : b.ticker.localeCompare(a.ticker)
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
  }, [holdings, sort])

  const totals = useMemo(() => {
    let marketValue = 0
    let weight = 0
    let costTotal = 0
    let hasCost = false
    let todayChange = 0
    let hasTodayChange = false
    let todayCurrentKnown = 0
    let todayPreviousKnown = 0
    let totalGainValue = 0
    let hasTotalGain = false

    for (const h of holdings) {
      marketValue += h.market_value ?? 0
      weight += h.weight_pct ?? 0
      if (h.cost_total != null) {
        costTotal += h.cost_total
        hasCost = true
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

    const todayChangePct = todayPreviousKnown > 0
      ? roundTo2((todayCurrentKnown - todayPreviousKnown) / todayPreviousKnown * 100)
      : null
    const totalGainPct = hasCost && costTotal > 0
      ? roundTo2((totalGainValue / costTotal) * 100)
      : null

    return {
      marketValue: roundTo2(marketValue),
      weight: roundTo2(weight),
      costTotal: hasCost ? roundTo2(costTotal) : null,
      todayChange: hasTodayChange ? roundTo2(todayChange) : null,
      todayChangePct,
      totalGainValue: hasTotalGain ? roundTo2(totalGainValue) : null,
      totalGainPct,
    }
  }, [holdings])

  const toggleSort = (key: SortKey): void => {
    setSort((current) => (
      current.key === key
        ? { key, dir: current.dir === "asc" ? "desc" : "asc" }
        : { key, dir: key === "weight_pct" ? "desc" : "asc" }
    ))
  }

  const renderSortIcon = (key: SortKey) => {
    if (sort.key !== key) return <ArrowUpDown className="h-3 w-3 text-muted-foreground" />
    return sort.dir === "asc"
      ? <ChevronUp className="h-3 w-3" />
      : <ChevronDown className="h-3 w-3" />
  }

  const getAriaSort = (key: SortKey): "ascending" | "descending" | "none" => {
    if (sort.key !== key) return "none"
    return sort.dir === "asc" ? "ascending" : "descending"
  }

  if (!holdings || holdings.length === 0) {
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
                <button type="button" className="inline-flex items-center gap-1 hover:text-foreground" onClick={() => toggleSort("ticker")}>
                  <span>{t("allocation.col.ticker")}</span>
                  {renderSortIcon("ticker")}
                </button>
              </th>
              <th className="text-left py-0.5 pr-2" aria-sort={getAriaSort("account_name")}>
                <button type="button" className="inline-flex items-center gap-1 hover:text-foreground" onClick={() => toggleSort("account_name")}>
                  <span>{t("allocation.col.account")}</span>
                  {renderSortIcon("account_name")}
                </button>
              </th>
              <th className="text-left py-0.5 pr-2">{t("allocation.col.category")}</th>
              <th className="text-right py-0.5 pr-2">{t("allocation.col.qty")}</th>
              <th className="text-right py-0.5 pr-2" aria-sort={getAriaSort("market_value")}>
                <button type="button" className="inline-flex items-center justify-end gap-1 hover:text-foreground" onClick={() => toggleSort("market_value")}>
                  <span>{t("allocation.col.value")}</span>
                  {renderSortIcon("market_value")}
                </button>
              </th>
              <th className="text-right py-0.5 pr-2" aria-sort={getAriaSort("weight_pct")}>
                <button type="button" className="inline-flex items-center justify-end gap-1 hover:text-foreground" onClick={() => toggleSort("weight_pct")}>
                  <span>{t("allocation.col.weight_pct")}</span>
                  {renderSortIcon("weight_pct")}
                </button>
              </th>
              <th className="text-right py-0.5 pr-2" aria-sort={getAriaSort("cost_total")}>
                <button type="button" className="inline-flex items-center justify-end gap-1 hover:text-foreground" onClick={() => toggleSort("cost_total")}>
                  <span>{term("cost_basis", t("allocation.col.cost_basis"))}</span>
                  {renderSortIcon("cost_total")}
                </button>
              </th>
              <th className="text-right py-0.5 pr-2" aria-sort={getAriaSort("change_value")}>
                <div className="inline-flex items-center justify-end gap-1">
                  <button type="button" className="inline-flex items-center justify-end gap-1 hover:text-foreground" onClick={() => toggleSort("change_value")}>
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
                  <button type="button" className="inline-flex items-center justify-end gap-1 hover:text-foreground" onClick={() => toggleSort("total_gain_value")}>
                    <span>{t("allocation.col.total_return")}</span>
                    {renderSortIcon("total_gain_value")}
                  </button>
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Info
                          className="h-3 w-3 cursor-help text-muted-foreground"
                          aria-label={t("allocation.col.total_return_tooltip")}
                        />
                      </TooltipTrigger>
                      <TooltipContent>
                        <p className="max-w-[220px]">{t("allocation.col.total_return_tooltip")}</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>
              </th>
            </tr>
          </thead>
          <tbody>
            {sortedHoldings.map((h) => {
              const isCrypto = h.category === "Crypto"
              const isCash = h.category === "Cash"
              const targetCurrency = displayCurrency ?? h.currency
              const currentFxRate = h.current_fx_rate
              const fxReturn = computeFxReturn(h.purchase_fx_rate, h.current_fx_rate)
              const showFxBreakdown =
                !isCash &&
                h.purchase_fx_rate != null &&
                fxReturn != null &&
                h.currency !== targetCurrency

              const showCashFxInfo =
                isCash &&
                currentFxRate != null &&
                Number.isFinite(currentFxRate) &&
                h.currency !== targetCurrency

              // Home return = local price return + FX impact (approximate additive)
              const homeReturn =
                showFxBreakdown && h.change_pct != null
                  ? h.change_pct + fxReturn
                  : null
              const quantityUnit = getQuantityUnitKey(h.category, h.ticker)
              const quantityText = t(quantityUnit.key, {
                quantity: formatQuantity(h.quantity, { category: h.category, ticker: h.ticker }),
                ...quantityUnit.params,
              })

              return (
                <tr key={`${h.account_id ?? "na"}-${h.ticker}`} className="border-b border-border/50">
                  <td className="py-0.5 pr-2 font-medium">{h.ticker}</td>
                  <td className="py-0.5 pr-2 text-muted-foreground">{h.account_name ?? "—"}</td>
                  <td className="py-0.5 pr-2 text-muted-foreground">
                    {t(`config.category.${h.category.toLowerCase()}`)}
                  </td>
                  <td className="py-0.5 pr-2 text-right">
                    {privacyMode
                      ? "***"
                      : quantityText}
                  </td>
                  <td className="py-0.5 pr-2 text-right">
                    {h.market_value == null ? "—" : maskMoney(h.market_value, displayCurrency ?? h.currency)}
                  </td>
                  <td className="py-0.5 pr-2 text-right">
                    {h.weight_pct != null ? `${h.weight_pct.toFixed(1)}%` : "—"}
                  </td>
                  <td className="py-0.5 pr-2 text-right">
                    {h.cost_total == null ? "—" : maskMoney(h.cost_total, displayCurrency ?? h.currency)}
                  </td>
                  <td className="py-0.5 pr-2 text-right">
                    {!isCash && (h.change_value != null || h.change_pct != null) ? (
                      <>
                        <div className={`font-medium ${getValueClass(h.change_value ?? h.change_pct)}`}>
                          {formatSignedMoney(h.change_value, displayCurrency ?? h.currency, privacyMode)}
                        </div>
                        <div className={getValueClass(h.change_pct)}>
                          {h.change_pct != null
                            ? `${fmtPct(h.change_pct)}${isCrypto ? ` (${t("allocation.crypto.change_24h_short")})` : ""}`
                            : "—"}
                        </div>
                      </>
                    ) : (
                      <div className={FINANCE_TEXT.neutral}>—</div>
                    )}
                    {isCrypto && h.change_pct != null && Math.abs(h.change_pct) >= 5 && (
                      <div className={`text-[10px] leading-tight mt-0.5 ${FINANCE_TEXT.warning}`}>
                        {t("allocation.crypto.volatility_warning")}
                      </div>
                    )}
                    {showCashFxInfo && (
                      <div className="text-muted-foreground text-[10px] leading-tight mt-0.5">
                        {t("allocation.col.fx_rate_info", {
                          from: h.currency,
                          rate: currentFxRate.toLocaleString(undefined, {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 6,
                          }),
                          to: targetCurrency,
                        })}
                      </div>
                    )}
                    {showFxBreakdown && (
                      <div className="text-muted-foreground text-[10px] leading-tight mt-0.5">
                        {homeReturn != null && (
                          <div className={homeReturn >= 0 ? FINANCE_TEXT.gain : FINANCE_TEXT.loss}>
                            {t("allocation.col.home_return", { pct: fmtPct(homeReturn) })}
                          </div>
                        )}
                        <div className={fxReturn >= 0 ? FINANCE_TEXT.gain : FINANCE_TEXT.loss}>
                          {t("allocation.col.fx_return", { pct: fmtPct(fxReturn) })}
                        </div>
                      </div>
                    )}
                  </td>
                  <td className="py-0.5 text-right">
                    {h.total_gain_value != null || h.total_gain_pct != null ? (
                      <>
                        <div className={`font-medium ${getValueClass(h.total_gain_value)}`}>
                          {formatSignedMoney(h.total_gain_value, displayCurrency ?? h.currency, privacyMode)}
                        </div>
                        <div className={getValueClass(h.total_gain_pct)}>
                          {h.total_gain_pct != null ? fmtPct(h.total_gain_pct) : "—"}
                        </div>
                      </>
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
          <tfoot>
            <tr className="border-t border-border font-medium">
              <td className="py-1 pr-2">{t("allocation.holdings.total_row")}</td>
              <td className="py-1 pr-2" />
              <td className="py-1 pr-2" />
              <td className="py-1 pr-2" />
              <td className="py-1 pr-2 text-right">
                {maskMoney(totals.marketValue, displayCurrency ?? holdings[0].currency)}
              </td>
              <td className="py-1 pr-2 text-right">{`${totals.weight.toFixed(1)}%`}</td>
              <td className="py-1 pr-2 text-right">
                {totals.costTotal != null ? maskMoney(totals.costTotal, displayCurrency ?? holdings[0].currency) : "—"}
              </td>
              <td className="py-1 pr-2 text-right">
                <div className={`font-medium ${getValueClass(portfolioTodayChangeValue ?? totals.todayChange)}`}>
                  {formatSignedMoney(portfolioTodayChangeValue ?? totals.todayChange, displayCurrency ?? holdings[0].currency, privacyMode)}
                </div>
                <div className={getValueClass(portfolioTodayChangePct ?? totals.todayChangePct)}>
                  {portfolioTodayChangePct != null || totals.todayChangePct != null
                    ? `${t("allocation.col.today")}: ${fmtPct(portfolioTodayChangePct ?? totals.todayChangePct ?? 0)}`
                    : "—"}
                </div>
              </td>
              <td className="py-1 text-right">
                <div className={`font-medium ${getValueClass(totals.totalGainValue)}`}>
                  {formatSignedMoney(totals.totalGainValue, displayCurrency ?? holdings[0].currency, privacyMode)}
                </div>
                <div className={getValueClass(totals.totalGainPct)}>
                  {totals.totalGainPct != null ? `${t("allocation.col.total_return")}: ${fmtPct(totals.totalGainPct)}` : "—"}
                </div>
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  )
}

function roundTo2(value: number): number {
  return Math.round(value * 100) / 100
}
