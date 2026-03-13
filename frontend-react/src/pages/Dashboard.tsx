import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { ChevronDown, ChevronUp, SendHorizonal } from "lucide-react"
import { isMarketOpen } from "@/lib/format"
import { FINANCE_TEXT } from "@/lib/colors"
import { formatLocalTime, formatRelativeTime, getErrorMessage } from "@/lib/utils"
import {
  useStocks,
  useEnrichedStocks,
  useLastScan,
  useHoldings,
  useRebalance,
  useProfile,
  useSignalActivity,
  useFearGreed,
  useSnapshots,
  useTwr,
  useGreatMinds,
} from "@/api/hooks/useDashboard"
import { useAccountSummary } from "@/api/hooks/useAccounts"
import { useScanCompletionEffect } from "@/api/hooks/useRadar"
import { useTriggerDigest } from "@/api/hooks/useAllocation"
import { useLocalStorage } from "@/hooks/useLocalStorage"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Card, CardContent } from "@/components/ui/card"
import { EmptyState } from "@/components/EmptyState"
import { LazySection } from "@/components/LazySection"
import { PortfolioPulse } from "@/components/dashboard/PortfolioPulse"
import { PerformanceChart } from "@/components/dashboard/PerformanceChart"
import { SignalAlerts } from "@/components/dashboard/SignalAlerts"
import { AllocationGlance } from "@/components/dashboard/AllocationGlance"
import { TopHoldings } from "@/components/dashboard/TopHoldings"
import { DividendIncome } from "@/components/dashboard/DividendIncome"
import { ResonanceSummary } from "@/components/dashboard/ResonanceSummary"
import { StockHeatmap } from "@/components/dashboard/StockHeatmap"
import { AccountsOverview } from "@/components/dashboard/AccountsOverview"
import { SectorAllocationCard } from "@/components/dashboard/SectorAllocationCard"
import { HoldingBreakdown } from "@/components/dashboard/HoldingBreakdown"

const DISPLAY_CURRENCY_OPTIONS = ["USD", "TWD", "JPY", "HKD"]

export default function Dashboard() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const [displayCurrency, setDisplayCurrency] = useState("USD")
  const [showAdvanced, setShowAdvanced] = useLocalStorage("dashboard_advanced", false)
  const digestMutation = useTriggerDigest()
  const [nowEpochSeconds, setNowEpochSeconds] = useState(() => Math.floor(Date.now() / 1000))

  useEffect(() => {
    const updateNow = () => setNowEpochSeconds(Math.floor(Date.now() / 1000))
    const timer = window.setInterval(updateNow, 60_000)
    return () => window.clearInterval(timer)
  }, [])

  const handleDigest = () => {
    digestMutation.mutate(undefined, {
      onSuccess: () => toast.success(t("common.success")),
      onError: (err: unknown) => toast.error(getErrorMessage(err) || t("common.error")),
    })
  }

  // Fast (DB-only) queries — fired immediately on mount.
  const { data: stocks, isLoading: stocksLoading, isError: stocksError } = useStocks()
  const { data: holdings } = useHoldings()
  const { data: lastScan } = useLastScan()
  const {
    data: accountSummary,
    isLoading: accountSummaryLoading,
    isError: accountSummaryError,
  } = useAccountSummary()
  const { data: signalActivity } = useSignalActivity()
  const { data: snapshots, isLoading: snapshotsLoading } = useSnapshots(730)
  const { data: twr } = useTwr()
  const { data: profile } = useProfile()
  useScanCompletionEffect()

  // useRebalance fires immediately (not gated) because heroLoading and PortfolioPulse
  // both depend on it. Its response is cached on the backend (60s TTL) so repeat
  // requests are fast; placeholderData keeps old data visible on currency switch.
  const {
    data: rebalance,
    isLoading: rebalanceLoading,
    isFetching: rebalanceFetching,
    isError: rebalanceError,
  } = useRebalance(displayCurrency)

  // Heavy yfinance queries — gated behind stocksLoading so the fast DB-only
  // requests above can claim FastAPI threadpool workers first.
  // Fear & Greed full payload only loads in advanced mode; the hero gauge can
  // already render from /scan/last fallback fields.
  const { data: enrichedStocks, isLoading: enrichedLoading } = useEnrichedStocks({
    enabled: !stocksLoading,
  })
  const {
    data: fearGreed,
    isFetching: fearGreedFetching,
    isError: fearGreedError,
  } = useFearGreed({
    enabled: !stocksLoading && showAdvanced,
  })
  const { data: greatMinds, isLoading: greatMindsLoading } = useGreatMinds({
    enabled: !stocksLoading,
  })

  const heroLoading = stocksLoading
  const heroError = stocksError
  const heroRefreshing = (rebalanceFetching && !rebalanceLoading) || fearGreedFetching
  const partialDataWarning = rebalanceError || (showAdvanced && fearGreedError)

  if (!heroLoading && heroError) {
    return (
      <div className="p-3 sm:p-6 space-y-4">
        <h1 className="text-xl sm:text-2xl font-bold">{t("dashboard.title")}</h1>
        <EmptyState
          icon="⚠️"
          message={t("common.error_backend")}
          title={t("common.error")}
          description={t("common.error_backend")}
          action={{
            label: t("common.retry"),
            onClick: () => window.location.reload(),
          }}
        />
      </div>
    )
  }

  // Onboarding: no data at all
  if (!stocksLoading && !rebalanceLoading && !stocks?.length && !rebalance) {
    return (
      <div className="p-3 sm:p-6 space-y-4">
        <h1 className="text-xl sm:text-2xl font-bold">{t("dashboard.title")}</h1>
        <EmptyState
          icon="🚀"
          message={t("dashboard.welcome")}
          title={t("dashboard.onboarding_title")}
          description={t("dashboard.onboarding_description")}
          action={{
            label: t("dashboard.onboarding_goto_radar"),
            onClick: () => navigate("/radar"),
          }}
          secondaryAction={{
            label: t("dashboard.onboarding_goto_allocation"),
            onClick: () => navigate("/allocation"),
            variant: "outline",
          }}
        />
      </div>
    )
  }

  // Timestamps
  const priceTs = rebalance?.calculated_at
    ? formatLocalTime(rebalance.calculated_at)
    : null
  const scanTs = lastScan?.last_scanned_at
    ? formatLocalTime(lastScan.last_scanned_at)
    : null
  const scanAgeSeconds = lastScan?.epoch
    ? Math.max(0, nowEpochSeconds - lastScan.epoch)
    : null
  const usMarketOpen = isMarketOpen("US")
  const staleScanThresholdSeconds = usMarketOpen ? 30 * 60 : 18 * 60 * 60
  const isScanStale = scanAgeSeconds !== null && scanAgeSeconds > staleScanThresholdSeconds
  const scanStaleSuffix = isScanStale && scanAgeSeconds !== null
    ? t("dashboard.scan_stale_suffix", {
        relative: formatRelativeTime(scanAgeSeconds, i18n.language),
      })
    : null

  return (
    <div className="p-3 sm:p-6 space-y-6">
      {/* Header row */}
      <div className="flex items-center gap-3 flex-wrap">
        <h1 className="text-xl sm:text-2xl font-bold flex-1">{t("dashboard.title")}</h1>
        <Button
          size="sm"
          variant="outline"
          className="text-xs gap-1.5 min-h-[44px]"
          onClick={handleDigest}
          disabled={digestMutation.isPending}
          title={t("dashboard.digest_tooltip")}
        >
          <SendHorizonal className="w-3.5 h-3.5" />
          {t("dashboard.digest_tooltip")}
        </Button>
        <Select value={displayCurrency} onValueChange={setDisplayCurrency}>
          <SelectTrigger className="w-28 text-xs min-h-[44px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {DISPLAY_CURRENCY_OPTIONS.map((c) => (
              <SelectItem key={c} value={c} className="text-xs">
                {c}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button
          variant="ghost"
          size="sm"
          className="text-xs gap-1.5 min-h-[44px]"
          onClick={() => setShowAdvanced(!showAdvanced)}
        >
          {showAdvanced ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          {showAdvanced ? t("dashboard.hide_advanced") : t("dashboard.show_advanced")}
        </Button>
      </div>

      {/* Timestamps */}
      {(priceTs || scanTs) && (
        <p className="text-xs text-muted-foreground -mt-4">
          {priceTs && <span>{t("dashboard.price_updated", { timestamp: priceTs })}</span>}
          {/* eslint-disable-next-line i18next/no-literal-string */}
          {priceTs && scanTs && <span> ｜ </span>}
          {scanTs && (
            <span className={isScanStale ? `${FINANCE_TEXT.warning} font-medium` : undefined}>
              {t("dashboard.last_scan", { timestamp: scanTs })}
              {!usMarketOpen && (
                <span className="text-muted-foreground font-normal">
                  {" "}
                  {t("dashboard.market_closed")}
                </span>
              )}
              {scanStaleSuffix && ` ${scanStaleSuffix}`}
            </span>
          )}
        </p>
      )}

      {partialDataWarning && (
        <p className={`text-xs -mt-2 ${FINANCE_TEXT.warning}`}>
          {t("common.error_backend")}
        </p>
      )}

      {/* ── Market Pulse ── */}
      <h2 className="text-xs uppercase tracking-wide text-muted-foreground">{t("dashboard.section_market_pulse")}</h2>

      <PortfolioPulse
        rebalance={rebalance}
        fearGreed={fearGreed}
        twr={twr}
        snapshots={snapshots ?? []}
        lastScan={lastScan}
        stocks={stocks ?? []}
        enrichedStocks={enrichedStocks ?? []}
        holdings={holdings ?? []}
        isLoading={heroLoading}
        isRefreshing={heroRefreshing}
      />

      <LazySection fallback={<Card><CardContent className="p-4 sm:p-6"><Skeleton className="h-20 w-full" /></CardContent></Card>}>
        <HoldingBreakdown rebalance={rebalance} isLoading={heroLoading} />
      </LazySection>

      <LazySection fallback={<Card><CardContent className="p-4 sm:p-6"><Skeleton className="h-24 w-full" /></CardContent></Card>}>
        <SignalAlerts
          stocks={stocks ?? []}
          enrichedStocks={enrichedStocks ?? []}
          rebalance={rebalance}
          signalActivity={signalActivity ?? []}
        />
      </LazySection>

      {/* ── Portfolio Overview ── */}
      <h2 className="text-xs uppercase tracking-wide text-muted-foreground">{t("dashboard.section_portfolio_overview")}</h2>

      <AccountsOverview
        accountSummary={accountSummary ?? []}
        rebalance={rebalance}
        displayCurrency={displayCurrency}
        isLoading={accountSummaryLoading && !accountSummary}
        isError={accountSummaryError}
      />

      <LazySection fallback={<Card><CardContent className="p-4 sm:p-6"><Skeleton className="h-[200px] w-full" /></CardContent></Card>}>
        <AllocationGlance rebalance={rebalance} profile={profile} isLoading={heroLoading} />
      </LazySection>

      {showAdvanced && (
        <LazySection fallback={<Card><CardContent className="p-4 sm:p-6"><Skeleton className="h-[200px] w-full" /></CardContent></Card>}>
          <SectorAllocationCard sectorExposure={rebalance?.sector_exposure ?? []} />
        </LazySection>
      )}

      <LazySection fallback={<Card><CardContent className="p-4 sm:p-6"><Skeleton className="h-32 w-full" /></CardContent></Card>}>
        <TopHoldings rebalance={rebalance} />
      </LazySection>

      {showAdvanced && (
        <>
          {/* ── Deep Dive ── */}
          <h2 className="text-xs uppercase tracking-wide text-muted-foreground">{t("dashboard.section_deep_dive")}</h2>

          <StockHeatmap enrichedStocks={enrichedStocks ?? []} isLoading={enrichedLoading} />

          <PerformanceChart snapshots={snapshots ?? []} isLoading={snapshotsLoading} />

          <DividendIncome rebalance={rebalance} enrichedStocks={enrichedStocks ?? []} />

          <LazySection fallback={<Card><CardContent className="p-4 sm:p-6"><Skeleton className="h-24 w-full" /></CardContent></Card>}>
            <ResonanceSummary greatMinds={greatMinds} isLoading={greatMindsLoading} />
          </LazySection>
        </>
      )}
    </div>
  )
}
