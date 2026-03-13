import { useMemo } from "react"
import { BriefcaseBusiness, Landmark, PiggyBank, Wallet } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Link } from "react-router-dom"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useIsPrivate, maskMoney } from "@/hooks/usePrivacyMode"
import { formatCurrency } from "@/lib/format"
import type { AccountSummaryItem } from "@/api/types/account"
import type { RebalanceResponse } from "@/api/types/dashboard"

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
}

const ACCOUNT_TYPE_COLOR: Record<string, string> = {
  brokerage: "#3B82F6",
  retirement: "#3B82F6",
  savings: "#10B981",
  bank: "#10B981",
  wallet: "#F59E0B",
  cash_wallet: "#F59E0B",
  crypto: "#8B5CF6",
  insurance: "#14B8A6",
  loan: "#EF4444",
  other: "#9CA3AF",
}

function accountTypeColor(accountType: string): string {
  return ACCOUNT_TYPE_COLOR[accountType] ?? "#9CA3AF"
}

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

export function AccountsOverview({
  accountSummary = [],
  rebalance,
  displayCurrency,
  isLoading = false,
  isError = false,
}: Props) {
  const { t } = useTranslation()
  const isPrivate = useIsPrivate()

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
    for (const holding of rebalance?.holdings_detail ?? []) {
      if (holding.account_id == null) continue
      positionValueByAccount.set(
        holding.account_id,
        (positionValueByAccount.get(holding.account_id) ?? 0) + (holding.market_value ?? 0),
      )
    }

    const mapped: AccountRow[] = accountSummary
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

        return {
          id: account.id,
          name: account.name,
          broker: account.broker,
          accountType: account.account_type,
          holdingsCount: item.holdings_count ?? 0,
          cashBalances: balances,
          missingFxCurrencies: Array.from(missingFxCurrencies),
          totalValue,
        }
      })

    return mapped.sort((a, b) => b.totalValue - a.totalValue || a.name.localeCompare(b.name))
  }, [accountSummary, rebalance?.holdings_detail, fxRateByCurrency])

  const total = rows.reduce((sum, row) => sum + row.totalValue, 0)

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
        <div className="flex items-center justify-between gap-3">
          <CardTitle className="text-base">{t("dashboard.accounts_overview.title")}</CardTitle>
          <Button asChild size="sm" variant="outline" className="text-xs min-h-[36px]">
            <Link to="/allocation?tab=accounts">{t("dashboard.accounts_overview.view_all")}</Link>
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div
          className="flex h-2.5 w-full overflow-hidden rounded-full bg-muted"
          role="img"
          aria-label={t("dashboard.accounts_overview.stacked_bar_aria")}
        >
          {rows.map((row) => (
            <div
              key={row.id}
              className="h-full"
              style={{
                width: `${total > 0 ? (row.totalValue / total) * 100 : 0}%`,
                backgroundColor: accountTypeColor(row.accountType),
              }}
              title={isPrivate ? `${row.name}: ***` : `${row.name}: ${row.totalValue.toFixed(2)} ${displayCurrency}`}
            />
          ))}
        </div>

        <div className="space-y-3">
          {rows.map((row) => (
            <div key={row.id} className="rounded-md border border-border/60 p-3">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm font-semibold flex items-center gap-1.5">
                    <AccountTypeIcon accountType={row.accountType} />
                    <span className="truncate">{row.name}</span>
                  </p>
                  <p className="text-xs text-muted-foreground truncate">
                    {row.broker} · {t(`config.account_type.${row.accountType}`)}
                  </p>
                </div>
                <div className="text-right shrink-0">
                  <p className="text-[11px] text-muted-foreground">{t("dashboard.accounts_overview.total_label")}</p>
                  <p className="text-sm font-semibold tabular-nums">
                    {isPrivate ? "***" : maskMoney(row.totalValue, displayCurrency)}
                  </p>
                </div>
              </div>

              <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                <span>{t("dashboard.accounts_overview.positions_count", { count: row.holdingsCount })}</span>
                <span>
                  {t("dashboard.accounts_overview.cash_label")}:{" "}
                  {isPrivate
                    ? "***"
                    : formatCashBalances(
                        row.cashBalances,
                        t("dashboard.accounts_overview.no_cash"),
                      )}
                </span>
              </div>

              {row.missingFxCurrencies.length > 0 && (
                <p className="mt-1 text-[11px] text-muted-foreground">
                  {t("dashboard.accounts_overview.cash_missing_fx_hint", {
                    currencies: row.missingFxCurrencies.join(", "),
                  })}
                </p>
              )}

              <div className="mt-2 flex items-center gap-2">
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
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
