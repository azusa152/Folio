import { useMemo } from "react"
import type { AccountSummaryItem } from "@/api/types/account"
import type { HoldingDetail, RebalanceResponse } from "@/api/types/dashboard"
import type { AccountRowData } from "../AccountsOverview"

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const ACCOUNT_COLORS = ["#2563EB", "#059669", "#D97706", "#7C3AED", "#0891B2", "#DC2626", "#EA580C", "#4F46E5"]
const DAILY_CHANGE_MIN_COVERAGE_PCT = 70
const LEGEND_ROW_LIMIT = 4
const TOP_HOLDINGS_LIMIT = 3

// ---------------------------------------------------------------------------
// Pure helpers
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useAccountsOverviewData(
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
