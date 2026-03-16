import { useCallback, useEffect, useRef, useState } from "react"
import { ChevronDown, ChevronRight, Clock3 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { useSearchParams } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { useAccounts } from "@/api/hooks/useAccounts"
import { useHoldings, useProfile } from "@/api/hooks/useDashboard"
import { usePrivacyMode } from "@/hooks/usePrivacyMode"
import { FINANCE_SURFACE, FINANCE_TEXT } from "@/lib/colors"
import { RebalanceAnalysis } from "@/components/allocation/analysis/RebalanceAnalysis"
import { CurrencyExposure } from "@/components/allocation/tools/CurrencyExposure"
import { StressTest } from "@/components/allocation/tools/StressTest"
import { SmartWithdrawal } from "@/components/allocation/tools/SmartWithdrawal"
import { TargetAllocation } from "@/components/allocation/tools/TargetAllocation"
import { HoldingsManager } from "../components/allocation/holdings/HoldingsManager"
import { TelegramSettings } from "@/components/allocation/settings/TelegramSettings"
import { NotificationPreferences } from "@/components/allocation/settings/NotificationPreferences"
import { TerminologySettings } from "@/components/allocation/settings/TerminologySettings"
import { DISPLAY_CURRENCIES } from "@/lib/constants"
import { cn, formatRelativeTime } from "@/lib/utils"
import { AccountsTab } from "@/components/allocation/accounts/AccountsTab"
import { AddTransactionSheet } from "@/components/allocation/transactions/AddTransactionSheet"
import { QuotaDashboard } from "@/components/allocation/wrappers/QuotaDashboard"
import { SmartActionCards } from "@/components/allocation/wrappers/SmartActionCards"

type TransactionSheetType = "BUY" | "SELL" | "DIVIDEND" | "DEPOSIT" | "WITHDRAWAL"

export default function Allocation() {
  const { t, i18n } = useTranslation()
  const [searchParams, setSearchParams] = useSearchParams()
  const [sopOpen, setSopOpen] = useState(false)
  const [nowEpochSeconds, setNowEpochSeconds] = useState(() => Math.floor(Date.now() / 1000))
  const tabParam = searchParams.get("tab")
  const activeTab =
    tabParam === "risk" ||
    tabParam === "actions" ||
    tabParam === "accounts" ||
    tabParam === "settings"
      ? tabParam
      : tabParam === "transactions"
        ? "accounts"
        : "portfolio"
  const [displayCurrency, setDisplayCurrency] = useState("USD")
  const [riskExpanded, setRiskExpanded] = useState(false)
  const [actionsExpanded, setActionsExpanded] = useState(false)
  const [transactionSheetOpen, setTransactionSheetOpen] = useState(false)
  const [transactionDefaultTicker, setTransactionDefaultTicker] = useState<string | undefined>(undefined)
  const [transactionDefaultAccountId, setTransactionDefaultAccountId] = useState<number | undefined>(undefined)
  const [transactionDefaultType, setTransactionDefaultType] = useState<TransactionSheetType | undefined>(undefined)
  const [transactionDefaultCurrency, setTransactionDefaultCurrency] = useState<string | undefined>(undefined)
  const handledDashboardActionRef = useRef<string | null>(null)

  const { data: profile, isLoading: profileLoading } = useProfile()
  const { data: holdings, isLoading: holdingsLoading, dataUpdatedAt: holdingsUpdatedAt } = useHoldings()
  const { data: accounts, isLoading: accountsLoading } = useAccounts()
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

  const openTransactionSheet = useCallback((options?: {
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
  }, [])

  useEffect(() => {
    if (activeTab !== "accounts") return

    const action = searchParams.get("action")
    const accountIdRaw = searchParams.get("accountId")
    if (!action || !accountIdRaw) return
    if (action !== "deposit" && action !== "trade") return

    const accountId = Number(accountIdRaw)
    if (!Number.isFinite(accountId)) return

    const dedupeKey = `${action}:${accountId}`
    if (handledDashboardActionRef.current === dedupeKey) return
    handledDashboardActionRef.current = dedupeKey

    const accountCurrency = accounts?.find((account) => account.id === accountId)?.currency
    // This effect hydrates one-time dashboard intent from URL params after navigation.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    openTransactionSheet({
      accountId,
      transactionType: action === "deposit" ? "DEPOSIT" : undefined,
      currency: accountCurrency,
    })

    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      next.delete("action")
      next.delete("accountId")
      return next
    })
  }, [activeTab, searchParams, accounts, openTransactionSheet, setSearchParams])

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
  const hasWrappedAccounts = (accounts ?? []).some((account) => !!account.tax_wrapper)
  const accountByWrapper = new Map<string, { id: number; currency: string }>()
  for (const account of accounts ?? []) {
    if (account.id == null) continue
    const wrapper = (account.tax_wrapper ?? "").trim().toLowerCase()
    if (!wrapper || accountByWrapper.has(wrapper)) continue
    accountByWrapper.set(wrapper, {
      id: account.id,
      currency: (account.currency || "USD").toUpperCase(),
    })
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
          onClick={() => openTransactionSheet()}
        >
          {t("transactions.record_button")}
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
          <TabsTrigger value="accounts" className="min-h-[44px]">{t("allocation.tab.accounts")}</TabsTrigger>
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
            onExecutePlacementSuggestion={(ticker, targetWrapper) => {
              const target = accountByWrapper.get(targetWrapper)
              if (!target) return
              openTransactionSheet({
                ticker,
                accountId: target.id,
                currency: target.currency,
                transactionType: "BUY",
              })
            }}
            onSetupTsumitateMigration={(tickers) => {
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
        </TabsContent>

        {/* Risk tab */}
        <TabsContent value="risk" className="mt-4 space-y-6">
          {riskExpanded ? (
            <>
              <CurrencyExposure
                privacyMode={privacyMode}
                profile={profile}
                enabled={activeTab === "risk"}
                showFxDashboardLink
              />
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
              <SmartActionCards
                enabled={activeTab === "actions"}
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

        {/* Accounts tab */}
        <TabsContent value="accounts" className="mt-4 space-y-4">
          {hasWrappedAccounts ? <QuotaDashboard enabled={activeTab === "accounts"} /> : null}
          <AccountsTab
            enabled={activeTab === "accounts"}
            onDepositToAccount={(accountId, currency) =>
              openTransactionSheet({
                accountId,
                transactionType: "DEPOSIT",
                currency,
              })}
            onRecordTransaction={(accountId, currency) =>
              openTransactionSheet({
                accountId,
                currency,
              })}
          />
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
