import { useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { Info, SearchX } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { useEligibleAssets } from "@/api/hooks/useWrappers"

type WrapperTab = "nisa_tsumitate" | "nisa_growth"
type AssetTypeFilter = "all" | "mutual_fund" | "etf" | "stock" | "reit"

function AssetTable({
  rows,
  loading,
  assetTypeFilter,
  onAssetTypeChange,
  totalUnfilteredCount,
  hasSearchQuery,
  onClearSearch,
}: {
  rows: Array<{
    ticker: string
    fund_name: string
    asset_type: string
    trust_fee_pct?: number | null
  }>
  loading: boolean
  assetTypeFilter: AssetTypeFilter
  onAssetTypeChange: (value: AssetTypeFilter) => void
  totalUnfilteredCount: number
  hasSearchQuery: boolean
  onClearSearch: () => void
}) {
  const { t } = useTranslation()
  const getAssetTypeLabel = (assetType: string): string => {
    switch (assetType) {
      case "mutual_fund":
      case "etf":
      case "stock":
      case "reit":
        return t(`nisa.eligible.asset_type.${assetType}`)
      default:
        return assetType
    }
  }
  const filteredRows = useMemo(() => {
    if (assetTypeFilter === "all") return rows
    return rows.filter((row) => row.asset_type === assetTypeFilter)
  }, [assetTypeFilter, rows])
  const showNoMatchState = totalUnfilteredCount > 0 || hasSearchQuery

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <label htmlFor="asset-type-filter" className="text-xs text-muted-foreground">
          {t("nisa.eligible.filter_asset_type")}
        </label>
        <select
          id="asset-type-filter"
          value={assetTypeFilter}
          onChange={(e) => onAssetTypeChange(e.target.value as AssetTypeFilter)}
          className="text-xs border border-border rounded px-2 py-2 min-h-[36px] bg-background"
        >
          <option value="all">{t("nisa.eligible.filter_all")}</option>
          <option value="mutual_fund">{t("nisa.eligible.asset_type.mutual_fund")}</option>
          <option value="etf">{t("nisa.eligible.asset_type.etf")}</option>
          <option value="stock">{t("nisa.eligible.asset_type.stock")}</option>
          <option value="reit">{t("nisa.eligible.asset_type.reit")}</option>
        </select>
      </div>

      <div className="rounded-md border border-border overflow-x-auto">
        <table className="w-full min-w-[720px] text-sm">
          <thead className="bg-muted/40">
            <tr className="text-left">
              <th className="px-3 py-2 font-medium">{t("nisa.eligible.table_fund_name")}</th>
              <th className="px-3 py-2 font-medium">{t("nisa.eligible.table_ticker")}</th>
              <th className="px-3 py-2 font-medium">{t("nisa.eligible.table_asset_type")}</th>
              <th className="px-3 py-2 font-medium">
                <span className="inline-flex items-center gap-1">
                  {t("nisa.eligible.table_trust_fee")}
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <button type="button" className="inline-flex text-muted-foreground">
                          <Info className="h-3.5 w-3.5" />
                        </button>
                      </TooltipTrigger>
                      <TooltipContent className="max-w-64 text-xs">
                        {t("nisa.eligible.trust_fee_help")}
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </span>
              </th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 8 }).map((_, index) => (
                <tr key={`skeleton-${index}`} className="border-t border-border">
                  <td className="px-3 py-2" colSpan={4}>
                    <Skeleton className="h-4 w-full" />
                  </td>
                </tr>
              ))
            ) : filteredRows.length > 0 ? (
              filteredRows.map((item) => (
                <tr key={`${item.ticker}-${item.fund_name}`} className="border-t border-border">
                  <td className="px-3 py-2">{item.fund_name || "—"}</td>
                  <td className="px-3 py-2 font-mono text-xs">{item.ticker}</td>
                  <td className="px-3 py-2">
                    <Badge variant="outline">{getAssetTypeLabel(item.asset_type)}</Badge>
                  </td>
                  <td className="px-3 py-2">
                    {item.trust_fee_pct != null
                      ? `${item.trust_fee_pct.toFixed(4)}%`
                      : t("nisa.eligible.trust_fee_unknown")}
                  </td>
                </tr>
              ))
            ) : (
              <tr className="border-t border-border">
                <td className="px-3 py-8" colSpan={4}>
                  <div className="flex flex-col items-center justify-center gap-3 text-center">
                    <div className="rounded-full bg-muted p-3">
                      <SearchX className="h-5 w-5 text-muted-foreground" />
                    </div>
                    {showNoMatchState ? (
                      <div className="space-y-1">
                        <p className="text-sm font-semibold">{t("nisa.eligible.filter_no_match_title")}</p>
                        <p className="text-xs text-muted-foreground">{t("nisa.eligible.filter_no_match")}</p>
                      </div>
                    ) : (
                      <div className="space-y-1">
                        <p className="text-sm font-semibold">{t("nisa.eligible.empty_title")}</p>
                        <p className="text-xs text-muted-foreground">{t("nisa.eligible.empty")}</p>
                      </div>
                    )}
                    {totalUnfilteredCount > 0 && assetTypeFilter !== "all" ? (
                      <Button size="sm" variant="outline" onClick={() => onAssetTypeChange("all")}>
                        {t("nisa.eligible.clear_filter")}
                      </Button>
                    ) : hasSearchQuery ? (
                      <Button size="sm" variant="outline" onClick={onClearSearch}>
                        {t("nisa.eligible.clear_search")}
                      </Button>
                    ) : totalUnfilteredCount === 0 ? (
                      <Button asChild size="sm" variant="outline">
                        <Link to="/nisa?tab=data">{t("nisa.eligible.empty_cta")}</Link>
                      </Button>
                    ) : null}
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function EligibleAssetsTab() {
  const { t } = useTranslation()
  const [activeWrapper, setActiveWrapper] = useState<WrapperTab>("nisa_tsumitate")
  const [search, setSearch] = useState("")
  const [limit, setLimit] = useState(50)
  const [assetTypeFilter, setAssetTypeFilter] = useState<AssetTypeFilter>("all")

  const tsumitateQuery = useEligibleAssets("nisa_tsumitate", {
    search,
    limit,
    enabled: activeWrapper === "nisa_tsumitate",
  })
  const growthQuery = useEligibleAssets("nisa_growth", {
    search,
    limit,
    enabled: activeWrapper === "nisa_growth",
  })

  const activeQuery = activeWrapper === "nisa_tsumitate" ? tsumitateQuery : growthQuery
  const loadedCount = activeQuery.data?.items.length ?? 0
  const totalCount = activeQuery.data?.total_count ?? 0
  const canLoadMore = loadedCount < totalCount

  return (
    <div className="space-y-4">
      <div className="space-y-1">
        <h2 className="text-base font-semibold">{t("nisa.eligible.title")}</h2>
        <p className="text-sm text-muted-foreground">{t("nisa.eligible.hint")}</p>
      </div>

      <Input
        value={search}
        onChange={(event) => {
          setSearch(event.target.value)
          setLimit(50)
          setAssetTypeFilter("all")
        }}
        placeholder={t("nisa.eligible.search_placeholder")}
        className="max-w-lg"
      />

      <Tabs
        value={activeWrapper}
        onValueChange={(value) => {
          setActiveWrapper(value as WrapperTab)
          setLimit(50)
          setAssetTypeFilter("all")
        }}
      >
        <TabsList className="min-h-[44px] h-auto gap-1">
          <TabsTrigger value="nisa_tsumitate" className="min-h-[44px] gap-2">
            {t("wrapper.nisa_tsumitate")}
            <Badge variant="secondary">{tsumitateQuery.data?.total_count ?? 0}</Badge>
          </TabsTrigger>
          <TabsTrigger value="nisa_growth" className="min-h-[44px] gap-2">
            {t("wrapper.nisa_growth")}
            <Badge variant="secondary">{growthQuery.data?.total_count ?? 0}</Badge>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="nisa_tsumitate" className="mt-4">
          <AssetTable
            rows={tsumitateQuery.data?.items ?? []}
            loading={tsumitateQuery.isLoading}
            assetTypeFilter={assetTypeFilter}
            onAssetTypeChange={setAssetTypeFilter}
            totalUnfilteredCount={tsumitateQuery.data?.items.length ?? 0}
            hasSearchQuery={search.trim().length > 0}
            onClearSearch={() => {
              setSearch("")
              setLimit(50)
            }}
          />
        </TabsContent>

        <TabsContent value="nisa_growth" className="mt-4">
          <AssetTable
            rows={growthQuery.data?.items ?? []}
            loading={growthQuery.isLoading}
            assetTypeFilter={assetTypeFilter}
            onAssetTypeChange={setAssetTypeFilter}
            totalUnfilteredCount={growthQuery.data?.items.length ?? 0}
            hasSearchQuery={search.trim().length > 0}
            onClearSearch={() => {
              setSearch("")
              setLimit(50)
            }}
          />
        </TabsContent>
      </Tabs>

      <div className="flex items-center justify-between gap-2">
        <p className="text-xs text-muted-foreground">
          {t("nisa.eligible.showing_count", {
            count: loadedCount,
            total: totalCount,
          })}
        </p>
        <Button
          size="sm"
          variant="outline"
          disabled={!canLoadMore || activeQuery.isFetching}
          onClick={() => setLimit((prev) => prev + 50)}
        >
          {t("nisa.eligible.load_more")}
        </Button>
      </div>
    </div>
  )
}
