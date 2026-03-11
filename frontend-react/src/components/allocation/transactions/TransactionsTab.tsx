import { useState } from "react"
import { useTranslation } from "react-i18next"
import { useAccounts } from "@/api/hooks/useAccounts"
import { Button } from "@/components/ui/button"
import { useTransactions } from "@/api/hooks/useTransactions"
import { useHoldings } from "@/api/hooks/useDashboard"
import { TransactionList } from "./TransactionList"

interface Props {
  enabled: boolean
  onRecordTransaction: () => void
  onOpenAccounts?: () => void
}

export function TransactionsTab({ enabled, onRecordTransaction, onOpenAccounts }: Props) {
  const { t } = useTranslation()
  const [tickerFilter, setTickerFilter] = useState("")
  const [accountFilter, setAccountFilter] = useState("")
  const { data: holdings } = useHoldings()
  const { data: accounts } = useAccounts(enabled, true)
  const { data: transactions, isLoading } = useTransactions({
    ticker: tickerFilter || undefined,
    accountId: accountFilter ? Number(accountFilter) : undefined,
    enabled,
    limit: 500,
  })

  const tickers = Array.from(new Set((holdings ?? []).map((holding) => holding.ticker))).sort()

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div>
          <p className="text-sm font-semibold">{t("transactions.title")}</p>
          <p className="text-xs text-muted-foreground">{t("transactions.caption")}</p>
        </div>
        <Button className="text-xs min-h-[44px]" onClick={onRecordTransaction}>
          {t("transactions.record_button")}
        </Button>
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        <label htmlFor="txn-ticker-filter" className="text-xs text-muted-foreground">
          {t("transactions.filter.ticker")}
        </label>
        <select
          id="txn-ticker-filter"
          value={tickerFilter}
          onChange={(event) => setTickerFilter(event.target.value)}
          className="text-xs border border-border rounded px-3 py-2 min-h-[40px] bg-background"
        >
          <option value="">{t("transactions.filter.all_tickers")}</option>
          {tickers.map((ticker) => (
            <option key={ticker} value={ticker}>
              {ticker}
            </option>
          ))}
        </select>

        <label htmlFor="txn-account-filter" className="text-xs text-muted-foreground">
          {t("transactions.filter.account")}
        </label>
        <select
          id="txn-account-filter"
          value={accountFilter}
          onChange={(event) => setAccountFilter(event.target.value)}
          className="text-xs border border-border rounded px-3 py-2 min-h-[40px] bg-background"
        >
          <option value="">{t("transactions.filter.all_accounts")}</option>
          {(accounts ?? []).map((account) => (
            <option key={account.id} value={account.id}>
              {account.name}
            </option>
          ))}
        </select>
      </div>

      <TransactionList transactions={transactions ?? []} accounts={accounts ?? []} isLoading={isLoading} />
      {(accounts ?? []).length === 0 ? (
        <div className="rounded-md border border-dashed border-border p-3 text-xs text-muted-foreground">
          <p>{t("transactions.form.account_empty_hint")}</p>
          {onOpenAccounts ? (
            <button type="button" className="text-primary hover:underline mt-1" onClick={onOpenAccounts}>
              {t("transactions.form.create_account")}
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
