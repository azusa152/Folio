import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import {
  useApplyAllDividends,
  useApplyDividend,
  useCheckDividends,
  useDismissDividend,
  usePendingDividends,
} from "@/api/hooks/useAllocation"
import type { DividendEvent } from "@/api/types/allocation"
import { getErrorMessage } from "@/lib/utils"

interface DividendAlertProps {
  enabled?: boolean
}

export function DividendAlert({ enabled = true }: DividendAlertProps) {
  const { t } = useTranslation()
  const { data: events, isLoading } = usePendingDividends(enabled)
  const checkMutation = useCheckDividends()
  const applyMutation = useApplyDividend()
  const dismissMutation = useDismissDividend()
  const applyAllMutation = useApplyAllDividends()

  const pending = events ?? []
  const hasPending = pending.length > 0

  function PreviewRows({ event }: { event: DividendEvent }) {
    const rows = event.preview ?? []
    if (rows.length === 0) return null
    return (
      <div className="mt-1 space-y-1">
        {rows.map((row, idx) => (
          <p key={`${row.account_id ?? "na"}-${idx}`} className="text-xs text-muted-foreground">
            {row.account_name ? <span className="font-medium">{row.account_name}: </span> : null}
            {t("allocation.dividend.preview_line", {
              shares: row.shares,
              amount: row.amount_per_share,
              total: row.estimated_cash,
              currency: row.currency,
            })}
          </p>
        ))}
      </div>
    )
  }

  const handleCheck = () => {
    checkMutation.mutate(undefined, {
      onSuccess: (result) => {
        toast.success(t("allocation.dividend.check_success", { count: result.detected }))
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
        <p className="text-xs font-medium">{t("allocation.dividend.none_title")}</p>
        <p className="text-xs text-muted-foreground">{t("allocation.dividend.none_caption")}</p>
        <Button
          size="sm"
          variant="outline"
          className="text-xs"
          disabled={checkMutation.isPending}
          onClick={handleCheck}
        >
          {t("allocation.dividend.check_now")}
        </Button>
      </div>
    )
  }

  return (
    <div className="rounded-md border border-emerald-300/50 bg-emerald-50/40 dark:bg-emerald-950/20 p-3 space-y-3">
      <div className="space-y-1">
        <p className="text-sm font-semibold">{t("allocation.dividend.title")}</p>
        <p className="text-xs text-muted-foreground">{t("allocation.dividend.caption")}</p>
      </div>

      {isLoading ? (
        <p className="text-xs text-muted-foreground">{t("common.loading")}</p>
      ) : (
        <div className="space-y-2">
          {pending.map((event) => (
            <div
              key={event.id}
              className="rounded border border-border/60 bg-background/60 p-2 space-y-2"
            >
              <p className="text-xs font-medium">
                {t("allocation.dividend.item_title", {
                  ticker: event.ticker,
                  ex_date: event.ex_dividend_date,
                  amount: event.amount_per_share,
                })}
              </p>
              <p className="text-xs text-muted-foreground">{t("allocation.dividend.item_help")}</p>
              <PreviewRows event={event} />
              <div className="flex gap-2 flex-wrap">
                <Button
                  size="sm"
                  className="text-xs"
                  disabled={applyMutation.isPending || applyAllMutation.isPending}
                  onClick={() => {
                    applyMutation.mutate(event.id, {
                      onSuccess: () => toast.success(t("allocation.dividend.apply_success")),
                      onError: (err: unknown) =>
                        toast.error(getErrorMessage(err) || t("common.error")),
                    })
                  }}
                >
                  {t("allocation.dividend.apply")}
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  className="text-xs"
                  disabled={dismissMutation.isPending || applyAllMutation.isPending}
                  onClick={() => {
                    dismissMutation.mutate(event.id, {
                      onSuccess: () => toast.success(t("allocation.dividend.dismiss_success")),
                      onError: (err: unknown) =>
                        toast.error(getErrorMessage(err) || t("common.error")),
                    })
                  }}
                >
                  {t("allocation.dividend.dismiss")}
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
              onSuccess: (result) =>
                toast.success(
                  t("allocation.dividend.apply_all_success", { count: result.applied }),
                ),
              onError: (err: unknown) => toast.error(getErrorMessage(err) || t("common.error")),
            })
          }}
        >
          {t("allocation.dividend.apply_all")}
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="text-xs"
          disabled={checkMutation.isPending}
          onClick={handleCheck}
        >
          {t("allocation.dividend.check_now")}
        </Button>
      </div>
    </div>
  )
}
