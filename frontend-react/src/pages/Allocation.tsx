import { useEffect, useRef, useState } from "react"
import { ChevronDown, ChevronRight, Clock3 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { useSearchParams } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { useAccounts } from "@/api/hooks/useAccounts"
import { useHoldings, useProfile } from "@/api/hooks/useDashboard"
import { usePrivacyMode, maskMoney } from "@/hooks/usePrivacyMode"
import { FINANCE_SURFACE, FINANCE_TEXT } from "@/lib/colors"
import { AddHoldingSheet } from "@/components/allocation/holdings/AddHoldingSheet"
import { RebalanceAnalysis } from "@/components/allocation/analysis/RebalanceAnalysis"
import { CurrencyExposure } from "@/components/allocation/tools/CurrencyExposure"
import { StressTest } from "@/components/allocation/tools/StressTest"
import { SmartWithdrawal } from "@/components/allocation/tools/SmartWithdrawal"
import { TargetAllocation } from "@/components/allocation/tools/TargetAllocation"
import { HoldingsManager } from "@/components/allocation/holdings/HoldingsManager"
import { TelegramSettings } from "@/components/allocation/settings/TelegramSettings"
import { NotificationPreferences } from "@/components/allocation/settings/NotificationPreferences"
import { TerminologySettings } from "@/components/allocation/settings/TerminologySettings"
import { DISPLAY_CURRENCIES } from "@/lib/constants"
import { cn, formatRelativeTime, getErrorMessage } from "@/lib/utils"
import {
  useNetWorthHistory,
  useNetWorthItems,
  useNetWorthSeedPreview,
  useNetWorthSummary,
  useSeedNetWorth,
} from "@/api/hooks/useNetWorth"
import { NetWorthOverview } from "@/components/allocation/networth/NetWorthOverview"
import { NetWorthItemsTable } from "@/components/allocation/networth/NetWorthItemsTable"
import { AddNetWorthItemSheet } from "@/components/allocation/networth/AddNetWorthItemSheet"
import { NetWorthHistoryChart } from "@/components/allocation/networth/NetWorthHistoryChart"
import { AccountsTab } from "@/components/allocation/accounts/AccountsTab"
import { TransactionsTab } from "@/components/allocation/transactions/TransactionsTab"
import { AddTransactionSheet } from "@/components/allocation/transactions/AddTransactionSheet"

type TransactionSheetType = "BUY" | "SELL" | "DIVIDEND" | "DEPOSIT" | "WITHDRAWAL"

export default function Allocation() {
  const { t, i18n } = useTranslation()
  const [searchParams, setSearchParams] = useSearchParams()
  const [sopOpen, setSopOpen] = useState(false)
  const [sheetOpen, setSheetOpen] = useState(false)
  const [nowEpochSeconds, setNowEpochSeconds] = useState(() => Math.floor(Date.now() / 1000))
  const tabParam = searchParams.get("tab")
  const activeTab =
    tabParam === "risk" ||
    tabParam === "actions" ||
    tabParam === "transactions" ||
    tabParam === "accounts" ||
    tabParam === "net-worth" ||
    tabParam === "settings"
      ? tabParam
      : "portfolio"
  const [netWorthSheetOpen, setNetWorthSheetOpen] = useState(false)
  const [netWorthSheetKind, setNetWorthSheetKind] = useState<"asset" | "liability">("asset")
  const [netWorthSopOpen, setNetWorthSopOpen] = useState(false)
  const [netWorthHistoryDays, setNetWorthHistoryDays] = useState<30 | 90 | 180 | 365 | 730>(30)
  const [displayCurrency, setDisplayCurrency] = useState("USD")
  const [riskExpanded, setRiskExpanded] = useState(false)
  const [actionsExpanded, setActionsExpanded] = useState(false)
  const [seedFeedback, setSeedFeedback] = useState("")
  const [transactionSheetOpen, setTransactionSheetOpen] = useState(false)
  const [transactionDefaultTicker, setTransactionDefaultTicker] = useState<string | undefined>(undefined)
  const [transactionDefaultAccountId, setTransactionDefaultAccountId] = useState<number | undefined>(undefined)
  const [transactionDefaultType, setTransactionDefaultType] = useState<TransactionSheetType | undefined>(undefined)
  const [transactionDefaultCurrency, setTransactionDefaultCurrency] = useState<string | undefined>(undefined)
  const netWorthTableRef = useRef<HTMLDivElement>(null)

  const { data: profile, isLoading: profileLoading } = useProfile()
  const { data: holdings, isLoading: holdingsLoading, dataUpdatedAt: holdingsUpdatedAt } = useHoldings()
  const { data: accounts, isLoading: accountsLoading } = useAccounts()
  const { data: netWorthSummary } = useNetWorthSummary(displayCurrency, activeTab === "net-worth")
  const { data: netWorthItems } = useNetWorthItems(displayCurrency, activeTab === "net-worth")
  const { data: netWorthHistory, isLoading: netWorthHistoryLoading } = useNetWorthHistory(
    netWorthHistoryDays,
    displayCurrency,
    activeTab === "net-worth",
  )
  const showNetWorthOnboarding = (netWorthItems?.length ?? 0) === 0
  const { data: netWorthSeedPreview } = useNetWorthSeedPreview(
    displayCurrency,
    activeTab === "net-worth" && showNetWorthOnboarding,
  )
  const seedNetWorth = useSeedNetWorth()
  const privacyMode = usePrivacyMode((s) => s.isPrivate)

  const isLoading = profileLoading || holdingsLoading
  const updatedAgo =
    holdingsUpdatedAt > 0
      ? formatRelativeTime(nowEpochSeconds - Math.floor(holdingsUpdatedAt / 1000), i18n.language)
      : ""

  const setActiveTab = (tab: string) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      if (tab === "portfolio") next.delete("tab")
      else next.set("tab", tab)
      return next
    })
  }

  useEffect(() => {
    const timer = window.setInterval(
      () => setNowEpochSeconds(Math.floor(Date.now() / 1000)),
      60_000,
    )
    return () => window.clearInterval(timer)
  }, [])

  if (isLoading) {
    return (
      <div className="p-3 sm:p-6 space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-80" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    )
  }

  if (!profile || !holdings) {
    return (
      <div className="p-3 sm:p-6 space-y-3">
        <h1 className="text-xl sm:text-2xl font-bold">{t("allocation.title")}</h1>
        <p className="text-sm text-destructive">{t("common.error_backend")}</p>
      </div>
    )
  }

  const hasSetup = holdings.length > 0
  const showQuickStart = !accountsLoading && (accounts?.length ?? 0) === 0
  const hasSeedableCash = (netWorthSeedPreview?.cash_positions?.length ?? 0) > 0

  const formatDisplayCurrency = (value: number) => maskMoney(value, displayCurrency)

  const openTransactionSheet = (options?: {
    ticker?: string
    accountId?: number
    transactionType?: TransactionSheetType
    currency?: string
  }) => {
    setTransactionDefaultTicker(options?.ticker)
    setTransactionDefaultAccountId(options?.accountId)
    setTransactionDefaultType(options?.transactionType)
    setTransactionDefaultCurrency(options?.currency)
    setTransactionSheetOpen(true)
  }

  return (
    <div className="p-3 sm:p-6 space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold">{t("allocation.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("allocation.caption")}</p>
          {updatedAgo ? (
            <p className="text-xs text-muted-foreground inline-flex items-center gap-1 mt-0.5">
              <Clock3 className="h-3.5 w-3.5" />
              {t("common.last_updated_relative", { time: updatedAgo })}
            </p>
          ) : null}
        </div>
        <Button
          size="sm"
          className="text-xs shrink-0 min-h-[44px]"
          onClick={() => setSheetOpen(true)}
        >
          {t("allocation.sidebar.add_holding")}
        </Button>
      </div>

      {/* SOP collapsible */}
      <div className="rounded-md border border-border">
        <button
          onClick={() => setSopOpen((v) => !v)}
          aria-expanded={sopOpen}
          className="w-full text-left px-4 py-2 text-sm font-medium min-h-[44px] hover:bg-muted/30 transition-colors flex items-center justify-between"
        >
          <span>{t("allocation.sop.title")}</span>
          <ChevronDown className={cn("h-4 w-4 text-muted-foreground transition-transform duration-200", sopOpen && "rotate-180")} />
        </button>
        {sopOpen && (
          <div className="px-4 pb-4">
            <div className="prose prose-sm dark:prose-invert max-w-none text-xs text-muted-foreground whitespace-pre-wrap">
              {t("allocation.sop.content")}
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              {t("allocation.sop_csv_note")}
            </p>
          </div>
        )}
      </div>
      {showQuickStart ? (
        <div className="rounded-md border border-border bg-muted/20 p-3">
          <p className="text-xs font-semibold">{t("allocation.quick_start.title")}</p>
          <ol className="mt-2 list-decimal pl-4 space-y-1 text-xs text-muted-foreground">
            <li>{t("allocation.quick_start.step1")}</li>
            <li>{t("allocation.quick_start.step2")}</li>
            <li>{t("allocation.quick_start.step3")}</li>
          </ol>
        </div>
      ) : null}

      {/* Setup guard — show hint when no holdings but still show Settings tab */}
      {!hasSetup && (
        <div className={`rounded-md border px-4 py-3 text-sm ${FINANCE_SURFACE.warning} ${FINANCE_TEXT.warning}`}>
          {t("allocation.setup_required")}
        </div>
      )}

      {/* Main tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="flex-wrap h-auto min-h-[44px] gap-1">
          <TabsTrigger value="portfolio" className="min-h-[44px]">{t("allocation.tab.portfolio")}</TabsTrigger>
          <TabsTrigger value="risk" className="min-h-[44px]">{t("allocation.tab.risk")}</TabsTrigger>
          <TabsTrigger value="actions" className="min-h-[44px]">{t("allocation.tab.actions")}</TabsTrigger>
          <TabsTrigger value="transactions" className="min-h-[44px]">{t("allocation.tab.transactions")}</TabsTrigger>
          <TabsTrigger value="accounts" className="min-h-[44px]">{t("allocation.tab.accounts")}</TabsTrigger>
          <TabsTrigger value="net-worth" className="min-h-[44px]">{t("allocation.tab.net_worth")}</TabsTrigger>
          <TabsTrigger value="settings" className="min-h-[44px]">{t("allocation.tab.settings")}</TabsTrigger>
        </TabsList>

        {/* Portfolio tab */}
        <TabsContent value="portfolio" className="mt-4 space-y-4">
          {/* Display currency selector */}
          <div className="flex items-center gap-2">
            <label htmlFor="alloc-currency" className="text-xs text-muted-foreground">{t("allocation.display_currency")}</label>
            <select
              id="alloc-currency"
              value={displayCurrency}
              onChange={(e) => setDisplayCurrency(e.target.value)}
              className="text-xs border border-border rounded px-3 py-2 min-h-[44px] bg-background"
            >
              {DISPLAY_CURRENCIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
          <RebalanceAnalysis
            displayCurrency={displayCurrency}
            privacyMode={privacyMode}
            enabled={activeTab === "portfolio"}
            onRecordTransaction={(ticker) => openTransactionSheet({ ticker })}
          />
        </TabsContent>

        {/* Risk tab */}
        <TabsContent value="risk" className="mt-4 space-y-6">
          {riskExpanded ? (
            <>
              <CurrencyExposure privacyMode={privacyMode} profile={profile} enabled={activeTab === "risk"} />
              <hr className="border-border" />
              <StressTest displayCurrency={displayCurrency} privacyMode={privacyMode} enabled={activeTab === "risk"} />
              <Button size="sm" variant="ghost" className="text-xs gap-1.5" onClick={() => setRiskExpanded(false)}>
                <ChevronDown className="h-3.5 w-3.5" />
                {t("allocation.tab_teaser.hide_details")}
              </Button>
            </>
          ) : (
            <div className="rounded-md border border-dashed border-border bg-muted/20 p-5 space-y-3">
              <p className="text-sm text-muted-foreground">{t("allocation.tab_teaser.risk_desc")}</p>
              <Button size="sm" variant="outline" className="text-xs gap-1.5" onClick={() => setRiskExpanded(true)}>
                <ChevronRight className="h-3.5 w-3.5" />
                {t("allocation.tab_teaser.show_details")}
              </Button>
            </div>
          )}
        </TabsContent>

        {/* Actions tab */}
        <TabsContent value="actions" className="mt-4 space-y-6">
          {actionsExpanded ? (
            <>
              <SmartWithdrawal privacyMode={privacyMode} />
              <Button size="sm" variant="ghost" className="text-xs gap-1.5" onClick={() => setActionsExpanded(false)}>
                <ChevronDown className="h-3.5 w-3.5" />
                {t("allocation.tab_teaser.hide_details")}
              </Button>
            </>
          ) : (
            <div className="rounded-md border border-dashed border-border bg-muted/20 p-5 space-y-3">
              <p className="text-sm text-muted-foreground">{t("allocation.tab_teaser.actions_desc")}</p>
              <Button size="sm" variant="outline" className="text-xs gap-1.5" onClick={() => setActionsExpanded(true)}>
                <ChevronRight className="h-3.5 w-3.5" />
                {t("allocation.tab_teaser.show_details")}
              </Button>
            </div>
          )}
        </TabsContent>

        {/* Transactions tab */}
        <TabsContent value="transactions" className="mt-4 space-y-4">
          <TransactionsTab
            enabled={activeTab === "transactions"}
            onRecordTransaction={() => openTransactionSheet()}
            onOpenAccounts={() => setActiveTab("accounts")}
          />
        </TabsContent>

        {/* Accounts tab */}
        <TabsContent value="accounts" className="mt-4 space-y-4">
          <AccountsTab
            enabled={activeTab === "accounts"}
            onDepositToAccount={(accountId, currency) =>
              openTransactionSheet({
                accountId,
                transactionType: "DEPOSIT",
                currency,
              })}
          />
        </TabsContent>

        {/* Net Worth tab */}
        <TabsContent value="net-worth" className="mt-4 space-y-4">
          {(netWorthItems?.length ?? 0) > 0 && (netWorthSummary?.stale_count ?? 0) > 0 && (
            <button
              type="button"
              onClick={() => {
                netWorthTableRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })
              }}
              className={`w-full rounded-md border px-3 py-2 text-left text-xs hover:bg-amber-500/20 ${FINANCE_SURFACE.warning} ${FINANCE_TEXT.warning}`}
            >
              {t("net_worth.stale_banner", { count: netWorthSummary?.stale_count ?? 0 })}
            </button>
          )}

          <div className="rounded-md border border-border">
            <button
              onClick={() => setNetWorthSopOpen((v) => !v)}
              aria-expanded={netWorthSopOpen}
              className="w-full text-left px-4 py-2 text-sm font-medium min-h-[44px] hover:bg-muted/30 transition-colors flex items-center justify-between"
            >
              <span>{t("net_worth.title")}</span>
              <ChevronDown className={cn("h-4 w-4 text-muted-foreground transition-transform duration-200", netWorthSopOpen && "rotate-180")} />
            </button>
            {netWorthSopOpen && (
              <div className="px-4 pb-4 text-xs text-muted-foreground space-y-1">
                <p>{t("net_worth.sop_what")}</p>
                <p>{t("net_worth.sop_steps")}</p>
                <p>{t("net_worth.sop_tips")}</p>
              </div>
            )}
          </div>

          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <label htmlFor="nw-currency" className="text-xs text-muted-foreground">{t("allocation.display_currency")}</label>
              <select
                id="nw-currency"
                value={displayCurrency}
                onChange={(e) => setDisplayCurrency(e.target.value)}
                className="text-xs border border-border rounded px-3 py-2 min-h-[44px] bg-background"
              >
                {DISPLAY_CURRENCIES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            <Button
              onClick={() => {
                setNetWorthSheetKind("asset")
                setNetWorthSheetOpen(true)
              }}
              className="text-xs min-h-[44px]"
            >
              {t("net_worth.add_item")}
            </Button>
          </div>

          {showNetWorthOnboarding ? (
            <div className="rounded-md border border-dashed border-border bg-muted/20 p-5 space-y-3">
              <p className="text-sm font-semibold">{t("net_worth.onboarding_title")}</p>
              <p className="text-xs text-muted-foreground">{t("net_worth.onboarding_desc")}</p>
              {netWorthSeedPreview?.has_holdings && hasSeedableCash && (
                <div className="rounded-md border border-border bg-background p-3 space-y-1">
                  <p className="text-xs font-medium">{t("net_worth.seed_preview_title")}</p>
                  <p className="text-xs text-muted-foreground">
                    {t("net_worth.seed_preview_investment", {
                      value: formatDisplayCurrency(netWorthSeedPreview.investment_value),
                    })}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {t("net_worth.seed_preview_cash", {
                      value: formatDisplayCurrency(netWorthSeedPreview.cash_value),
                      count: netWorthSeedPreview.cash_positions.length,
                    })}
                  </p>
                  <Button
                    size="sm"
                    className="mt-2 text-xs"
                    disabled={seedNetWorth.isPending}
                    onClick={() => {
                      setSeedFeedback("")
                      seedNetWorth.mutate(undefined, {
                        onSuccess: (result) => {
                          const createdCount = result.created_items.length
                          if (createdCount > 0) {
                            setSeedFeedback(t("net_worth.seed_success", { count: createdCount }))
                            return
                          }
                          setSeedFeedback(t("net_worth.seed_already_done"))
                        },
                        onError: (err: unknown) => {
          toast.error(getErrorMessage(err) || t("common.error"))
        },
                      })
                    }}
                  >
                    {t("net_worth.seed_import_btn")}
                  </Button>
                  {seedFeedback ? <p className="text-xs text-muted-foreground">{seedFeedback}</p> : null}
                </div>
              )}
              <div className="flex gap-2">
                <Button
                  size="sm"
                  onClick={() => {
                    setNetWorthSheetKind("asset")
                    setNetWorthSheetOpen(true)
                  }}
                  className="text-xs"
                >
                  {t("net_worth.onboarding_add_asset")}
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setNetWorthSheetKind("liability")
                    setNetWorthSheetOpen(true)
                  }}
                  className="text-xs"
                >
                  {t("net_worth.onboarding_add_liability")}
                </Button>
              </div>
            </div>
          ) : (
            <>
              <NetWorthOverview summary={netWorthSummary} />
              <NetWorthHistoryChart
                history={netWorthHistory ?? []}
                isLoading={netWorthHistoryLoading}
                privacyMode={privacyMode}
                timeframe={netWorthHistoryDays}
                onTimeframeChange={setNetWorthHistoryDays}
              />
              <div ref={netWorthTableRef}>
                <NetWorthItemsTable items={netWorthItems ?? []} privacyMode={privacyMode} />
              </div>
            </>
          )}
        </TabsContent>

        {/* Settings tab */}
        <TabsContent value="settings" className="mt-4 space-y-8">
          <section className="space-y-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">
              {t("allocation.tab.portfolio")}
            </p>
            <div className="rounded-md border border-border p-4">
              <TargetAllocation />
            </div>
            <div className="rounded-md border border-border p-4">
              <HoldingsManager privacyMode={privacyMode} />
            </div>
          </section>

          <section className="space-y-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">
              {t("terminology_settings.terminology_mode")}
            </p>
            <div className="rounded-md border border-border p-4">
              <TerminologySettings />
            </div>
          </section>

          <section className="space-y-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">
              {t("allocation.telegram.title")}
            </p>
            <div className="rounded-md border border-border p-4">
              <TelegramSettings privacyMode={privacyMode} />
            </div>
            <div className="rounded-md border border-border p-4">
              <NotificationPreferences />
            </div>
          </section>
        </TabsContent>
      </Tabs>

      {/* Add Holding sidebar sheet */}
      <AddHoldingSheet open={sheetOpen} onClose={() => setSheetOpen(false)} />
      <AddNetWorthItemSheet
        key={`${netWorthSheetOpen ? "open" : "closed"}-${netWorthSheetKind}`}
        open={netWorthSheetOpen}
        onClose={() => setNetWorthSheetOpen(false)}
        initialKind={netWorthSheetKind}
      />
      {transactionSheetOpen ? (
        <AddTransactionSheet
          key={`${transactionSheetOpen ? "open" : "closed"}-${transactionDefaultTicker ?? "all"}-${transactionDefaultAccountId ?? "na"}-${transactionDefaultType ?? "BUY"}-${transactionDefaultCurrency ?? "USD"}`}
          open={transactionSheetOpen}
          onClose={() => setTransactionSheetOpen(false)}
          defaultTicker={transactionDefaultTicker}
          defaultAccountId={transactionDefaultAccountId}
          defaultTransactionType={transactionDefaultType}
          defaultCurrency={transactionDefaultCurrency}
          onOpenBuyForAccount={(accountId, currency) =>
            openTransactionSheet({
              accountId,
              transactionType: "BUY",
              currency,
            })}
          onOpenAccounts={() => {
            setTransactionSheetOpen(false)
            setActiveTab("accounts")
          }}
        />
      ) : null}
    </div>
  )
}
