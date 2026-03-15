import { useEffect, useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { useSearchParams } from "react-router-dom"
import { RefreshCw } from "lucide-react"
import { formatLocalTime, formatRelativeTime, parseUtc, getErrorMessage } from "@/lib/utils"
import { FX_WATCH_REFRESH_COOLDOWN_SECONDS } from "@/lib/constants"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import {
  useFxWatches,
  useFxAnalysis,
  useCheckFxWatches,
  useAlertFxWatches,
  useFxHistoryMap,
  useRefreshFxRates,
} from "@/api/hooks/useFxWatch"
import { WatchCard } from "@/components/fxwatch/WatchCard"
import { AddWatchDialog } from "@/components/fxwatch/AddWatchDialog"
import type { FxWatch } from "@/api/types/fxWatch"
import { useCurrencyExposure } from "@/api/hooks/useAllocation"
import { CurrencyExposure } from "@/components/allocation/tools/CurrencyExposure"
import { PortfolioImpactSnapshot } from "@/components/fxwatch/PortfolioImpactSnapshot"
import { useProfile } from "@/api/hooks/useDashboard"
import { usePrivacyMode } from "@/hooks/usePrivacyMode"

type SortMode = "alert_first" | "alphabetical" | "volatility"
type FilterMode = "all" | "active_only"

function isRateLimitError(err: unknown): boolean {
  if (err == null || typeof err !== "object") return false
  const obj = err as Record<string, unknown>
  if (obj.status === 429) return true
  if (obj.statusCode === 429) return true
  if (typeof obj.response === "object" && obj.response !== null) {
    const response = obj.response as Record<string, unknown>
    if (response.status === 429) return true
  }
  return false
}

function getRetryAfterSeconds(err: unknown): number | null {
  if (err == null || typeof err !== "object") return null
  const obj = err as Record<string, unknown>

  const asPositiveInt = (value: unknown): number | null => {
    const n = typeof value === "string" ? Number.parseInt(value, 10) : Number(value)
    if (!Number.isFinite(n) || n <= 0) return null
    return Math.ceil(n)
  }

  const directRetry = asPositiveInt(obj.retry_after_seconds)
  if (directRetry !== null) return directRetry

  if (typeof obj.detail === "object" && obj.detail !== null) {
    const detail = obj.detail as Record<string, unknown>
    const detailRetry = asPositiveInt(detail.retry_after_seconds)
    if (detailRetry !== null) return detailRetry
  }

  if (typeof obj.response === "object" && obj.response !== null) {
    const response = obj.response as Record<string, unknown>
    const responseRetry = asPositiveInt(response.retry_after_seconds)
    if (responseRetry !== null) return responseRetry

    if (typeof response.headers === "object" && response.headers !== null) {
      const headers = response.headers as Record<string, unknown>
      const retryAfter =
        asPositiveInt(headers["retry-after"]) ??
        asPositiveInt(headers["Retry-After"])
      if (retryAfter !== null) return retryAfter
    }
  }

  return null
}

/** Returns absolute (unsigned) % change — used for volatility sort. */
function computeAbsChangePct(history: { close: number }[]): number | null {
  if (history.length < 2) return null
  const first = history[0].close
  const last = history[history.length - 1].close
  if (first <= 0) return null
  return Math.abs((last - first) / first) * 100
}

export default function FxWatch() {
  const { t, i18n } = useTranslation()
  const [searchParams, setSearchParams] = useSearchParams()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [nowEpochSeconds, setNowEpochSeconds] = useState(() => Math.floor(Date.now() / 1000))
  const [refreshCooldownUntilEpochSeconds, setRefreshCooldownUntilEpochSeconds] = useState(0)
  const [refreshCooldownRemainingSeconds, setRefreshCooldownRemainingSeconds] = useState(0)
  const rawSort = searchParams.get("sort")
  const rawFilter = searchParams.get("filter")
  const rawTab = searchParams.get("tab")
  const sortMode: SortMode =
    rawSort === "alphabetical" || rawSort === "volatility" || rawSort === "alert_first"
      ? rawSort
      : "alert_first"
  const filterMode: FilterMode = rawFilter === "active_only" ? "active_only" : "all"
  const activeTab = rawTab === "overview" || rawTab === "exposure" ? rawTab : "watches"

  const { data: watches, isLoading, isError } = useFxWatches()
  const { data: profile } = useProfile()
  const privacyMode = usePrivacyMode((s) => s.isPrivate)
  const { data: exposure } = useCurrencyExposure(activeTab !== "watches")
  const setSortMode = (nextSortMode: SortMode) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      if (nextSortMode === "alert_first") next.delete("sort")
      else next.set("sort", nextSortMode)
      return next
    })
  }

  const setFilterMode = (nextFilterMode: FilterMode) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      if (nextFilterMode === "all") next.delete("filter")
      else next.set("filter", nextFilterMode)
      return next
    })
  }
  const setActiveTab = (nextTab: "overview" | "watches" | "exposure") => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      if (nextTab === "watches") next.delete("tab")
      else next.set("tab", nextTab)
      return next
    })
  }

  useEffect(() => {
    const timer = window.setInterval(() => setNowEpochSeconds(Math.floor(Date.now() / 1000)), 60_000)
    return () => window.clearInterval(timer)
  }, [])

  useEffect(() => {
    if (refreshCooldownUntilEpochSeconds <= 0) return

    const timer = window.setInterval(() => {
      const now = Math.floor(Date.now() / 1000)
      const remaining = Math.max(0, refreshCooldownUntilEpochSeconds - now)
      setRefreshCooldownRemainingSeconds(remaining)
      if (remaining === 0) {
        setRefreshCooldownUntilEpochSeconds(0)
        window.clearInterval(timer)
      }
    }, 1000)
    return () => window.clearInterval(timer)
  }, [refreshCooldownUntilEpochSeconds])

  const hasWatches = (watches?.length ?? 0) > 0
  const { data: analysisState, isLoading: analysisLoading } = useFxAnalysis(hasWatches)
  const analysisMap = useMemo(() => analysisState?.by_watch_id ?? {}, [analysisState])
  const checkMutation = useCheckFxWatches()
  const refreshMutation = useRefreshFxRates()
  const alertMutation = useAlertFxWatches()

  // Eagerly fetch history for all pairs (sparklines)
  const pairs = useMemo(
    () => (watches ?? []).map((w) => ({ base: w.base_currency, quote: w.quote_currency })),
    [watches],
  )
  const { data: historyMap = {} } = useFxHistoryMap(pairs)

  // Summary stats
  const activeCount = watches?.filter((w) => w.is_active).length ?? 0
  const alertCount = Object.values(analysisMap).filter((a) => a.should_alert).length
  const lastAlertTimes = (watches ?? [])
    .map((w) => w.last_alerted_at)
    .filter((ts): ts is string => ts !== null)
  const lastAlert =
    lastAlertTimes.length > 0
      ? formatLocalTime(lastAlertTimes.reduce((a, b) => (parseUtc(a) > parseUtc(b) ? a : b)))
      : null

  const checkedAtEpoch = analysisState?.checked_at ? Math.floor(parseUtc(analysisState.checked_at).getTime() / 1000) : 0
  const ratesUpdatedAgo =
    checkedAtEpoch > 0
      ? formatRelativeTime(nowEpochSeconds - checkedAtEpoch, i18n.language)
      : ""

  const freshnessAgeSeconds = checkedAtEpoch > 0 ? nowEpochSeconds - checkedAtEpoch : null
  const freshnessDotClass =
    freshnessAgeSeconds === null
      ? "bg-muted-foreground/40"
      : freshnessAgeSeconds < 10 * 60
        ? "bg-emerald-500"
        : freshnessAgeSeconds < 2 * 60 * 60
          ? "bg-amber-500"
          : "bg-muted-foreground/40"

  const checkedAtLabel = analysisState?.checked_at ? formatLocalTime(analysisState.checked_at) : null
  const handleCheck = () => {
    checkMutation.mutate(undefined, {
      onSuccess: () => toast.success(t("common.success")),
      onError: (err: unknown) => {
        if (isRateLimitError(err)) {
          const retryAfter = getRetryAfterSeconds(err)
          toast.error(
            retryAfter
              ? t("fx_watch.rate_limit_exceeded_retry_after", { seconds: retryAfter })
              : t("fx_watch.rate_limit_exceeded"),
          )
          return
        }
        toast.error(getErrorMessage(err) || t("common.error"))
      },
    })
  }

  const handleRefreshRates = () => {
    refreshMutation.mutate(undefined, {
      onSuccess: () => {
        setRefreshCooldownRemainingSeconds(FX_WATCH_REFRESH_COOLDOWN_SECONDS)
        setRefreshCooldownUntilEpochSeconds(
          Math.floor(Date.now() / 1000) + FX_WATCH_REFRESH_COOLDOWN_SECONDS,
        )
        toast.success(t("fx_watch.refresh_success"))
      },
      onError: (err: unknown) => {
        if (isRateLimitError(err)) {
          const retryAfter = getRetryAfterSeconds(err)
          toast.error(
            retryAfter
              ? t("fx_watch.rate_limit_exceeded_retry_after", { seconds: retryAfter })
              : t("fx_watch.rate_limit_exceeded"),
          )
          return
        }
        toast.error(getErrorMessage(err) || t("common.error"))
      },
    })
  }

  const handleAlert = () => {
    alertMutation.mutate(undefined, {
      onSuccess: () => toast.success(t("common.success")),
      onError: (err: unknown) => toast.error(getErrorMessage(err) || t("common.error")),
    })
  }

  // Filter
  const filteredWatches = useMemo(() => {
    if (!watches) return []
    if (filterMode === "active_only") return watches.filter((w) => w.is_active)
    return watches
  }, [watches, filterMode])

  // Sort
  const sortedWatches = useMemo(() => {
    const list = [...filteredWatches]
    if (sortMode === "alert_first") {
      list.sort((a, b) => {
        const aAlert = analysisMap[a.id]?.should_alert ? 1 : 0
        const bAlert = analysisMap[b.id]?.should_alert ? 1 : 0
        if (bAlert !== aAlert) return bAlert - aAlert
        // secondary: active first
        return (b.is_active ? 1 : 0) - (a.is_active ? 1 : 0)
      })
    } else if (sortMode === "alphabetical") {
      list.sort((a, b) => {
        const pairA = `${a.base_currency}/${a.quote_currency}`
        const pairB = `${b.base_currency}/${b.quote_currency}`
        return pairA.localeCompare(pairB)
      })
    } else if (sortMode === "volatility") {
      list.sort((a, b) => {
        const pairA = `${a.base_currency}/${a.quote_currency}`
        const pairB = `${b.base_currency}/${b.quote_currency}`
        const histA = historyMap[pairA] ?? []
        const histB = historyMap[pairB] ?? []
        const volA = computeAbsChangePct(histA.slice(-30)) ?? 0
        const volB = computeAbsChangePct(histB.slice(-30)) ?? 0
        return volB - volA
      })
    }
    return list
  }, [filteredWatches, sortMode, analysisMap, historyMap])

  if (isLoading) {
    return (
      <div className="p-3 sm:p-6 space-y-4">
        <Skeleton className="h-8 w-56" />
        <Skeleton className="h-4 w-72" />
        <div className="grid grid-cols-4 gap-3">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-14 rounded-lg" />
          ))}
        </div>
        {[1, 2].map((i) => (
          <Skeleton key={i} className="h-16 w-full rounded-lg" />
        ))}
      </div>
    )
  }

  if (isError || !watches) {
    return (
      <div className="p-3 sm:p-6 space-y-3">
        <h1 className="text-xl sm:text-2xl font-bold">{t("fx_watch.title")}</h1>
        <p className="text-sm text-destructive">{t("common.error_backend")}</p>
      </div>
    )
  }

  return (
    <div className="p-3 sm:p-6 space-y-4">
      {/* Toolbar row */}
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h1 className="text-xl sm:text-2xl font-bold">{t("fx_watch.title")}</h1>
            {/* SOP info popover */}
            <Popover>
              <PopoverTrigger asChild>
                <button
                  aria-label={t("fx_watch.sop_title")}
                  className="rounded-full min-h-[44px] min-w-[44px] text-xs border border-border text-muted-foreground hover:text-foreground transition-colors flex items-center justify-center"
                >
                  ?
                </button>
              </PopoverTrigger>
              <PopoverContent className="w-96 max-h-96 overflow-y-auto text-xs" align="start">
                <p className="font-semibold mb-2">{t("fx_watch.sop_title")}</p>
                <div className="text-muted-foreground whitespace-pre-wrap leading-relaxed">
                  {t("fx_watch.sop_content")}
                </div>
              </PopoverContent>
            </Popover>
          </div>
          <p className="text-sm text-muted-foreground">{t("fx_watch.caption")}</p>
          <div className="mt-1 flex items-center gap-2 flex-wrap">
            {ratesUpdatedAgo ? (
              <p className="text-xs text-muted-foreground" title={checkedAtLabel ?? undefined}>
                <span className={`mr-1 inline-block h-2 w-2 rounded-full ${freshnessDotClass}`} />
                {t("fx_watch.rates_updated", { time: ratesUpdatedAgo })}
              </p>
            ) : null}
            <Button
              size="sm"
              variant="ghost"
              className="h-7 px-2 text-xs"
              onClick={handleRefreshRates}
              disabled={refreshMutation.isPending || refreshCooldownRemainingSeconds > 0 || watches.length === 0}
            >
              <RefreshCw className={`mr-1 h-3.5 w-3.5 ${refreshMutation.isPending ? "animate-spin" : ""}`} />
              {refreshMutation.isPending
                ? t("fx_watch.action.refreshing")
                : refreshCooldownRemainingSeconds > 0
                  ? t("fx_watch.action.refresh_cooldown", { seconds: refreshCooldownRemainingSeconds })
                  : t("fx_watch.action.refresh")}
            </Button>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2 flex-wrap">
          <Button
            size="sm"
            variant="outline"
            className="min-h-[44px]"
            onClick={handleCheck}
            disabled={checkMutation.isPending || watches.length === 0}
          >
            {checkMutation.isPending ? t("fx_watch.action.analyzing") : t("fx_watch.action.check")}
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="min-h-[44px]"
            onClick={handleAlert}
            disabled={alertMutation.isPending || watches.length === 0}
          >
            {alertMutation.isPending ? t("fx_watch.action.sending") : t("fx_watch.action.alert")}
          </Button>
          <Button size="sm" className="min-h-[44px]" onClick={() => setDialogOpen(true)}>
            {t("fx_watch.action.add")}
          </Button>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as "overview" | "watches" | "exposure")}>
        <TabsList className="flex-wrap h-auto min-h-[44px] gap-1">
          <TabsTrigger value="overview" className="min-h-[44px]">
            {t("fx_watch.tab.overview")}
          </TabsTrigger>
          <TabsTrigger value="watches" className="min-h-[44px]">
            {t("fx_watch.tab.watches")}
          </TabsTrigger>
          <TabsTrigger value="exposure" className="min-h-[44px]">
            {t("fx_watch.tab.exposure")}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-4 space-y-4">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <SummaryCard label={t("fx_watch.metric.total")} value={String(watches.length)} />
            <SummaryCard label={t("fx_watch.metric.active")} value={String(activeCount)} />
            <SummaryCard
              label={t("fx_watch.metric.alerts")}
              value={String(alertCount)}
              highlight={alertCount > 0}
            />
            <SummaryCard
              label={t("fx_watch.metric.last_alert")}
              value={lastAlert ?? t("fx_watch.metric.not_sent")}
              small
            />
          </div>

          {exposure ? (
            <PortfolioImpactSnapshot exposure={exposure} privacyMode={privacyMode} />
          ) : (
            <div className="rounded-md border border-border p-3">
              <p className="text-sm font-semibold">{t("fx_watch.overview.portfolio_impact")}</p>
              <p className="mt-2 text-xs text-muted-foreground">{t("common.loading")}</p>
            </div>
          )}
        </TabsContent>

        <TabsContent value="watches" className="mt-4 space-y-3">
          {watches.length === 0 ? (
            <div className="space-y-1 py-4">
              <p className="text-sm text-muted-foreground">{t("fx_watch.empty.message")}</p>
              <p className="text-xs text-muted-foreground">{t("fx_watch.empty.hint")}</p>
            </div>
          ) : (
            <>
              <div className="flex items-center gap-2 flex-wrap">
                <div className="flex rounded-md border border-border overflow-hidden">
                  <button
                    onClick={() => setFilterMode("all")}
                    className={`px-3 py-1 text-xs min-h-[44px] transition-colors ${
                      filterMode === "all"
                        ? "bg-primary text-primary-foreground"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {t("fx_watch.filter.all")}
                  </button>
                  <button
                    onClick={() => setFilterMode("active_only")}
                    className={`px-3 py-1 text-xs min-h-[44px] border-l border-border transition-colors ${
                      filterMode === "active_only"
                        ? "bg-primary text-primary-foreground"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {t("fx_watch.filter.active_only")}
                  </button>
                </div>

                <Select value={sortMode} onValueChange={(v) => setSortMode(v as SortMode)}>
                  <SelectTrigger className="w-36 text-xs min-h-[44px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="alert_first" className="text-xs">
                      {t("fx_watch.sort.alert_first")}
                    </SelectItem>
                    <SelectItem value="alphabetical" className="text-xs">
                      {t("fx_watch.sort.alphabetical")}
                    </SelectItem>
                    <SelectItem value="volatility" className="text-xs">
                      {t("fx_watch.sort.volatility")}
                    </SelectItem>
                  </SelectContent>
                </Select>

                <span className="text-xs text-muted-foreground">
                  {t("fx_watch.list.title")} ({sortedWatches.length})
                </span>
              </div>

              {sortedWatches.map((watch: FxWatch) => {
                const pair = `${watch.base_currency}/${watch.quote_currency}`
                return (
                  <WatchCard
                    key={watch.id}
                    watch={watch}
                    analysis={analysisMap[watch.id]}
                    analysisLoading={analysisLoading}
                    sparklineData={historyMap[pair]}
                  />
                )
              })}
            </>
          )}
        </TabsContent>

        <TabsContent value="exposure" className="mt-4">
          {profile ? (
            <CurrencyExposure privacyMode={privacyMode} profile={profile} enabled={activeTab === "exposure"} />
          ) : (
            <p className="text-sm text-muted-foreground">{t("common.loading")}</p>
          )}
        </TabsContent>
      </Tabs>

      <AddWatchDialog open={dialogOpen} onClose={() => setDialogOpen(false)} />
    </div>
  )
}

interface SummaryCardProps {
  label: string
  value: string
  highlight?: boolean
  small?: boolean
}

function SummaryCard({ label, value, highlight = false, small = false }: SummaryCardProps) {
  return (
    <div className="rounded-lg border border-border p-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p
        className={`${small ? "text-sm font-semibold truncate" : "text-2xl font-bold"} ${
          highlight ? "text-destructive" : ""
        }`}
      >
        {value}
      </p>
    </div>
  )
}
