import { useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { CATEGORY_COLOR_FALLBACK, CATEGORY_COLOR_MAP, CATEGORY_ICON_SHORT } from "@/lib/constants"
import type { HoldingDetail, RebalanceResponse } from "@/api/types/dashboard"

const TOP_LIMIT = 8

interface Props {
  rebalance?: RebalanceResponse | null
  isLoading?: boolean
}

interface RowItem {
  label: string
  category: string
  weightPct: number
  color: string
}

function getCategoryColor(category: string): string {
  return CATEGORY_COLOR_MAP[category] ?? CATEGORY_COLOR_FALLBACK
}

function normalizeHoldingWeight(weight: number | null | undefined): number {
  if (!Number.isFinite(weight)) return 0
  return Math.max(0, Number(weight))
}

export function HoldingBreakdown({ rebalance, isLoading = false }: Props) {
  const { t } = useTranslation()
  const [expanded, setExpanded] = useState(false)

  const allRows = useMemo<RowItem[]>(() => {
    const holdings = rebalance?.holdings_detail ?? []
    const sorted = [...holdings]
      .map((holding: HoldingDetail) => {
        const weightPct = normalizeHoldingWeight(holding.weight_pct)
        return {
          label: holding.ticker,
          category: holding.category,
          weightPct,
          color: getCategoryColor(holding.category),
        }
      })
      .filter((holding) => holding.weightPct > 0)
      .sort((a, b) => b.weightPct - a.weightPct)

    return sorted
  }, [rebalance?.holdings_detail])

  const hasMore = allRows.length > TOP_LIMIT
  const otherWeight = allRows.slice(TOP_LIMIT).reduce((sum, h) => sum + h.weightPct, 0)

  const collapsedRows: RowItem[] = otherWeight > 0
    ? [
        ...allRows.slice(0, TOP_LIMIT),
        {
          label: t("dashboard.holding_breakdown.other"),
          category: "Other",
          weightPct: otherWeight,
          color: CATEGORY_COLOR_FALLBACK,
        },
      ]
    : allRows.slice(0, TOP_LIMIT)

  const displayRows = expanded ? allRows : collapsedRows
  const totalWeight = allRows.reduce((sum, row) => sum + row.weightPct, 0)

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-4 sm:p-6 space-y-3">
          <Skeleton className="h-5 w-48" />
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-full" />
        </CardContent>
      </Card>
    )
  }

  if (allRows.length === 0) return null

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">{t("dashboard.holding_breakdown.title")}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div
          className="flex h-3 w-full overflow-hidden rounded-full bg-muted"
          role="img"
          aria-label={t("dashboard.holding_breakdown.stacked_bar_aria")}
        >
          {collapsedRows.map((row) => (
            <div
              key={`${row.label}-${row.category}`}
              className="h-full"
              style={{
                width: `${totalWeight > 0 ? (row.weightPct / totalWeight) * 100 : 0}%`,
                backgroundColor: row.color,
              }}
              title={`${row.label}: ${row.weightPct.toFixed(1)}%`}
            />
          ))}
        </div>

        <div className="space-y-2">
          {displayRows.map((row) => (
            <div key={`${row.label}-${row.category}`} className="space-y-1.5">
              <div className="flex items-center justify-between gap-3 text-sm">
                <span className="truncate text-muted-foreground">
                  {CATEGORY_ICON_SHORT[row.category] ?? ""} {row.label}
                </span>
                <span className="font-medium tabular-nums">{row.weightPct.toFixed(1)}%</span>
              </div>
              <div className="h-2 w-full rounded-full bg-muted">
                <div
                  className="h-full rounded-full transition-all"
                  style={{
                    width: `${totalWeight > 0 ? (row.weightPct / totalWeight) * 100 : 0}%`,
                    backgroundColor: row.color,
                  }}
                />
              </div>
            </div>
          ))}
        </div>

        {hasMore && (
          <Button
            variant="ghost"
            size="sm"
            className="h-auto px-0 text-xs"
            onClick={() => setExpanded((prev) => !prev)}
          >
            {expanded ? t("dashboard.holding_breakdown.show_less") : t("dashboard.holding_breakdown.show_all")}
          </Button>
        )}
      </CardContent>
    </Card>
  )
}
