import { useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { useXRayAlert } from "@/api/hooks/useAllocation"
import type { XRayEntry } from "@/api/types/allocation"
import { useTerminology } from "@/hooks/useTerminology"
import { getErrorMessage } from "@/lib/utils"

interface Props {
  xray: XRayEntry[]
  coveragePct: number
  skippedEtfs: Array<{ ticker: string; weight_pct: number }>
}

const XRAY_WARNING_THRESHOLD = 15
const XRAY_LOW_COVERAGE_THRESHOLD = 50

function getCoverageBarClass(coveragePct: number): string {
  if (coveragePct >= 80) return "bg-emerald-500"
  if (coveragePct >= XRAY_LOW_COVERAGE_THRESHOLD) return "bg-amber-500"
  return "bg-rose-500"
}

export function XRayOverlap({ xray, coveragePct, skippedEtfs }: Props) {
  const { t } = useTranslation()
  const { term } = useTerminology()
  const alertMutation = useXRayAlert()
  const feedback = alertMutation.isSuccess ? t("common.success") : alertMutation.isError ? t("common.error") : null

  const top15 = [...xray].sort((a, b) => b.total_weight_pct - a.total_weight_pct).slice(0, 15)
  const hasWarning = top15.some((e) => e.total_weight_pct > XRAY_WARNING_THRESHOLD)
  const isLowCoverage = coveragePct < XRAY_LOW_COVERAGE_THRESHOLD
  const skippedEtfList = skippedEtfs.map((item) => `${item.ticker} (${item.weight_pct.toFixed(1)}%)`).join(", ")
  const [tableExpanded, setTableExpanded] = useState(false)
  const showTable = !isLowCoverage || tableExpanded

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold">{term("xray", t("allocation.xray.title"))}</p>
        <Button
          size="sm"
          variant="outline"
          className="text-xs"
          onClick={() => alertMutation.mutate(undefined, { onError: (err: unknown) => toast.error(getErrorMessage(err) || t("common.error")) })}
          disabled={alertMutation.isPending}
        >
          {t("allocation.xray.alert_button")}
        </Button>
      </div>

      <p className="text-xs text-muted-foreground">{t("allocation.xray.subtitle")}</p>

      <div className="space-y-1">
        <div className="flex items-center justify-between text-xs">
          <span className="text-muted-foreground">{t("allocation.xray.coverage_label")}</span>
          <span className="font-medium">{t("allocation.xray.coverage", { pct: coveragePct.toFixed(1) })}</span>
        </div>
        <div className="h-2 w-full rounded-full bg-muted">
          <div
            className={`h-2 rounded-full transition-all ${getCoverageBarClass(coveragePct)}`}
            style={{ width: `${Math.max(0, Math.min(coveragePct, 100))}%` }}
          />
        </div>
      </div>

      {skippedEtfs.length > 0 && (
        <div className="rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-700 dark:text-amber-300">
          {t("allocation.xray.skipped_etf", { etfs: skippedEtfList })}
        </div>
      )}

      {isLowCoverage && (
        <div className="rounded-md border border-blue-500/40 bg-blue-500/10 px-3 py-2 text-xs text-blue-700 dark:text-blue-300">
          <p>{t("allocation.xray.low_coverage")}</p>
          {top15.length > 0 && (
            <button
              type="button"
              className="mt-1 underline underline-offset-2 hover:opacity-80"
              onClick={() => setTableExpanded((v) => !v)}
            >
              {tableExpanded ? t("allocation.xray.hide_table") : t("allocation.xray.show_table")}
            </button>
          )}
        </div>
      )}

      {top15.length === 0 && <p className="text-sm text-muted-foreground">{t("allocation.xray.empty")}</p>}

      {showTable && hasWarning && (
        <div className="rounded-md border border-orange-500/40 bg-orange-500/10 px-3 py-2 text-xs text-orange-700 dark:text-orange-400">
          {t("allocation.xray.warning", { threshold: XRAY_WARNING_THRESHOLD })}
        </div>
      )}

      {showTable && top15.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <TooltipProvider>
              <thead>
                <tr className="text-muted-foreground border-b border-border">
                  <th className="text-left py-0.5 pr-2">{t("allocation.col.ticker")}</th>
                  <th className="text-left py-0.5 pr-2">{t("allocation.xray.col_name")}</th>
                  <th className="text-right py-0.5 pr-2">
                    <span className="inline-flex items-center gap-1">
                      {t("allocation.xray.col_direct")}
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <button
                            type="button"
                            aria-label={t("allocation.xray.help_direct")}
                            className="h-4 w-4 rounded-full border border-border text-[10px] leading-none"
                          >
                            ?
                          </button>
                        </TooltipTrigger>
                        <TooltipContent sideOffset={6}>{t("allocation.xray.help_direct")}</TooltipContent>
                      </Tooltip>
                    </span>
                  </th>
                  <th className="text-right py-0.5 pr-2">
                    <span className="inline-flex items-center gap-1">
                      {t("allocation.xray.col_indirect")}
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <button
                            type="button"
                            aria-label={t("allocation.xray.help_indirect")}
                            className="h-4 w-4 rounded-full border border-border text-[10px] leading-none"
                          >
                            ?
                          </button>
                        </TooltipTrigger>
                        <TooltipContent sideOffset={6}>{t("allocation.xray.help_indirect")}</TooltipContent>
                      </Tooltip>
                    </span>
                  </th>
                  <th className="text-right py-0.5">{t("allocation.xray.col_total")}</th>
                </tr>
              </thead>
            </TooltipProvider>
            <tbody>
              {top15.map((e) => (
                <tr
                  key={e.symbol}
                  className={`border-b border-border/50 ${e.total_weight_pct > XRAY_WARNING_THRESHOLD ? "text-orange-600 dark:text-orange-400" : ""}`}
                >
                  <td className="py-0.5 pr-2 font-medium">{e.symbol}</td>
                  <td className="py-0.5 pr-2 text-muted-foreground max-w-[120px] truncate">{e.name}</td>
                  <td className="py-0.5 pr-2 text-right">{e.direct_weight_pct.toFixed(1)}%</td>
                  <td className="py-0.5 pr-2 text-right">{e.indirect_weight_pct.toFixed(1)}%</td>
                  <td className="py-0.5 text-right font-semibold">{e.total_weight_pct.toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {feedback && <p className="text-xs text-muted-foreground">{feedback}</p>}
    </div>
  )
}
