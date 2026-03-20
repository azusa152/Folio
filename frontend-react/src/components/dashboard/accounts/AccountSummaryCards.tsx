import { useTranslation } from "react-i18next"
import { CircleHelp } from "lucide-react"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import type { AccountRowData } from "../AccountsOverview"

interface Props {
  rows: AccountRowData[]
  legendRows: AccountRowData[]
  hiddenLegendCount: number
  activeRowId: number | null
  setActiveRowId: (id: number | null) => void
  isPrivate: boolean
  displayCurrency: string
}

export function AccountSummaryCards({
  rows,
  legendRows,
  hiddenLegendCount,
  activeRowId,
  setActiveRowId,
  isPrivate,
  displayCurrency,
}: Props) {
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
