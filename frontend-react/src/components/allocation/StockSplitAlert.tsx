import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import {
  useApplyAllStockSplits,
  useApplyStockSplit,
  useCheckStockSplits,
  useDismissStockSplit,
  usePendingStockSplits,
} from "@/api/hooks/useAllocation"
import type { StockSplitEvent } from "@/api/types/allocation"
import { getErrorMessage } from "@/lib/utils"

interface StockSplitAlertProps {
  enabled?: boolean
}

export function StockSplitAlert({ enabled = true }: StockSplitAlertProps) {
  const { t } = useTranslation()
  const { data: events, isLoading } = usePendingStockSplits(enabled)
  const checkMutation = useCheckStockSplits()
  const applyMutation = useApplyStockSplit()
  const dismissMutation = useDismissStockSplit()
  const applyAllMutation = useApplyAllStockSplits()

  const pending = events ?? []
  const hasPending = pending.length > 0

  function formatQty(n: number) {
    return n % 1 === 0 ? n.toFixed(0) : n.toFixed(4).replace(/\.?0+$/, "")
  }

  function PreviewRows({ event }: { event: StockSplitEvent }) {
    const rows = event.preview ?? []
    if (rows.length === 0) return null
    return (
      <div className="mt-1 space-y-1">
        {rows.map((row) => (
          <p key={row.account_id} className="text-xs text-muted-foreground font-mono">
            {row.account_name && <span className="font-medium font-sans">{row.account_name}: </span>}
            {formatQty(row.before_qty)} → <span className="text-green-600 dark:text-green-400">{formatQty(row.after_qty)}</span>
            {t("allocation.stock_split.preview_shares")}
            {row.before_cost_basis != null && row.after_cost_basis != null && (
              <> · {row.before_cost_basis.toFixed(2)} → <span className="text-green-600 dark:text-green-400">{row.after_cost_basis.toFixed(2)}</span>{t("allocation.stock_split.preview_cost")}</>
            )}
          </p>
        ))}
      </div>
    )
  }

  const handleCheck = () => {
    checkMutation.mutate(undefined, {
      onSuccess: (result) => {
        toast.success(
          t("allocation.stock_split.check_success", { count: result.detected }),
        )
      },
      onError: (err: unknown) => {
        toast.error(getErrorMessage(err) || t("common.error"))
      },
    })
  }

  if (!enabled) return null

  if (!hasPending && !isLoading) {
    return (
      <div className="rounded-md border border-border bg-muted/20 p-3 space-y-2">
        <p className="text-xs font-medium">{t("allocation.stock_split.none_title")}</p>
        <p className="text-xs text-muted-foreground">
          {t("allocation.stock_split.none_caption")}
        </p>
        <Button
          size="sm"
          variant="outline"
          className="text-xs"
          disabled={checkMutation.isPending}
          onClick={handleCheck}
        >
          {t("allocation.stock_split.check_now")}
        </Button>
      </div>
    )
  }

  return (
    <div className="rounded-md border border-amber-300/50 bg-amber-50/40 dark:bg-amber-950/20 p-3 space-y-3">
      <div className="space-y-1">
        <p className="text-sm font-semibold">{t("allocation.stock_split.title")}</p>
        <p className="text-xs text-muted-foreground">
          {t("allocation.stock_split.caption")}
        </p>
      </div>

      {isLoading ? (
        <p className="text-xs text-muted-foreground">{t("common.loading")}</p>
      ) : (
        <div className="space-y-2">
          {pending.map((event) => (
            <div key={event.id} className="rounded border border-border/60 bg-background/60 p-2 space-y-2">
              <p className="text-xs font-medium">
                {t("allocation.stock_split.item_title", {
                  ticker: event.ticker,
                  ratio: event.ratio_label,
                  split_date: event.split_date,
                })}
              </p>
              <p className="text-xs text-muted-foreground">
                {t("allocation.stock_split.item_help")}
              </p>
              <PreviewRows event={event} />
              <div className="flex gap-2 flex-wrap">
                <Button
                  size="sm"
                  className="text-xs"
                  disabled={applyMutation.isPending || applyAllMutation.isPending}
                  onClick={() => {
                    applyMutation.mutate(event.id, {
                      onSuccess: () => {
                        toast.success(t("allocation.stock_split.apply_success"))
                      },
                      onError: (err: unknown) => {
                        toast.error(getErrorMessage(err) || t("common.error"))
                      },
                    })
                  }}
                >
                  {t("allocation.stock_split.apply")}
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  className="text-xs"
                  disabled={dismissMutation.isPending || applyAllMutation.isPending}
                  onClick={() => {
                    dismissMutation.mutate(event.id, {
                      onSuccess: () => {
                        toast.success(t("allocation.stock_split.dismiss_success"))
                      },
                      onError: (err: unknown) => {
                        toast.error(getErrorMessage(err) || t("common.error"))
                      },
                    })
                  }}
                >
                  {t("allocation.stock_split.dismiss")}
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-2 flex-wrap">
        <Button
          size="sm"
          className="text-xs"
          disabled={!hasPending || applyAllMutation.isPending}
          onClick={() => {
            applyAllMutation.mutate(undefined, {
              onSuccess: (result) => {
                toast.success(
                  t("allocation.stock_split.apply_all_success", { count: result.applied }),
                )
              },
              onError: (err: unknown) => {
                toast.error(getErrorMessage(err) || t("common.error"))
              },
            })
          }}
        >
          {t("allocation.stock_split.apply_all")}
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="text-xs"
          disabled={checkMutation.isPending}
          onClick={handleCheck}
        >
          {t("allocation.stock_split.check_now")}
        </Button>
      </div>
    </div>
  )
}
