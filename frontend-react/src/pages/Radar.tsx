import { useMemo, useState } from "react"
import { ChevronDown } from "lucide-react"
import { useTranslation } from "react-i18next"
import { useSearchParams } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { cn, formatLocalTime } from "@/lib/utils"
import { HOLDING_QUANTITY_EPSILON } from "@/lib/constants"
import { useLocalStorage } from "@/hooks/useLocalStorage"
import { Skeleton } from "@/components/ui/skeleton"
import { FINANCE_TEXT } from "@/lib/colors"
import { useLastScan, useHoldings } from "@/api/hooks/useDashboard"
import {
  useRadarStocks,
  useRadarEnrichedStocks,
  useRemovedStocks,
  useScanStatus,
  useScanCompletionEffect,
  useResonance,
} from "@/api/hooks/useRadar"
import { CategoryTabs } from "@/components/radar/CategoryTabs"
import { AddStockDrawer } from "@/components/radar/AddStockDrawer"
import { RadarFilterPanel } from "@/components/radar/RadarFilterPanel"
import type { RadarEnrichedStock } from "@/api/types/radar"
import { filterStocks, useRadarFilters } from "@/hooks/useRadarFilters"
import type { StockCategory } from "@/api/types/radar"

const RADAR_TAB_VALUES = ["Trend_Setter", "Moat", "Growth", "Mutual_Fund", "Bond", "Crypto", "archive"] as const

export default function Radar() {
  const { t } = useTranslation()
  const [searchParams, setSearchParams] = useSearchParams()
  const [sopOpen, setSopOpen] = useState(false)
  const [showFullSop, setShowFullSop] = useState(false)
  const [helpDismissed, setHelpDismissed] = useLocalStorage("radar_first_visit_help_dismissed", false)
  const [filterOpen, setFilterOpen] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const {
    filters,
    setFilter,
    toggleSignal,
    toggleSector,
    toggleTag,
    toggleMarketCapBucket,
    resetFilters,
    applyPreset,
    activeFilterCount,
  } = useRadarFilters()

  const { data: stocks, isLoading: stocksLoading, isError: stocksError } = useRadarStocks()
  const { data: enrichedStocks } = useRadarEnrichedStocks()
  const { data: removedStocks } = useRemovedStocks()
  const { data: lastScan } = useLastScan()
  const { data: scanStatus } = useScanStatus()
  const { data: resonanceMap } = useResonance()
  const { data: holdings } = useHoldings()
  useScanCompletionEffect()

  const isScanning = scanStatus?.is_running ?? false
  const categoryParam = searchParams.get("category")
  const activeCategory = RADAR_TAB_VALUES.includes(categoryParam as (typeof RADAR_TAB_VALUES)[number])
    ? (categoryParam as (typeof RADAR_TAB_VALUES)[number])
    : "Trend_Setter"

  // Build enriched map: ticker → enriched data
  const enrichedMap = useMemo(() => {
    const map: Record<string, RadarEnrichedStock> = {}
    for (const es of enrichedStocks ?? []) {
      if (es.ticker) map[es.ticker] = es
    }
    return map
  }, [enrichedStocks])

  // Build held tickers set from non-cash portfolio holdings for O(1) lookup per card
  const heldTickers = useMemo(
    () =>
      new Set(
        (holdings ?? [])
          .filter((h) => !h.is_cash && h.quantity > HOLDING_QUANTITY_EPSILON)
          .map((h) => h.ticker.toUpperCase()),
      ),
    [holdings],
  )

  const availableSectors = useMemo(() => {
    const sectors = new Set<string>()
    for (const stock of stocks ?? []) {
      const sector = enrichedMap[stock.ticker]?.sector?.trim()
      if (sector) sectors.add(sector)
    }
    return Array.from(sectors).sort((a, b) => a.localeCompare(b))
  }, [stocks, enrichedMap])

  const availableTags = useMemo(() => {
    const tags = new Set<string>()
    for (const stock of stocks ?? []) {
      for (const tag of stock.current_tags ?? []) {
        const trimmed = tag.trim()
        if (trimmed) tags.add(trimmed)
      }
    }
    return Array.from(tags).sort((a, b) => a.localeCompare(b))
  }, [stocks])

  const filteredStocks = useMemo(
    () => filterStocks(stocks ?? [], enrichedMap, heldTickers, filters),
    [stocks, enrichedMap, heldTickers, filters],
  )
  const totalActiveCount = useMemo(() => (stocks ?? []).filter((s) => s.is_active).length, [stocks])
  const filteredActiveCount = useMemo(
    () => filteredStocks.filter((s) => s.is_active).length,
    [filteredStocks],
  )

  if (stocksLoading) {
    return (
      <div className="p-3 sm:p-6 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <Skeleton className="h-8 w-48" />
            <Skeleton className="mt-1 h-4 w-64" />
          </div>
          <Skeleton className="h-9 w-28" />
        </div>
        <Skeleton className="h-10 w-full" />
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-16 w-full rounded-lg" />
        ))}
      </div>
    )
  }

  if (stocksError || !stocks) {
    return (
      <div className="p-3 sm:p-6 space-y-3">
        <h1 className="text-xl sm:text-2xl font-bold">{t("radar.title")}</h1>
        <p className="text-sm text-destructive">{t("radar.loading.error")}</p>
        <p className="text-xs text-muted-foreground">{t("radar.loading.error_hint")}</p>
      </div>
    )
  }

  const scanTs = lastScan?.last_scanned_at
    ? formatLocalTime(lastScan.last_scanned_at)
    : null

  const setActiveCategory = (category: StockCategory | "archive") => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      if (category === "Trend_Setter") next.delete("category")
      else next.set("category", category)
      return next
    })
  }

  return (
    <div className="p-3 sm:p-6 space-y-4">
      {/* Header row */}
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="flex-1">
          <h1 className="text-xl sm:text-2xl font-bold">{t("radar.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("radar.caption")}</p>
        </div>
        <div className="flex items-center gap-2">
          {isScanning && (
            <span aria-live="polite" role="status" className={`text-xs ${FINANCE_TEXT.warning} animate-pulse`}>
              {t("radar.scan.running")}
            </span>
          )}
          <Button size="sm" variant="outline" className="min-h-[44px]" onClick={() => setDrawerOpen(true)}>
            {t("radar.panel_header")}
          </Button>
        </div>
      </div>

      {/* SOP collapsible */}
      {!helpDismissed && (
        <div className="rounded-md border border-border bg-muted/20 px-4 py-3">
          <p className="text-sm font-medium">{t("radar.first_visit.title")}</p>
          <p className="mt-1 text-xs text-muted-foreground">{t("radar.first_visit.description")}</p>
          <ol className="mt-2 space-y-1 text-xs text-muted-foreground list-decimal pl-4">
            <li>{t("radar.first_visit.step_1")}</li>
            <li>{t("radar.first_visit.step_2")}</li>
            <li>{t("radar.first_visit.step_3")}</li>
          </ol>
          <div className="mt-3 flex flex-wrap gap-2">
            <Button size="sm" variant="outline" onClick={() => setSopOpen(true)}>
              {t("radar.first_visit.learn_more")}
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setHelpDismissed(true)}>
              {t("radar.first_visit.dismiss")}
            </Button>
          </div>
        </div>
      )}

      <div className="rounded-md border border-border">
        <button
          onClick={() => setSopOpen((v) => !v)}
          aria-expanded={sopOpen}
          className="w-full text-left px-4 py-2 text-sm font-medium min-h-[44px] hover:bg-muted/30 transition-colors flex items-center justify-between"
        >
          <span>{t("radar.sop.learn_more_title")}</span>
          <ChevronDown className={cn("h-4 w-4 text-muted-foreground transition-transform duration-200", sopOpen && "rotate-180")} />
        </button>
        {sopOpen && (
          <div className="px-4 pb-4">
            <p className="text-xs font-medium">{t("radar.sop.quick_title")}</p>
            <ol className="mt-2 space-y-1 text-xs text-muted-foreground list-decimal pl-4">
              <li>{t("radar.first_visit.step_1")}</li>
              <li>{t("radar.first_visit.step_2")}</li>
              <li>{t("radar.first_visit.step_3")}</li>
            </ol>
            <div className="mt-3">
              <Button
                size="sm"
                variant="outline"
                onClick={() => setShowFullSop((v) => !v)}
              >
                {showFullSop ? t("radar.sop.hide_full") : t("radar.sop.show_full")}
              </Button>
            </div>
            {showFullSop && (
              <>
                <div className="mt-3 prose prose-sm dark:prose-invert max-w-none text-xs text-muted-foreground whitespace-pre-wrap">
                  {t("radar.sop.content")}
                </div>
                <p className="mt-2 text-xs text-muted-foreground">
                  {t("radar.fundamentals_note")}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {t("radar.pwa_note")}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {t("radar.filter.note")}
                </p>
              </>
            )}
          </div>
        )}
      </div>

      <RadarFilterPanel
        isOpen={filterOpen}
        onToggleOpen={() => setFilterOpen((v) => !v)}
        filters={filters}
        activeFilterCount={activeFilterCount}
        availableSectors={availableSectors}
        availableTags={availableTags}
        setFilter={setFilter}
        toggleSignal={toggleSignal}
        toggleSector={toggleSector}
        toggleTag={toggleTag}
        toggleMarketCapBucket={toggleMarketCapBucket}
        resetFilters={resetFilters}
        applyPreset={applyPreset}
      />

      {/* Data freshness */}
      <p className="text-xs text-muted-foreground -mt-2">
        {scanTs
          ? t("radar.last_scan_time", { time: scanTs })
          : t("radar.no_scan_yet")}
        {" · "}
        {activeFilterCount > 0
          ? t("radar.filter.showing_filtered", { filtered: filteredActiveCount, total: totalActiveCount })
          : t("radar.loading.success", { count: totalActiveCount })}
      </p>

      {/* Category tabs */}
      <CategoryTabs
        stocks={filteredStocks}
        totalStocks={stocks}
        hasActiveFilters={activeFilterCount > 0}
        removedStocks={removedStocks ?? []}
        enrichedMap={enrichedMap}
        resonanceMap={resonanceMap ?? {}}
        heldTickers={heldTickers}
        activeCategory={activeCategory}
        onCategoryChange={setActiveCategory}
      />

      {/* Control panel drawer */}
      <AddStockDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        isScanning={isScanning}
      />
    </div>
  )
}
