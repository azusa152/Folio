import { useTranslation } from "react-i18next"
import { BriefcaseBusiness, ChevronDown, Landmark, PiggyBank, Wallet } from "lucide-react"
import { Link } from "react-router-dom"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { maskMoney } from "@/hooks/usePrivacyMode"
import { isTaxWrapperType, TAX_WRAPPER_ICONS } from "@/lib/constants"
import { FINANCE_TEXT } from "@/lib/colors"
import {
  formatCurrency,
  formatQuantity,
  formatSignedMoneyWithPrivacy,
  formatSignedPct,
  getQuantityUnitKey,
} from "@/lib/format"
import { getDisplayName } from "@/lib/stock-display"
import type { AccountRowData } from "../AccountsOverview"

function AccountTypeIcon({ accountType }: { accountType: string }) {
  if (accountType === "brokerage" || accountType === "retirement") {
    return <BriefcaseBusiness className="h-3.5 w-3.5 text-muted-foreground" />
  }
  if (accountType === "bank" || accountType === "savings") {
    return <Landmark className="h-3.5 w-3.5 text-muted-foreground" />
  }
  if (accountType === "wallet" || accountType === "cash_wallet") {
    return <Wallet className="h-3.5 w-3.5 text-muted-foreground" />
  }
  return <PiggyBank className="h-3.5 w-3.5 text-muted-foreground" />
}

function formatCashBalances(
  balances: Array<{ currency: string; balance: number }>,
  noCashLabel: string,
): string {
  if (balances.length === 0) return noCashLabel
  return balances.map((item) => formatCurrency(item.balance, item.currency)).join(" / ")
}

function categoryLabel(
  t: (key: string) => string,
  bucket: AccountRowData["categoryBreakdown"][number],
): string {
  if (bucket.category === "stocks") return t("dashboard.accounts_overview.stocks_category")
  if (bucket.category === "cash") return t("dashboard.accounts_overview.cash_category")
  if (bucket.category === "crypto") return t("dashboard.accounts_overview.crypto_category")
  if (bucket.category === "bonds") return t("dashboard.accounts_overview.bonds_category")
  if (bucket.category === "commodities")
    return t("dashboard.accounts_overview.commodities_category")
  return t("dashboard.accounts_overview.other_category")
}

interface Props {
  row: AccountRowData
  isExpanded: boolean
  onOpenChange: (isOpen: boolean) => void
  isPrivate: boolean
  displayCurrency: string
  setActiveRowId: (id: number | null) => void
}

export function AccountTableRow({
  row,
  isExpanded,
  onOpenChange,
  isPrivate,
  displayCurrency,
  setActiveRowId,
}: Props) {
  const { t } = useTranslation()

  const cashSummary = isPrivate
    ? "***"
    : formatCashBalances(row.cashBalances, t("dashboard.accounts_overview.no_cash"))
  const rowMeta = `${t("dashboard.accounts_overview.positions_count", { count: row.holdingsCount })} · ${t("dashboard.accounts_overview.cash_label")}: ${cashSummary}`
  const accountReturnPct =
    row.accountGainLoss != null && row.accountCostTotal > 0
      ? (row.accountGainLoss / row.accountCostTotal) * 100
      : null
  const showStandaloneCash = row.topHoldings.length === 0 && row.remainingCount === 0

  return (
    <Collapsible open={isExpanded} onOpenChange={onOpenChange}>
      <div
        className="rounded-md border border-border/60"
        onPointerEnter={() => setActiveRowId(row.id)}
        onPointerLeave={() => setActiveRowId(null)}
      >
        <div className="flex items-center gap-1.5 p-2">
          <CollapsibleTrigger asChild>
            <button
              type="button"
              className="flex min-w-0 flex-1 items-center gap-2 rounded-sm px-1 py-1 text-left hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              aria-label={`${row.name} ${t("dashboard.accounts_overview.toggle_details")}`}
            >
              <div className="min-w-0 flex-1">
                <div className="flex min-w-0 items-center gap-1.5">
                  <span
                    className="h-2.5 w-2.5 shrink-0 rounded-full"
                    style={{ backgroundColor: row.color }}
                    aria-hidden
                  />
                  <AccountTypeIcon accountType={row.accountType} />
                  <span className="truncate text-sm font-semibold">{row.name}</span>
                  {isTaxWrapperType(row.taxWrapper) ? (
                    <Badge variant="outline" className="hidden text-[11px] sm:inline-flex">
                      {TAX_WRAPPER_ICONS[row.taxWrapper]} {t(`wrapper.${row.taxWrapper}`)}
                    </Badge>
                  ) : null}
                  <span className="hidden truncate text-xs text-muted-foreground sm:inline">
                    {rowMeta}
                  </span>
                </div>
                <p className="mt-0.5 truncate text-xs text-muted-foreground sm:hidden">{rowMeta}</p>
              </div>

              <div className="flex shrink-0 items-center gap-2">
                <div className="text-right">
                  <p className="text-[11px] text-muted-foreground">
                    {t("dashboard.accounts_overview.total_label")}
                  </p>
                  <p className="text-sm font-semibold tabular-nums">
                    {isPrivate ? "***" : maskMoney(row.totalValue, displayCurrency)}
                  </p>
                </div>
                <ChevronDown
                  className={`h-4 w-4 shrink-0 text-muted-foreground transition-transform ${isExpanded ? "rotate-180" : ""}`}
                  aria-hidden
                />
              </div>
            </button>
          </CollapsibleTrigger>

          <div className="flex shrink-0 items-center gap-1">
            <Button asChild size="sm" variant="ghost" className="h-7 px-2 text-xs">
              <Link to={`/allocation?tab=accounts&accountId=${row.id}&action=deposit`}>
                {t("dashboard.accounts_overview.deposit")}
              </Link>
            </Button>
            <Button asChild size="sm" variant="ghost" className="h-7 px-2 text-xs">
              <Link to={`/allocation?tab=accounts&accountId=${row.id}&action=trade`}>
                {t("dashboard.accounts_overview.trade")}
              </Link>
            </Button>
          </div>
        </div>

        <CollapsibleContent className="border-t border-border/50 px-2.5 py-2">
          <p className="truncate text-xs text-muted-foreground">
            {row.broker} · {t(`config.account_type.${row.accountType}`)}
          </p>
          {row.missingFxCurrencies.length > 0 && (
            <p className="mt-1 text-[11px] text-muted-foreground">
              {t("dashboard.accounts_overview.cash_missing_fx_hint", {
                currencies: row.missingFxCurrencies.join(", "),
              })}
            </p>
          )}

          <div className="mt-2 space-y-1.5 text-xs">
            <div className="space-y-1.5 rounded-md border border-border/60 p-2">
              <p className="font-medium text-foreground">
                {t("dashboard.accounts_overview.value_breakdown_label")}
              </p>
              <ul className="space-y-1">
                {row.categoryBreakdown.map((bucket) => (
                  <li
                    key={`${row.id}-${bucket.category}-${bucket.customLabel ?? "default"}`}
                    className="space-y-1"
                  >
                    <div className="flex items-center justify-between gap-2 text-[11px]">
                      <span
                        className="truncate text-muted-foreground"
                        title={bucket.category === "other" ? bucket.customLabel : undefined}
                      >
                        {categoryLabel(t, bucket)}
                      </span>
                      <span className="shrink-0 tabular-nums text-foreground">
                        {isPrivate ? "***" : maskMoney(bucket.value, displayCurrency)}{" "}
                        <span className="text-muted-foreground">({bucket.pct.toFixed(0)}%)</span>
                      </span>
                    </div>
                    <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${Math.max(0, Math.min(bucket.pct, 100))}%`,
                          backgroundColor: row.color,
                        }}
                        aria-hidden
                      />
                    </div>
                  </li>
                ))}
              </ul>
            </div>

            {row.dailyChange != null && (
              <div className="flex items-center justify-between gap-2">
                <span className="text-muted-foreground">
                  {t("dashboard.accounts_overview.today_change")}
                </span>
                <span
                  className={`tabular-nums ${row.dailyChange >= 0 ? FINANCE_TEXT.gain : FINANCE_TEXT.loss}`}
                >
                  {formatSignedMoneyWithPrivacy(row.dailyChange, displayCurrency, isPrivate)}
                  {!isPrivate &&
                    row.dailyChangePct != null &&
                    ` (${formatSignedPct(row.dailyChangePct, 1)})`}
                </span>
              </div>
            )}
            {row.dailyChange != null && row.dailyChangePct == null && (
              <p className="text-[11px] text-muted-foreground">
                {t("dashboard.accounts_overview.today_change_estimated", {
                  coverage: Math.round(row.dailyChangeCoveragePct ?? 0),
                })}
              </p>
            )}
            {row.dailyChange == null && (
              <div className="flex items-center justify-between gap-2">
                <span className="text-muted-foreground">
                  {t("dashboard.accounts_overview.today_change")}
                </span>
                <span className="tabular-nums text-muted-foreground">
                  {t("dashboard.accounts_overview.today_change_unavailable")}
                </span>
              </div>
            )}

            {row.accountGainLoss != null && accountReturnPct != null && (
              <div className="flex items-center justify-between gap-2">
                <span className="text-muted-foreground">
                  {t("dashboard.accounts_overview.unrealized_pnl")}
                </span>
                <span
                  className={`tabular-nums ${row.accountGainLoss >= 0 ? FINANCE_TEXT.gain : FINANCE_TEXT.loss}`}
                >
                  {formatSignedMoneyWithPrivacy(row.accountGainLoss, displayCurrency, isPrivate)}
                  {!isPrivate && ` (${formatSignedPct(accountReturnPct, 1)})`}
                </span>
              </div>
            )}

            <div className="flex items-center justify-between gap-2">
              <p className="font-medium text-foreground">
                {t("dashboard.accounts_overview.top_positions_label")}
              </p>
              <Link
                to={`/allocation?tab=accounts&accountId=${row.id}`}
                className="text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
              >
                {t("dashboard.accounts_overview.view_positions")}
              </Link>
            </div>

            {row.topHoldings.length === 0 ? (
              <p className="text-muted-foreground">
                {t("dashboard.accounts_overview.no_positions")} ·{" "}
                <Link
                  to={`/allocation?tab=accounts&accountId=${row.id}&action=trade`}
                  className="underline underline-offset-2"
                >
                  {t("dashboard.accounts_overview.trade")}
                </Link>
              </p>
            ) : (
              <ul className="space-y-1">
                {row.topHoldings.map((holding) => {
                  const returnPct =
                    holding.cost_total && holding.cost_total > 0
                      ? ((holding.market_value - holding.cost_total) / holding.cost_total) * 100
                      : null
                  const quantityUnit = getQuantityUnitKey(holding.category, holding.ticker)
                  const returnClass =
                    returnPct == null
                      ? "text-muted-foreground"
                      : returnPct >= 0
                        ? FINANCE_TEXT.gain
                        : FINANCE_TEXT.loss
                  return (
                    <li
                      key={`${row.id}-${holding.ticker}`}
                      className="flex items-center justify-between gap-2"
                    >
                      <div className="min-w-0">
                        {getDisplayName(holding.name) ? (
                          <>
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <p className="truncate font-medium text-foreground">
                                    {getDisplayName(holding.name)}
                                  </p>
                                </TooltipTrigger>
                                <TooltipContent sideOffset={4} className="max-w-60 text-xs">
                                  {getDisplayName(holding.name)}
                                </TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                            <p className="truncate text-[10px] text-muted-foreground">
                              {holding.ticker}
                            </p>
                          </>
                        ) : (
                          <p className="truncate font-medium text-foreground">{holding.ticker}</p>
                        )}
                        <p className="truncate text-muted-foreground">
                          {t(quantityUnit.key, {
                            quantity: formatQuantity(holding.quantity, {
                              category: holding.category,
                              ticker: holding.ticker,
                            }),
                            ...quantityUnit.params,
                          })}
                        </p>
                      </div>
                      <div className="shrink-0 text-right">
                        <p className="tabular-nums text-foreground">
                          {isPrivate ? "***" : maskMoney(holding.market_value, displayCurrency)}
                        </p>
                        <p className={`tabular-nums ${returnClass}`}>
                          {returnPct == null ? "—" : formatSignedPct(returnPct, 1)}
                        </p>
                      </div>
                    </li>
                  )
                })}
              </ul>
            )}

            {row.remainingCount > 0 && (
              <Link
                to={`/allocation?tab=accounts&accountId=${row.id}`}
                className="inline-flex text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
              >
                {t("dashboard.accounts_overview.more_positions", { count: row.remainingCount })}
              </Link>
            )}
          </div>

          {showStandaloneCash && (
            <div className="mt-2 flex items-center justify-between gap-2 border-t border-border/50 pt-2 text-xs">
              <span className="text-muted-foreground">
                {t("dashboard.accounts_overview.cash_label")}:
              </span>
              <span className="tabular-nums text-foreground">{cashSummary}</span>
            </div>
          )}
        </CollapsibleContent>
      </div>
    </Collapsible>
  )
}
