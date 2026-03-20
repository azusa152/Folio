import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Link } from "react-router-dom"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { useIsPrivate, maskMoney } from "@/hooks/usePrivacyMode"
import type { AccountSummaryItem } from "@/api/types/account"
import type { HoldingDetail, RebalanceResponse } from "@/api/types/dashboard"
import { AccountEmptyState } from "./accounts/AccountEmptyState"
import { AccountSummaryCards } from "./accounts/AccountSummaryCards"
import { AccountTableRow } from "./accounts/AccountTableRow"
import { useAccountsOverviewData } from "./accounts/useAccountsOverviewData"

// ---------------------------------------------------------------------------
// Shared types exported for sub-components
// ---------------------------------------------------------------------------

export interface AccountRowData {
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

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface Props {
  accountSummary?: AccountSummaryItem[]
  rebalance?: RebalanceResponse | null
  displayCurrency: string
  isLoading?: boolean
  isError?: boolean
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

  if (isLoading || isError || rows.length === 0) {
    return (
      <AccountEmptyState
        isLoading={isLoading}
        isError={isError}
        hasRows={rows.length > 0}
      />
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
        <AccountSummaryCards
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
              <AccountTableRow
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
