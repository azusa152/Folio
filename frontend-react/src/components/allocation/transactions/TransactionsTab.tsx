import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Button } from "@/components/ui/button"
import { useTransactions } from "@/api/hooks/useTransactions"
import { useHoldings } from "@/api/hooks/useDashboard"
import { TransactionList } from "./TransactionList"

interface Props {
  enabled: boolean
  onRecordTransaction: () => void
}

export function TransactionsTab({ enabled, onRecordTransaction }: Props) {
  const { t } = useTranslation()
  const [tickerFilter, setTickerFilter] = useState("")
  const { data: holdings } = useHoldings()
  const { data: transactions, isLoading } = useTransactions({
    ticker: tickerFilter || undefined,
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

      <div className="flex items-center gap-2">
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
      </div>

      <TransactionList transactions={transactions ?? []} isLoading={isLoading} />
    </div>
  )
}
