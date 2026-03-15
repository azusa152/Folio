import { useMemo, useState } from "react"
import { BriefcaseBusiness, ChevronDown, CircleHelp, Landmark, PiggyBank, Wallet } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Link } from "react-router-dom"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { useIsPrivate, maskMoney } from "@/hooks/usePrivacyMode"
import { FINANCE_TEXT } from "@/lib/colors"
import { formatCurrency } from "@/lib/format"
import type { AccountSummaryItem } from "@/api/types/account"
import type { HoldingDetail, RebalanceResponse } from "@/api/types/dashboard"

interface Props {
  accountSummary?: AccountSummaryItem[]
  rebalance?: RebalanceResponse | null
  displayCurrency: string
  isLoading?: boolean
  isError?: boolean
}

interface AccountRow {
  id: number
  name: string
  broker: string
  accountType: string
  holdingsCount: number
  cashBalances: Array<{ currency: string; balance: number }>
  missingFxCurrencies: string[]
  totalValue: number
  sharePct: number
  color: string
  topHoldings: HoldingDetail[]
  remainingCount: number
  accountGainLoss: number | null
  accountCostTotal: number
}

const ACCOUNT_COLORS = ["#2563EB", "#059669", "#D97706", "#7C3AED", "#0891B2", "#DC2626", "#EA580C", "#4F46E5"]

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
  return balances
    .map((item) => formatCurrency(item.balance, item.currency))
    .join(" / ")
}

function formatHoldingQuantity(value: number): string {
  if (Number.isInteger(value)) {
    return value.toLocaleString()
  }
  return value.toLocaleString(undefined, { maximumFractionDigits: 4 })
}

export function AccountsOverview({
  accountSummary = [],
  rebalance,
  displayCurrency,
  isLoading = false,
  isError = false,
}: Props) {
  const { t } = useTranslation()
  const isPrivate = useIsPrivate()
  const [activeRowId, setActiveRowId] = useState<number | null>(null)
  const [expandedRowIds, setExpandedRowIds] = useState<Set<number>>(new Set())

  const fxRateByCurrency = useMemo(() => {
    const rates = new Map<string, number>()
    rates.set(displayCurrency, 1)
    for (const holding of rebalance?.holdings_detail ?? []) {
      if (!holding.currency) continue
      if (!Number.isFinite(holding.current_fx_rate) || (holding.current_fx_rate ?? 0) <= 0) continue
      if (!rates.has(holding.currency)) {
        rates.set(holding.currency, holding.current_fx_rate ?? 0)
      }
    }
    return rates
  }, [displayCurrency, rebalance?.holdings_detail])

  const rows = useMemo<AccountRow[]>(() => {
    const positionValueByAccount = new Map<number, number>()
    const holdingsByAccount = new Map<number, HoldingDetail[]>()
    for (const holding of rebalance?.holdings_detail ?? []) {
      if (holding.account_id == null) continue
      const accountHoldings = holdingsByAccount.get(holding.account_id) ?? []
      accountHoldings.push(holding)
      holdingsByAccount.set(holding.account_id, accountHoldings)
      positionValueByAccount.set(
        holding.account_id,
        (positionValueByAccount.get(holding.account_id) ?? 0) + (holding.market_value ?? 0),
      )
    }

    const mapped = accountSummary
      .filter((item) => item.account?.id != null)
      .map((item) => {
        const account = item.account!
        const balances = item.cash_balances ?? []
        let convertedCash = 0
        const missingFxCurrencies = new Set<string>()
        for (const balance of balances) {
          const rate = fxRateByCurrency.get(balance.currency)
          if (rate == null) {
            missingFxCurrencies.add(balance.currency)
            continue
          }
          convertedCash += balance.balance * rate
        }
        const totalValue = (positionValueByAccount.get(account.id) ?? 0) + convertedCash
        const accountHoldings = [...(holdingsByAccount.get(account.id) ?? [])].sort(
          (a, b) => (b.market_value ?? 0) - (a.market_value ?? 0),
        )
        const topHoldings = accountHoldings.slice(0, 3)
        const remainingCount = Math.max(accountHoldings.length - topHoldings.length, 0)
        let accountGainLoss = 0
        let accountCostTotal = 0
        let hasCostData = false
        for (const holding of accountHoldings) {
          const costTotal = holding.cost_total
          if (costTotal == null || costTotal <= 0) continue
          hasCostData = true
          accountCostTotal += costTotal
          accountGainLoss += (holding.market_value ?? 0) - costTotal
        }

        return {
          id: account.id,
          name: account.name,
          broker: account.broker,
          accountType: account.account_type,
          holdingsCount: item.holdings_count ?? 0,
          cashBalances: balances,
          missingFxCurrencies: Array.from(missingFxCurrencies),
          totalValue,
          sharePct: 0,
          color: "",
          topHoldings,
          remainingCount,
          accountGainLoss: hasCostData ? accountGainLoss : null,
          accountCostTotal,
        }
      })

    const sorted = mapped.sort((a, b) => b.totalValue - a.totalValue || a.name.localeCompare(b.name))
    const grandTotal = sorted.reduce((sum, row) => sum + row.totalValue, 0)
    return sorted.map((row, index) => ({
      ...row,
      sharePct: grandTotal > 0 ? (row.totalValue / grandTotal) * 100 : 0,
      color: ACCOUNT_COLORS[index % ACCOUNT_COLORS.length] ?? "#9CA3AF",
    }))
  }, [accountSummary, rebalance?.holdings_detail, fxRateByCurrency])

  const total = rows.reduce((sum, row) => sum + row.totalValue, 0)
  const legendRows = rows.slice(0, 4)
  const hiddenLegendCount = Math.max(rows.length - legendRows.length, 0)

  function setExpanded(rowId: number, isOpen: boolean) {
    setExpandedRowIds((prev) => {
      const next = new Set(prev)
      if (isOpen) {
        next.add(rowId)
      } else {
        next.delete(rowId)
      }
      return next
    })
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <Skeleton className="h-5 w-40" />
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
        </CardContent>
      </Card>
    )
  }

  if (isError && rows.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">{t("dashboard.accounts_overview.title")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <p className="text-sm font-semibold">{t("dashboard.accounts_overview.error_title")}</p>
          <p className="text-sm text-muted-foreground">{t("dashboard.accounts_overview.error_description")}</p>
        </CardContent>
      </Card>
    )
  }

  if (rows.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">{t("dashboard.accounts_overview.title")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm font-semibold">{t("dashboard.accounts_overview.empty_title")}</p>
          <p className="text-sm text-muted-foreground">{t("dashboard.accounts_overview.empty_description")}</p>
          <Button asChild size="sm" variant="outline" className="min-h-[36px]">
            <Link to="/allocation?tab=accounts">{t("dashboard.accounts_overview.empty_cta")}</Link>
          </Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="space-y-1">
            <CardTitle className="text-base">{t("dashboard.accounts_overview.title")}</CardTitle>
            <p className="text-xs text-muted-foreground">
              {t("dashboard.accounts_overview.header_total_label")}:{" "}
              <span className="font-semibold tabular-nums text-foreground">
                {isPrivate ? "***" : maskMoney(total, displayCurrency)}
              </span>
            </p>
          </div>
          <Button asChild size="sm" variant="outline" className="text-xs min-h-[36px]">
            <Link to="/allocation?tab=accounts">{t("dashboard.accounts_overview.view_all")}</Link>
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <span>{t("dashboard.accounts_overview.distribution_label")}</span>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    className="inline-flex h-5 w-5 items-center justify-center rounded-sm text-muted-foreground hover:text-foreground"
                    aria-label={t("dashboard.accounts_overview.distribution_help_aria")}
                  >
                    <CircleHelp className="h-3.5 w-3.5" />
                  </button>
                </TooltipTrigger>
                <TooltipContent sideOffset={6}>
                  {t("dashboard.accounts_overview.distribution_help")}
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>

          <div
            className="flex h-3.5 w-full overflow-hidden rounded-full bg-muted"
            role="group"
            aria-label={t("dashboard.accounts_overview.stacked_bar_aria")}
          >
            {rows.map((row) => (
              <button
                key={row.id}
                type="button"
                className="h-full transition-opacity focus-visible:z-10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                style={{
                  width: `${row.sharePct}%`,
                  backgroundColor: row.color,
                  opacity: activeRowId == null || activeRowId === row.id ? 1 : 0.35,
                }}
                aria-label={`${row.name} ${Math.round(row.sharePct)}%`}
                aria-pressed={activeRowId === row.id}
                title={isPrivate ? `${row.name}: ***` : `${row.name}: ${row.totalValue.toFixed(2)} ${displayCurrency}`}
                onPointerEnter={() => setActiveRowId(row.id)}
                onPointerLeave={() => setActiveRowId(null)}
                onFocus={() => setActiveRowId(row.id)}
                onBlur={() => setActiveRowId(null)}
                onClick={() => setActiveRowId((prev) => (prev === row.id ? null : row.id))}
              />
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
            {legendRows.map((row) => (
              <button
                key={row.id}
                type="button"
                className="inline-flex items-center gap-1.5 rounded-sm text-muted-foreground hover:text-foreground"
                style={{ opacity: activeRowId == null || activeRowId === row.id ? 1 : 0.45 }}
                aria-label={`${row.name} ${Math.round(row.sharePct)}%`}
                aria-pressed={activeRowId === row.id}
                onPointerEnter={() => setActiveRowId(row.id)}
                onPointerLeave={() => setActiveRowId(null)}
                onFocus={() => setActiveRowId(row.id)}
                onBlur={() => setActiveRowId(null)}
                onClick={() => setActiveRowId((prev) => (prev === row.id ? null : row.id))}
              >
                <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: row.color }} aria-hidden />
                <span className="max-w-28 truncate">{row.name}</span>
                <span className="tabular-nums">{Math.round(row.sharePct)}%</span>
              </button>
            ))}
            {hiddenLegendCount > 0 && (
              <span className="text-muted-foreground">
                {t("dashboard.accounts_overview.legend_more", { count: hiddenLegendCount })}
              </span>
            )}
          </div>
        </div>

        <ScrollArea className="pr-2" viewportClassName="max-h-[320px]">
          <div className="space-y-2">
            {rows.map((row) => {
              const cashSummary = isPrivate
                ? "***"
                : formatCashBalances(
                    row.cashBalances,
                    t("dashboard.accounts_overview.no_cash"),
                  )
              const rowMeta = `${t("dashboard.accounts_overview.positions_count", { count: row.holdingsCount })} · ${t("dashboard.accounts_overview.cash_label")}: ${cashSummary}`
              const accountReturnPct = row.accountGainLoss != null && row.accountCostTotal > 0
                ? (row.accountGainLoss / row.accountCostTotal) * 100
                : null

              return (
                <Collapsible key={row.id} open={expandedRowIds.has(row.id)} onOpenChange={(isOpen) => setExpanded(row.id, isOpen)}>
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
                            <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: row.color }} aria-hidden />
                            <AccountTypeIcon accountType={row.accountType} />
                            <span className="truncate text-sm font-semibold">{row.name}</span>
                            <span className="hidden truncate text-xs text-muted-foreground sm:inline">{rowMeta}</span>
                          </div>
                          <p className="mt-0.5 truncate text-xs text-muted-foreground sm:hidden">{rowMeta}</p>
                        </div>

                        <div className="flex shrink-0 items-center gap-2">
                          <div className="text-right">
                            <p className="text-[11px] text-muted-foreground">{t("dashboard.accounts_overview.total_label")}</p>
                            <p className="text-sm font-semibold tabular-nums">
                              {isPrivate ? "***" : maskMoney(row.totalValue, displayCurrency)}
                            </p>
                          </div>
                          <ChevronDown
                            className={`h-4 w-4 shrink-0 text-muted-foreground transition-transform ${expandedRowIds.has(row.id) ? "rotate-180" : ""}`}
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
                            const returnPct = holding.cost_total && holding.cost_total > 0
                              ? ((holding.market_value - holding.cost_total) / holding.cost_total) * 100
                              : null
                            const returnClass = returnPct == null
                              ? "text-muted-foreground"
                              : returnPct >= 0
                                ? FINANCE_TEXT.gain
                                : FINANCE_TEXT.loss
                            return (
                              <li key={`${row.id}-${holding.ticker}`} className="flex items-center justify-between gap-2">
                                <div className="min-w-0">
                                  <p className="truncate font-medium text-foreground">{holding.ticker}</p>
                                  <p className="truncate text-muted-foreground">
                                    {t("dashboard.accounts_overview.shares_label", { quantity: formatHoldingQuantity(holding.quantity) })}
                                  </p>
                                </div>
                                <div className="shrink-0 text-right">
                                  <p className="tabular-nums text-foreground">
                                    {isPrivate ? "***" : maskMoney(holding.market_value, displayCurrency)}
                                  </p>
                                  <p className={`tabular-nums ${returnClass}`}>
                                    {returnPct == null ? "—" : `${returnPct >= 0 ? "+" : ""}${returnPct.toFixed(1)}%`}
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

                    <div className="mt-2 flex items-center justify-between gap-2 border-t border-border/50 pt-2 text-xs">
                      <span className="text-muted-foreground">
                        {t("dashboard.accounts_overview.cash_label")}:
                      </span>
                      <span className="tabular-nums text-foreground">
                        {cashSummary}
                      </span>
                    </div>

                    {row.accountGainLoss != null && accountReturnPct != null && (
                      <div className="mt-1 flex items-center justify-between gap-2 text-xs">
                        <span className="text-muted-foreground">
                          {t("dashboard.accounts_overview.account_gain_loss")}
                        </span>
                        <span
                          className={`tabular-nums ${row.accountGainLoss >= 0 ? FINANCE_TEXT.gain : FINANCE_TEXT.loss}`}
                        >
                          {isPrivate
                            ? "***"
                            : `${row.accountGainLoss >= 0 ? "+" : "-"}${maskMoney(Math.abs(row.accountGainLoss), displayCurrency)} (${accountReturnPct >= 0 ? "+" : ""}${accountReturnPct.toFixed(1)}%)`}
                        </span>
                      </div>
                    )}
                  </CollapsibleContent>
                </div>
              </Collapsible>
              )
            })}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
