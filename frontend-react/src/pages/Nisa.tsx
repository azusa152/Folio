import { useCallback, useMemo, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { useSearchParams } from "react-router-dom"
import { ChevronDown, RefreshCw } from "lucide-react"
import { toast } from "sonner"
import { useAccounts } from "@/api/hooks/useAccounts"
import { useAllocRebalance } from "@/api/hooks/useAllocation"
import { getPreferredWrapperAccountMap, isJapaneseWrapperAccount } from "@/lib/wrapperAccounts"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { AddTransactionSheet } from "@/components/allocation/transactions/AddTransactionSheet"
import type { TransactionType } from "@/components/allocation/transactions/AddTransactionSheet"
import { SmartActionCards } from "@/components/allocation/wrappers/SmartActionCards"
import { AssetLocationViz } from "@/components/allocation/wrappers/AssetLocationViz"
import { TsumitateMigrationCard } from "@/components/allocation/wrappers/TsumitateMigrationCard"
import { QuotaDashboard } from "@/components/allocation/wrappers/QuotaDashboard"
import { EligibleAssetsTab } from "@/components/nisa/EligibleAssetsTab"
import { DataManagementTab } from "@/components/nisa/DataManagementTab"
import { ContributionsTab } from "@/components/nisa/ContributionsTab"
import { NisaEducationCard } from "@/components/nisa/NisaEducationCard"
import { NisaOnboardingBanner } from "@/components/nisa/NisaOnboardingBanner"
import { useEligibleAssetsMetadata, useSyncNav } from "@/api/hooks/useWrappers"

const NAV_SYNC_COOLDOWN_SECONDS = 60
const NISA_ACTIONS_DISPLAY_CURRENCY = "JPY"

type NisaTab = "eligible" | "quota" | "contributions" | "actions" | "data"

export default function Nisa() {
  const { t } = useTranslation()
  const [searchParams, setSearchParams] = useSearchParams()
  const tabParam = searchParams.get("tab")
  const activeTab: NisaTab =
    tabParam === "quota" || tabParam === "contributions" || tabParam === "actions" || tabParam === "data"
      ? tabParam
      : "eligible"

  const { data: accounts } = useAccounts()
  const hasJapaneseWrapperAccounts = useMemo(
    () => (accounts ?? []).some((account) => isJapaneseWrapperAccount(account)),
    [accounts],
  )
  const rebalanceQuery = useAllocRebalance(
    NISA_ACTIONS_DISPLAY_CURRENCY,
    activeTab === "actions" && hasJapaneseWrapperAccounts,
  )
  const tsumitateMetaQuery = useEligibleAssetsMetadata("nisa_tsumitate")
  const growthMetaQuery = useEligibleAssetsMetadata("nisa_growth")
  const syncNavMutation = useSyncNav()
  const [cooldownUntil, setCooldownUntil] = useState(0)
  const [cooldownRemaining, setCooldownRemaining] = useState(0)
  const [transactionSheetOpen, setTransactionSheetOpen] = useState(false)
  const [transactionDefaultTicker, setTransactionDefaultTicker] = useState<string | undefined>(undefined)
  const [transactionDefaultAccountId, setTransactionDefaultAccountId] = useState<number | undefined>(undefined)
  const [transactionDefaultType, setTransactionDefaultType] = useState<TransactionType | undefined>(undefined)
  const [transactionDefaultCurrency, setTransactionDefaultCurrency] = useState<string | undefined>(undefined)
  const [sopOpen, setSopOpen] = useState(false)

  const accountByWrapper = useMemo(
    () => getPreferredWrapperAccountMap(accounts),
    [accounts],
  )

  const openTransactionSheet = useCallback((options?: {
    ticker?: string
    accountId?: number
    transactionType?: TransactionType
    currency?: string
  }) => {
    setTransactionDefaultTicker(options?.ticker)
    setTransactionDefaultAccountId(options?.accountId)
    setTransactionDefaultType(options?.transactionType)
    setTransactionDefaultCurrency(options?.currency)
    setTransactionSheetOpen(true)
  }, [])

  useEffect(() => {
    if (cooldownUntil <= 0) return
    const timer = window.setInterval(() => {
      const remaining = Math.max(0, cooldownUntil - Math.floor(Date.now() / 1000))
      setCooldownRemaining(remaining)
      if (remaining === 0) {
        setCooldownUntil(0)
        window.clearInterval(timer)
      }
    }, 1000)
    return () => window.clearInterval(timer)
  }, [cooldownUntil])

  const handleSyncNav = () => {
    syncNavMutation.mutate(undefined, {
      onSuccess: (data) => {
        const preRefreshNote =
          data.pre_refresh && !data.pre_refresh.success
            ? ` ${t("nisa.nav_sync.pre_refresh_skipped")}`
            : ""
        if (data.failed > 0) {
          const detailPreview = data.failed_details
            .slice(0, 3)
            .map(
              (item) =>
                `${item.ticker}(${t(`nisa.nav_sync.reason_${item.reason}`, { defaultValue: item.reason })})`,
            )
            .join(", ")
          toast.warning(
            t("nisa.nav_sync.partial", {
              synced: data.synced,
              failed: data.failed,
              details: detailPreview,
            }) + preRefreshNote,
          )
        } else {
          toast.success(
            t("nisa.nav_sync.success", { synced: data.synced, failed: data.failed }) +
              preRefreshNote,
          )
        }
        setCooldownRemaining(NAV_SYNC_COOLDOWN_SECONDS)
        setCooldownUntil(Math.floor(Date.now() / 1000) + NAV_SYNC_COOLDOWN_SECONDS)
      },
      onError: () => {
        toast.error(t("nisa.nav_sync.failed"))
      },
    })
  }

  const setActiveTab = (tab: string) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      if (tab === "eligible") next.delete("tab")
      else next.set("tab", tab)
      return next
    })
  }

  return (
    <div className="p-3 sm:p-6 space-y-4">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold">{t("nisa.title")}</h1>
        <p className="text-sm text-muted-foreground">{t("nisa.caption")}</p>
        <div className="mt-1 flex items-center justify-between gap-2">
          <p className="text-xs text-muted-foreground">
            {t("eligibility.last_updated_compact", {
              tsumitate: tsumitateMetaQuery.data?.last_refreshed_at
                ? new Date(tsumitateMetaQuery.data.last_refreshed_at).toLocaleDateString()
                : "—",
              growth: growthMetaQuery.data?.last_refreshed_at
                ? new Date(growthMetaQuery.data.last_refreshed_at).toLocaleDateString()
                : "—",
            })}
          </p>
          <Button
            size="sm"
            variant="ghost"
            className="h-7 px-2 text-xs"
            onClick={handleSyncNav}
            disabled={syncNavMutation.isPending || cooldownRemaining > 0}
          >
            <RefreshCw className={`mr-1 h-3.5 w-3.5 ${syncNavMutation.isPending ? "animate-spin" : ""}`} />
            {syncNavMutation.isPending
              ? t("nisa.nav_sync.syncing")
              : cooldownRemaining > 0
                ? t("nisa.nav_sync.cooldown", { seconds: cooldownRemaining })
                : t("nisa.nav_sync.button")}
          </Button>
        </div>
      </div>

      <div id="nisa-sop" className="rounded-md border border-border">
        <button
          onClick={() => setSopOpen((value) => !value)}
          aria-expanded={sopOpen}
          className="w-full text-left px-4 py-2 text-sm font-medium min-h-[44px] hover:bg-muted/30 transition-colors flex items-center justify-between"
        >
          <span>{t("nisa.sop.title")}</span>
          <ChevronDown
            className={cn(
              "h-4 w-4 text-muted-foreground transition-transform duration-200",
              sopOpen && "rotate-180",
            )}
          />
        </button>
        {sopOpen ? (
          <div className="px-4 pb-4">
            <div className="prose prose-sm dark:prose-invert max-w-none text-xs text-muted-foreground whitespace-pre-wrap">
              {t("nisa.sop.content")}
            </div>
          </div>
        ) : null}
      </div>

      {!hasJapaneseWrapperAccounts ? (
        <NisaOnboardingBanner
          onLearnMore={() => {
            setSopOpen(true)
            document.getElementById("nisa-sop")?.scrollIntoView({ behavior: "smooth", block: "start" })
          }}
        />
      ) : null}

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="flex-wrap h-auto min-h-[44px] gap-1">
          <TabsTrigger value="eligible" className="min-h-[44px]">
            {t("nisa.tabs.eligible")}
          </TabsTrigger>
          <TabsTrigger value="quota" className="min-h-[44px]">
            {t("nisa.tabs.quota")}
          </TabsTrigger>
          <TabsTrigger value="contributions" className="min-h-[44px]">
            {t("nisa.tabs.contributions")}
          </TabsTrigger>
          <TabsTrigger value="actions" className="min-h-[44px]">
            {t("nisa.tabs.actions")}
          </TabsTrigger>
          <TabsTrigger value="data" className="min-h-[44px]">
            {t("nisa.tabs.data")}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="eligible" className="mt-4">
          <EligibleAssetsTab />
        </TabsContent>

        <TabsContent value="quota" className="mt-4 space-y-4">
          <div className="space-y-4">
            <QuotaDashboard enabled={activeTab === "quota"} />
            <NisaEducationCard />
          </div>
        </TabsContent>

        <TabsContent value="contributions" className="mt-4">
          <ContributionsTab />
        </TabsContent>

        <TabsContent value="actions" className="mt-4 space-y-4">
          <SmartActionCards
            enabled={activeTab === "actions"}
            forceHideActions={!hasJapaneseWrapperAccounts}
            emptyHintKey="nisa.actions.empty"
            onApplyRouting={(ticker, accountId, currency) =>
              openTransactionSheet({
                ticker,
                accountId,
                currency,
                transactionType: "BUY",
              })}
            onReviewDetax={(accountId, currency) =>
              openTransactionSheet({
                accountId,
                currency,
                transactionType: "SELL",
              })}
          />

          {hasJapaneseWrapperAccounts && (rebalanceQuery.data?.wrapper_allocations?.length ?? 0) > 0 ? (
            <>
              <AssetLocationViz
                taxEfficiencyScore={rebalanceQuery.data?.tax_efficiency_score}
                wrapperAllocations={rebalanceQuery.data?.wrapper_allocations}
                placementSuggestions={rebalanceQuery.data?.placement_suggestions}
                taxSavingsEstimate={rebalanceQuery.data?.tax_savings_estimate}
                onExecuteSuggestion={(ticker, targetWrapper) => {
                  const target = accountByWrapper.get(targetWrapper)
                  if (!target) return
                  openTransactionSheet({
                    ticker,
                    accountId: target.id,
                    currency: target.currency,
                    transactionType: "BUY",
                  })
                }}
              />
              <TsumitateMigrationCard
                migration={rebalanceQuery.data?.tsumitate_migration}
                onSetup={(tickers) => {
                  const target = accountByWrapper.get("nisa_tsumitate")
                  if (!target || tickers.length === 0) return
                  openTransactionSheet({
                    ticker: tickers[0],
                    accountId: target.id,
                    currency: target.currency,
                    transactionType: "BUY",
                  })
                }}
              />
            </>
          ) : null}
        </TabsContent>

        <TabsContent value="data" className="mt-4">
          <DataManagementTab />
        </TabsContent>
      </Tabs>

      {transactionSheetOpen ? (
        <AddTransactionSheet
          key={`${transactionSheetOpen ? "open" : "closed"}-${transactionDefaultTicker ?? "all"}-${transactionDefaultAccountId ?? "na"}-${transactionDefaultType ?? "BUY"}-${transactionDefaultCurrency ?? "USD"}`}
          open={transactionSheetOpen}
          onClose={() => setTransactionSheetOpen(false)}
          defaultTicker={transactionDefaultTicker}
          defaultAccountId={transactionDefaultAccountId}
          defaultTransactionType={transactionDefaultType}
          defaultCurrency={transactionDefaultCurrency}
        />
      ) : null}
    </div>
  )
}
