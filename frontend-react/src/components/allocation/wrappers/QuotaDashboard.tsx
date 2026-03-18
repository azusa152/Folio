import { useMemo } from "react"
import { useTranslation } from "react-i18next"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Badge } from "@/components/ui/badge"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { useRestorationForecast, useWrapperQuota } from "@/api/hooks/useWrappers"

function ratio(used: number, remaining: number): number {
  const total = used + remaining
  if (total <= 0) return 0
  return Math.max(0, Math.min(100, (used / total) * 100))
}

function formatDate(isoDate: string, locale: string): string {
  try {
    return new Date(`${isoDate}T00:00:00`).toLocaleDateString(locale)
  } catch {
    return isoDate
  }
}

export function QuotaDashboard({ enabled = true }: { enabled?: boolean }) {
  const { t, i18n } = useTranslation()
  const { data: quotaData, isLoading: quotaLoading } = useWrapperQuota(enabled)
  const { data: restorationData, isLoading: restorationLoading } = useRestorationForecast(enabled)

  const nisaTsumitate = quotaData?.quotas?.nisa_tsumitate
  const nisaGrowth = quotaData?.quotas?.nisa_growth

  const lifetime = useMemo(() => {
    // Both wrappers share the same combined lifetime figures from the API
    // (compute_lifetime_used sums across both NISA wrappers).
    // Use whichever wrapper is available; fall back to the other.
    const used = nisaTsumitate?.lifetime_used ?? nisaGrowth?.lifetime_used ?? 0
    const remaining = nisaTsumitate?.lifetime_remaining ?? nisaGrowth?.lifetime_remaining ?? 0
    return { used, remaining, pct: ratio(used, remaining) }
  }, [nisaGrowth?.lifetime_remaining, nisaGrowth?.lifetime_used, nisaTsumitate?.lifetime_remaining, nisaTsumitate?.lifetime_used])

  if (quotaLoading || restorationLoading) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">{t("wrapper.dashboard.title")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="text-base">{t("wrapper.dashboard.title")}</CardTitle>
          <Badge variant="outline">{t(`wrapper.dashboard.policy_${quotaData?.restoration_policy ?? "next_year"}`)}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <TooltipProvider>
        {[nisaTsumitate, nisaGrowth].map((quota) => {
          if (!quota) return null
          const used = quota.wrapper_annual_used
          const remaining = quota.wrapper_annual_remaining
          const limit = used + remaining
          return (
            <div key={quota.wrapper} className="space-y-1.5">
              <div className="flex items-center justify-between gap-2 text-xs">
                <span className="font-medium">{t(`wrapper.${quota.wrapper}`)}</span>
                <span className="text-muted-foreground">
                  {t("wrapper.dashboard.used_remaining", {
                    used: Math.round(used).toLocaleString(),
                    remaining: Math.round(Math.max(0, remaining)).toLocaleString(),
                  })}
                </span>
              </div>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    className="block w-full h-2 overflow-hidden rounded-full bg-muted focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"
                    aria-label={t("wrapper.dashboard.progress_tooltip", {
                      used: Math.round(used).toLocaleString(),
                      remaining: Math.round(Math.max(0, remaining)).toLocaleString(),
                      limit: Math.round(Math.max(0, limit)).toLocaleString(),
                    })}
                  >
                    <div
                      className="h-full rounded-full bg-primary"
                      style={{ width: `${ratio(used, remaining)}%` }}
                    />
                  </button>
                </TooltipTrigger>
                <TooltipContent className="text-xs">
                  {t("wrapper.dashboard.progress_tooltip", {
                    used: Math.round(used).toLocaleString(),
                    remaining: Math.round(Math.max(0, remaining)).toLocaleString(),
                    limit: Math.round(Math.max(0, limit)).toLocaleString(),
                  })}
                </TooltipContent>
              </Tooltip>
            </div>
          )
        })}

        <div className="space-y-1.5">
          <div className="flex items-center justify-between gap-2 text-xs">
            <span className="font-medium">{t("wrapper.dashboard.lifetime_combined")}</span>
            <span className="text-muted-foreground">
              {t("wrapper.dashboard.used_remaining", {
                used: Math.round(lifetime.used).toLocaleString(),
                remaining: Math.round(Math.max(0, lifetime.remaining)).toLocaleString(),
              })}
            </span>
          </div>
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                className="block w-full h-2 overflow-hidden rounded-full bg-muted focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"
                aria-label={t("wrapper.dashboard.progress_tooltip", {
                  used: Math.round(lifetime.used).toLocaleString(),
                  remaining: Math.round(Math.max(0, lifetime.remaining)).toLocaleString(),
                  limit: Math.round(Math.max(0, lifetime.used + lifetime.remaining)).toLocaleString(),
                })}
              >
                <div className="h-full rounded-full bg-emerald-500" style={{ width: `${lifetime.pct}%` }} />
              </button>
            </TooltipTrigger>
            <TooltipContent className="text-xs">
              {t("wrapper.dashboard.progress_tooltip", {
                used: Math.round(lifetime.used).toLocaleString(),
                remaining: Math.round(Math.max(0, lifetime.remaining)).toLocaleString(),
                limit: Math.round(Math.max(0, lifetime.used + lifetime.remaining)).toLocaleString(),
              })}
            </TooltipContent>
          </Tooltip>
        </div>

        {nisaGrowth ? (
          <div className="space-y-1.5">
            <div className="flex items-center justify-between gap-2 text-xs">
              <span className="font-medium">{t("wrapper.dashboard.growth_sub_limit")}</span>
              <span className="text-muted-foreground">
                {t("wrapper.dashboard.used_remaining", {
                  used: Math.round(nisaGrowth.growth_sub_limit_used ?? 0).toLocaleString(),
                  remaining: Math.round(Math.max(0, nisaGrowth.growth_sub_limit_remaining ?? 0)).toLocaleString(),
                })}
              </span>
            </div>
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  className="block w-full h-2 overflow-hidden rounded-full bg-muted focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring"
                  aria-label={t("wrapper.dashboard.progress_tooltip", {
                    used: Math.round(nisaGrowth.growth_sub_limit_used ?? 0).toLocaleString(),
                    remaining: Math.round(Math.max(0, nisaGrowth.growth_sub_limit_remaining ?? 0)).toLocaleString(),
                    limit: Math.round(
                      Math.max(0, (nisaGrowth.growth_sub_limit_used ?? 0) + (nisaGrowth.growth_sub_limit_remaining ?? 0)),
                    ).toLocaleString(),
                  })}
                >
                  <div
                    className="h-full rounded-full bg-blue-500"
                    style={{
                      width: `${ratio(nisaGrowth.growth_sub_limit_used ?? 0, nisaGrowth.growth_sub_limit_remaining ?? 0)}%`,
                    }}
                  />
                </button>
              </TooltipTrigger>
              <TooltipContent className="text-xs">
                {t("wrapper.dashboard.progress_tooltip", {
                  used: Math.round(nisaGrowth.growth_sub_limit_used ?? 0).toLocaleString(),
                  remaining: Math.round(Math.max(0, nisaGrowth.growth_sub_limit_remaining ?? 0)).toLocaleString(),
                  limit: Math.round(
                    Math.max(0, (nisaGrowth.growth_sub_limit_used ?? 0) + (nisaGrowth.growth_sub_limit_remaining ?? 0)),
                  ).toLocaleString(),
                })}
              </TooltipContent>
            </Tooltip>
          </div>
        ) : null}

        <div className="space-y-2">
          <p className="text-xs font-medium">{t("wrapper.dashboard.restoration_forecast")}</p>
          {restorationData?.pending?.length ? (
            <ul className="space-y-1">
              {restorationData.pending.map((item, index) => (
                <li key={`${item.tax_wrapper}-${item.effective_date}-${index}`} className="text-xs text-muted-foreground">
                  {t(`wrapper.${item.tax_wrapper}`)}: +{Math.round(item.amount).toLocaleString()} ({formatDate(String(item.effective_date), i18n.language)})
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-muted-foreground">{t("wrapper.dashboard.restoration_empty")}</p>
          )}
        </div>
        </TooltipProvider>
      </CardContent>
    </Card>
  )
}
