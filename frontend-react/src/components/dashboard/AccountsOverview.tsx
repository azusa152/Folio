import { useMemo, useState } from "react"
import { BriefcaseBusiness, ChevronDown, CircleHelp, Landmark, PiggyBank, Wallet } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Link } from "react-router-dom"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { useIsPrivate, maskMoney } from "@/hooks/usePrivacyMode"
import { isTaxWrapperType, TAX_WRAPPER_ICONS } from "@/lib/constants"
import { FINANCE_TEXT } from "@/lib/colors"
import { formatCurrency, formatQuantity, formatSignedMoneyWithPrivacy, formatSignedPct, getQuantityUnitKey } from "@/lib/format"
import type { AccountSummaryItem } from "@/api/types/account"
import type { HoldingDetail, RebalanceResponse } from "@/api/types/dashboard"

interface Props {
  accountSummary?: AccountSummaryItem[]
  rebalance?: RebalanceResponse | null
  displayCurrency: string
  isLoading?: boolean
  isError?: boolean
}

interface AccountRowData {
  id: number
  name: string
  broker: string
  accountType: string
  taxWrapper?: string | null
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
  categoryBreakdown: Array<{
    category: "stocks" | "cash" | "crypto" | "bonds" | "commodities" | "other"
    value: number
    pct: number
    customLabel?: string
  }>
  dailyChange: number | null
  dailyChangePct: number | null
  dailyChangeCoveragePct: number | null
}

const ACCOUNT_COLORS = ["#2563EB", "#059669", "#D97706", "#7C3AED", "#0891B2", "#DC2626", "#EA580C", "#4F46E5"]
const DAILY_CHANGE_MIN_COVERAGE_PCT = 70
const LEGEND_ROW_LIMIT = 4
const TOP_HOLDINGS_LIMIT = 3

// ---------------------------------------------------------------------------
// Pure helpers
// ---------------------------------------------------------------------------

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

function toCategoryBucket(category: string | undefined): {
  category: "stocks" | "cash" | "crypto" | "bonds" | "commodities" | "other"
  customLabel?: string
} {
  const normalized = (category ?? "").trim().toLowerCase().replace(/[\s_]+/g, "_")
  if (normalized === "cash") return { category: "cash" }
  if (normalized === "crypto") return { category: "crypto" }
  if (normalized === "bond" || normalized === "fixed_income") return { category: "bonds" }
  if (normalized === "commodity" || normalized === "commodities") return { category: "commodities" }

  const stockLike = new Set([
    "equity",
    "etf",
    "growth",
    "moat",
    "trend_setter",
    "trendsetter",
  ])
  if (stockLike.has(normalized)) return { category: "stocks" }

  if (category && category.trim().length > 0) {
    return { category: "other", customLabel: category }
  }
  return { category: "stocks" }
}

function isCashHolding(holding: HoldingDetail): boolean {
  return toCategoryBucket(holding.category).category === "cash"
}

function categoryLabel(
  t: (key: string) => string,
  bucket: AccountRowData["categoryBreakdown"][number],
): string {
  if (bucket.category === "stocks") return t("dashboard.accounts_overview.stocks_category")
  if (bucket.category === "cash") return t("dashboard.accounts_overview.cash_category")
  if (bucket.category === "crypto") return t("dashboard.accounts_overview.crypto_category")
  if (bucket.category === "bonds") return t("dashboard.accounts_overview.bonds_category")
  if (bucket.category === "commodities") return t("dashboard.accounts_overview.commodities_category")
  return t("dashboard.accounts_overview.other_category")
}

// ---------------------------------------------------------------------------
// Data hook
// ---------------------------------------------------------------------------

function useAccountsOverviewData(
  accountSummary: AccountSummaryItem[],
  rebalance: RebalanceResponse | null | undefined,
  displayCurrency: string,
): { rows: AccountRowData[]; total: number; legendRows: AccountRowData[]; hiddenLegendCount: number } {
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

  const rows = useMemo<AccountRowData[]>(() => {
    const positionValueByAccount = new Map<number, number>()
    const holdingsByAccount = new Map<number, HoldingDetail[]>()
    for (const holding of rebalance?.holdings_detail ?? []) {
      if (holding.account_id == null) continue
      const accountHoldings = holdingsByAccount.get(holding.account_id) ?? []
      if (!isCashHolding(holding)) {
        accountHoldings.push(holding)
      }
      holdingsByAccount.set(holding.account_id, accountHoldings)
      if (!isCashHolding(holding)) {
        positionValueByAccount.set(
          holding.account_id,
          (positionValueByAccount.get(holding.account_id) ?? 0) + (holding.market_value ?? 0),
        )
      }
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
        const positionValue = positionValueByAccount.get(account.id) ?? 0
        const accountHoldings = [...(holdingsByAccount.get(account.id) ?? [])].sort(
          (a, b) => (b.market_value ?? 0) - (a.market_value ?? 0),
        )
        const topHoldings = accountHoldings.slice(0, TOP_HOLDINGS_LIMIT)
        const remainingCount = Math.max(accountHoldings.length - topHoldings.length, 0)
        let accountGainLoss = 0
        let accountCostTotal = 0
        let hasCostData = false
        let accountDailyChange = 0
        let hasDailyData = false
        let dailyCoveredCurrentValue = 0
        let dailyCoveredPreviousValue = 0
        const categoryByKey = new Map<string, { category: AccountRowData["categoryBreakdown"][number]["category"]; value: number; customLabel?: string }>()
        for (const holding of accountHoldings) {
          const bucket = toCategoryBucket(holding.category)
          const bucketKey = bucket.category
          const currentBucket = categoryByKey.get(bucketKey)
          if (currentBucket) {
            currentBucket.value += holding.market_value ?? 0
          } else {
            categoryByKey.set(bucketKey, {
              category: bucket.category,
              value: holding.market_value ?? 0,
              customLabel: bucket.customLabel,
            })
          }

          const costTotal = holding.cost_total
          if (costTotal == null || costTotal <= 0) continue
          hasCostData = true
          accountCostTotal += costTotal
          accountGainLoss += (holding.market_value ?? 0) - costTotal
        }
        for (const holding of accountHoldings) {
          if (!Number.isFinite(holding.change_pct) || !Number.isFinite(holding.market_value)) continue
          const changePct = holding.change_pct ?? 0
          const denominator = 100 + changePct
          if (Math.abs(denominator) < 1e-9) continue
          const currentValue = holding.market_value ?? 0
          const previousValue = currentValue / (1 + changePct / 100)
          const deltaValue = currentValue - previousValue
          if (!Number.isFinite(deltaValue) || !Number.isFinite(previousValue) || previousValue < 0) continue
          hasDailyData = true
          accountDailyChange += deltaValue
          dailyCoveredCurrentValue += currentValue
          dailyCoveredPreviousValue += previousValue
        }
        if (convertedCash > 0) {
          const cashBucket = categoryByKey.get("cash")
          if (cashBucket) {
            cashBucket.value += convertedCash
          } else {
            categoryByKey.set("cash", { category: "cash", value: convertedCash })
          }
        }
        const categoryBreakdown = [...categoryByKey.values()]
          .filter((entry) => entry.value > 0)
          .sort((a, b) => b.value - a.value)
          .map((entry) => ({
            category: entry.category,
            value: entry.value,
            pct: totalValue > 0 ? (entry.value / totalValue) * 100 : 0,
            customLabel: entry.customLabel,
          }))
        const previousValue = totalValue - accountDailyChange
        const dailyCoveragePct = positionValue > 0
          ? (dailyCoveredCurrentValue / positionValue) * 100
          : 0
        const dailyChangePct = hasDailyData && previousValue > 0
          && dailyCoveredPreviousValue > 0
          && dailyCoveragePct >= DAILY_CHANGE_MIN_COVERAGE_PCT
          ? (accountDailyChange / dailyCoveredPreviousValue) * 100
          : null

        return {
          id: account.id,
          name: account.name,
          broker: account.broker,
          accountType: account.account_type,
          taxWrapper: account.tax_wrapper,
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
          categoryBreakdown,
          dailyChange: hasDailyData ? accountDailyChange : null,
          dailyChangePct,
          dailyChangeCoveragePct: hasDailyData ? dailyCoveragePct : null,
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
  const legendRows = rows.slice(0, LEGEND_ROW_LIMIT)
  const hiddenLegendCount = Math.max(rows.length - legendRows.length, 0)

  return { rows, total, legendRows, hiddenLegendCount }
}

// ---------------------------------------------------------------------------
// AccountDistributionBar — stacked bar chart + legend
// ---------------------------------------------------------------------------

interface AccountDistributionBarProps {
  rows: AccountRowData[]
  legendRows: AccountRowData[]
  hiddenLegendCount: number
  activeRowId: number | null
  setActiveRowId: (id: number | null) => void
  isPrivate: boolean
  displayCurrency: string
}

function AccountDistributionBar({
  rows,
  legendRows,
  hiddenLegendCount,
  activeRowId,
  setActiveRowId,
  isPrivate,
  displayCurrency,
}: AccountDistributionBarProps) {
  const { t } = useTranslation()

  return (
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
            onClick={() => setActiveRowId(activeRowId === row.id ? null : row.id)}
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
            onClick={() => setActiveRowId(activeRowId === row.id ? null : row.id)}
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
  )
}

// ---------------------------------------------------------------------------
// AccountRow — collapsible per-account row
// ---------------------------------------------------------------------------

interface AccountRowProps {
  row: AccountRowData
  isExpanded: boolean
  onOpenChange: (isOpen: boolean) => void
  isPrivate: boolean
  displayCurrency: string
  setActiveRowId: (id: number | null) => void
}

function AccountRow({
  row,
  isExpanded,
  onOpenChange,
  isPrivate,
  displayCurrency,
  setActiveRowId,
}: AccountRowProps) {
  const { t } = useTranslation()

  const cashSummary = isPrivate
    ? "***"
    : formatCashBalances(row.cashBalances, t("dashboard.accounts_overview.no_cash"))
  const rowMeta = `${t("dashboard.accounts_overview.positions_count", { count: row.holdingsCount })} · ${t("dashboard.accounts_overview.cash_label")}: ${cashSummary}`
  const accountReturnPct = row.accountGainLoss != null && row.accountCostTotal > 0
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
                  <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: row.color }} aria-hidden />
                  <AccountTypeIcon accountType={row.accountType} />
                  <span className="truncate text-sm font-semibold">{row.name}</span>
                  {isTaxWrapperType(row.taxWrapper) ? (
                    <Badge variant="outline" className="hidden text-[11px] sm:inline-flex">
                      {TAX_WRAPPER_ICONS[row.taxWrapper]} {t(`wrapper.${row.taxWrapper}`)}
                    </Badge>
                  ) : null}
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
                  <li key={`${row.id}-${bucket.category}-${bucket.customLabel ?? "default"}`} className="space-y-1">
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
                <span className="text-muted-foreground">{t("dashboard.accounts_overview.today_change")}</span>
                <span
                  className={`tabular-nums ${row.dailyChange >= 0 ? FINANCE_TEXT.gain : FINANCE_TEXT.loss}`}
                >
                  {formatSignedMoneyWithPrivacy(row.dailyChange, displayCurrency, isPrivate)}
                  {!isPrivate && row.dailyChangePct != null && ` (${formatSignedPct(row.dailyChangePct, 1)})`}
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
                <span className="text-muted-foreground">{t("dashboard.accounts_overview.today_change")}</span>
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
                  const returnPct = holding.cost_total && holding.cost_total > 0
                    ? ((holding.market_value - holding.cost_total) / holding.cost_total) * 100
                    : null
                  const quantityUnit = getQuantityUnitKey(holding.category, holding.ticker)
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
              <span className="tabular-nums text-foreground">
                {cashSummary}
              </span>
            </div>
          )}
        </CollapsibleContent>
      </div>
    </Collapsible>
  )
}

// ---------------------------------------------------------------------------
// AccountsOverview — orchestrator
// ---------------------------------------------------------------------------

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

  const { rows, total, legendRows, hiddenLegendCount } = useAccountsOverviewData(
    accountSummary,
    rebalance,
    displayCurrency,
  )

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
        <AccountDistributionBar
          rows={rows}
          legendRows={legendRows}
          hiddenLegendCount={hiddenLegendCount}
          activeRowId={activeRowId}
          setActiveRowId={setActiveRowId}
          isPrivate={isPrivate}
          displayCurrency={displayCurrency}
        />

        <ScrollArea className="pr-2" viewportClassName="max-h-[320px]">
          <div className="space-y-2">
            {rows.map((row) => (
              <AccountRow
                key={row.id}
                row={row}
                isExpanded={expandedRowIds.has(row.id)}
                onOpenChange={(isOpen) => setExpanded(row.id, isOpen)}
                isPrivate={isPrivate}
                displayCurrency={displayCurrency}
                setActiveRowId={setActiveRowId}
              />
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
