import { useTranslation } from "react-i18next"
import { Button } from "@/components/ui/button"
import { EligibilityBadge } from "@/components/common/EligibilityBadge"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ELIGIBILITY_CHECK_WRAPPERS, STOCK_CATEGORIES } from "@/lib/constants"
import { cn } from "@/lib/utils"
import { NisaAssetPicker } from "../NisaAssetPicker"
import { SellablePositionPicker } from "../SellablePositionPicker"
import type {
  TransactionType,
  StockCategory,
  NisaEligibleAssetItem,
  SellablePositionItem,
  NisaAssetTypeFilter,
  FieldErrors,
} from "@/hooks/useAddTransactionForm"
import type { UseQueryResult } from "@tanstack/react-query"

interface EligibilityResult {
  ticker: string
  wrapper: string
  eligible: boolean
  asset_type?: string | null
  suggested_wrapper?: string | null
  reasons: string[]
}

interface AccountItem {
  id?: number
  name?: string
  broker?: string
  currency?: string
}

interface RoutingSuggestion {
  wrapper: string
  amount: number
  reason: string
}

interface RoutingSuggestionData {
  suggestions?: RoutingSuggestion[]
}

interface NisaEligibleAssetsData {
  items?: NisaEligibleAssetItem[]
}

interface AssetSectionProps {
  transactionType: TransactionType
  isCashMovement: boolean
  currency: string
  ticker: string
  thesis: string
  category: StockCategory
  forcedCategory: StockCategory | null
  isNewToRadar: boolean
  shouldShowNisaPicker: boolean
  shouldShowSellPicker: boolean
  nisaFreeTickerInput: boolean
  selectedWrapper: string
  nisaAssetTypeFilter: NisaAssetTypeFilter
  nisaPickerOpen: boolean
  nisaPickerSearch: string
  nisaEligibleAssetsQuery: UseQueryResult<NisaEligibleAssetsData>
  selectedNisaAssetForDisplay: NisaEligibleAssetItem | null
  isMobile: boolean
  commandListScrollFix: Record<string, unknown>
  sellPickerOpen: boolean
  sellPickerSearch: string
  filteredSellablePositions: SellablePositionItem[]
  selectedSellablePositionForDisplay: SellablePositionItem | null
  sellablePositionsQuery: UseQueryResult<unknown>
  eligibility: EligibilityResult | undefined | null
  eligibilityQueryIsLoading: boolean
  suggestedAccount: AccountItem | null | undefined
  routingSuggestionQuery: UseQueryResult<RoutingSuggestionData>
  routingSuggestedAccounts: Map<string, { id: number; currency: string }>
  canSplitPurchase: boolean
  splitSubmitting: boolean
  addTransactionMutationIsPending: boolean
  fieldErrors: FieldErrors
  setTransactionType: (t: TransactionType) => void
  setTicker: (t: string) => void
  setThesis: (t: string) => void
  setCategory: (c: StockCategory) => void
  setNisaAssetTypeFilter: (f: NisaAssetTypeFilter) => void
  setNisaPickerOpen: (o: boolean) => void
  setNisaPickerSearch: (s: string) => void
  setSellPickerOpen: (o: boolean) => void
  setSellPickerSearch: (s: string) => void
  setAccountId: (id: string) => void
  setCurrency: (c: string) => void
  setInsufficientBalance: (v: { available: number; required: number } | null) => void
  setFieldErrors: (updater: (prev: FieldErrors) => FieldErrors) => void
  applyCashMovementDefaults: (currency: string) => void
  onSelectNisaAsset: (item: NisaEligibleAssetItem) => void
  onSelectSellablePosition: (item: SellablePositionItem) => void
  getSellValueSourceLabel: (valueSource?: SellablePositionItem["value_source"]) => string | null
  createSplitTransactions: () => Promise<void>
}

export function AssetSection({
  transactionType,
  isCashMovement,
  currency,
  ticker,
  thesis,
  category,
  forcedCategory,
  isNewToRadar,
  shouldShowNisaPicker,
  shouldShowSellPicker,
  nisaFreeTickerInput,
  selectedWrapper,
  nisaAssetTypeFilter,
  nisaPickerOpen,
  nisaPickerSearch,
  nisaEligibleAssetsQuery,
  selectedNisaAssetForDisplay,
  isMobile,
  commandListScrollFix,
  sellPickerOpen,
  sellPickerSearch,
  filteredSellablePositions,
  selectedSellablePositionForDisplay,
  sellablePositionsQuery,
  eligibility,
  eligibilityQueryIsLoading,
  suggestedAccount,
  routingSuggestionQuery,
  routingSuggestedAccounts,
  canSplitPurchase,
  splitSubmitting,
  addTransactionMutationIsPending,
  fieldErrors,
  setTransactionType,
  setTicker,
  setThesis,
  setCategory,
  setNisaAssetTypeFilter,
  setNisaPickerOpen,
  setNisaPickerSearch,
  setSellPickerOpen,
  setSellPickerSearch,
  setAccountId,
  setCurrency,
  setInsufficientBalance,
  setFieldErrors,
  applyCashMovementDefaults,
  onSelectNisaAsset,
  onSelectSellablePosition,
  getSellValueSourceLabel,
  createSplitTransactions,
}: AssetSectionProps) {
  const { t } = useTranslation()

  return (
    <>
      <div className="space-y-1">
        <p className="text-xs font-medium">{t("transactions.form.type")}</p>
        <div className="grid grid-cols-2 gap-1">
          {(["BUY", "SELL", "DIVIDEND", "DEPOSIT", "WITHDRAWAL"] as TransactionType[]).map((type) => (
            <button
              key={type}
              type="button"
              onClick={() => {
                setTransactionType(type)
                setSellPickerOpen(false)
                setSellPickerSearch("")
                setInsufficientBalance(null)
                setFieldErrors(() => ({}))
                if (type === "DEPOSIT" || type === "WITHDRAWAL") {
                  applyCashMovementDefaults(currency)
                }
              }}
              className={`text-xs py-1.5 rounded border transition-colors ${
                transactionType === type
                  ? "bg-primary text-primary-foreground border-primary"
                  : "border-border hover:bg-muted/30"
              }`}
            >
              {t(`transactions.type.${type.toLowerCase()}`)}
            </button>
          ))}
        </div>
      </div>

      {!isCashMovement ? (
        <div className="space-y-1">
          <p className="text-xs font-medium">{t("transactions.form.ticker")}</p>
          {shouldShowNisaPicker && selectedWrapper === "nisa_growth" ? (
            <div className="flex flex-wrap gap-1 pb-1">
              {(["all", "mutual_fund", "etf", "stock", "reit"] as const).map((type) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => setNisaAssetTypeFilter(type)}
                  className={cn(
                    "rounded-full border px-2 py-1 text-[11px] leading-none",
                    nisaAssetTypeFilter === type
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-border text-muted-foreground hover:bg-muted/40",
                  )}
                >
                  {type === "all" ? t("nisa.eligible.filter_all") : t(`nisa.eligible.asset_type.${type}`)}
                </button>
              ))}
            </div>
          ) : null}

          {nisaFreeTickerInput ? (
            <>
              <Input
                value={ticker}
                aria-label={t("transactions.form.ticker")}
                onChange={(event) => {
                  setTicker(event.target.value.normalize("NFKC").toUpperCase())
                  setFieldErrors((prev) => ({ ...prev, ticker: undefined }))
                  setInsufficientBalance(null)
                }}
                onBlur={() => {
                  if (/^\d{4}$/.test(ticker)) setTicker(`${ticker}.T`)
                }}
                placeholder="e.g. 7203.T"
                className="text-xs"
              />
              <p className="text-[11px] text-muted-foreground">{t("nisa.eligible.listed_input_hint")}</p>
              <p className="text-[11px] text-amber-600 dark:text-amber-400">
                {t("nisa.eligible.listed_eligibility_disclaimer")}
              </p>
            </>
          ) : shouldShowNisaPicker ? (
            <NisaAssetPicker
              ticker={ticker}
              selectedWrapper={selectedWrapper}
              nisaPickerOpen={nisaPickerOpen}
              nisaPickerSearch={nisaPickerSearch}
              nisaEligibleAssetsQuery={nisaEligibleAssetsQuery}
              selectedNisaAssetForDisplay={selectedNisaAssetForDisplay}
              isMobile={isMobile}
              commandListScrollFix={commandListScrollFix}
              onSelect={onSelectNisaAsset}
              setNisaPickerOpen={setNisaPickerOpen}
              setNisaPickerSearch={setNisaPickerSearch}
            />
          ) : shouldShowSellPicker ? (
            <SellablePositionPicker
              ticker={ticker}
              transactionType={transactionType}
              sellPickerOpen={sellPickerOpen}
              sellPickerSearch={sellPickerSearch}
              filteredSellablePositions={filteredSellablePositions}
              selectedSellablePositionForDisplay={selectedSellablePositionForDisplay}
              sellablePositionsQuery={sellablePositionsQuery}
              isMobile={isMobile}
              commandListScrollFix={commandListScrollFix}
              getSellValueSourceLabel={getSellValueSourceLabel}
              onSelect={onSelectSellablePosition}
              setSellPickerOpen={setSellPickerOpen}
              setSellPickerSearch={setSellPickerSearch}
            />
          ) : (
            <Input
              value={ticker}
              aria-label={t("transactions.form.ticker")}
              onChange={(event) => {
                setTicker(event.target.value.normalize("NFKC").toUpperCase())
                setFieldErrors((prev) => ({ ...prev, ticker: undefined }))
                setInsufficientBalance(null)
              }}
              onBlur={() => {
                if (/^\d{4}$/.test(ticker)) setTicker(`${ticker}.T`)
              }}
              placeholder="e.g. AAPL, 7203.T"
              className="text-xs"
            />
          )}

          {transactionType === "BUY" && ELIGIBILITY_CHECK_WRAPPERS.has(selectedWrapper) ? (
            <div className="pt-1 space-y-1">
              <EligibilityBadge result={eligibility ?? undefined} loading={eligibilityQueryIsLoading} />
              {eligibility && !eligibility.eligible ? (
                <div className="space-y-1">
                  <p className="text-[11px] text-destructive">{t("eligibility.not_eligible")}</p>
                  {eligibility.suggested_wrapper ? (
                    suggestedAccount ? (
                      <button
                        type="button"
                        className="text-[11px] text-primary hover:underline"
                        onClick={() => {
                          if (suggestedAccount.id == null) return
                          setAccountId(String(suggestedAccount.id))
                          const nextCurrency = (suggestedAccount.currency || currency).toUpperCase()
                          setCurrency(nextCurrency)
                          setInsufficientBalance(null)
                        }}
                      >
                        {t("eligibility.switch_to_suggested_account", {
                          wrapper: t(`wrapper.${eligibility.suggested_wrapper}`),
                        })}
                      </button>
                    ) : (
                      <p className="text-[11px] text-muted-foreground">
                        {t("eligibility.no_suggested_account", {
                          wrapper: t(`wrapper.${eligibility.suggested_wrapper}`),
                        })}
                      </p>
                    )
                  ) : null}
                </div>
              ) : null}
            </div>
          ) : null}

          {transactionType === "BUY" && routingSuggestionQuery.data?.suggestions?.length ? (
            <div className="pt-1 space-y-1">
              <p className="text-[11px] font-medium">{t("routing.suggest_title")}</p>
              <div className="space-y-1">
                {routingSuggestionQuery.data.suggestions.map((item, idx) => {
                  const suggested = routingSuggestedAccounts.get(item.wrapper)
                  return (
                    <div
                      key={`${item.wrapper}-${idx}`}
                      className="rounded-md border border-border bg-muted/20 px-2 py-1.5"
                    >
                      <div className="flex items-center justify-between gap-2 text-[11px]">
                        <span>{t(`wrapper.${item.wrapper}`, { defaultValue: item.wrapper })}</span>
                        <span>{Math.round(item.amount).toLocaleString()}</span>
                      </div>
                      <p className="text-[11px] text-muted-foreground">
                        {t(item.reason, { defaultValue: item.reason })}
                      </p>
                      {suggested ? (
                        <button
                          type="button"
                          className="text-[11px] text-primary hover:underline"
                          onClick={() => {
                            setAccountId(String(suggested.id))
                            setCurrency(suggested.currency)
                            setInsufficientBalance(null)
                          }}
                        >
                          {t("smart_actions.apply_suggestion")}
                        </button>
                      ) : null}
                    </div>
                  )
                })}
              </div>
              {canSplitPurchase ? (
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="h-7 text-[11px]"
                  disabled={splitSubmitting || addTransactionMutationIsPending}
                  onClick={() => {
                    createSplitTransactions().catch(() => {
                      // createSplitTransactions handles all user feedback paths.
                    })
                  }}
                >
                  {t("smart_actions.split_purchase")}
                </Button>
              ) : null}
            </div>
          ) : null}

          {fieldErrors.ticker ? <p className="text-xs text-destructive">{fieldErrors.ticker}</p> : null}
        </div>
      ) : null}

      {!isCashMovement && isNewToRadar ? (
        <div className="space-y-1">
          <p className="text-xs font-medium">{t("transactions.form.thesis")}</p>
          <Input
            value={thesis}
            aria-label={t("transactions.form.thesis")}
            onChange={(event) => setThesis(event.target.value)}
            placeholder={t("transactions.form.thesis_hint")}
            className="text-xs"
          />
          <p className="text-xs font-medium pt-2">{t("transactions.form.category")}</p>
          <Select
            value={forcedCategory ?? category}
            onValueChange={(value) => setCategory(value as StockCategory)}
            disabled={forcedCategory != null}
          >
            <SelectTrigger aria-label={t("transactions.form.category")} className="text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {STOCK_CATEGORIES.map((item) => (
                <SelectItem key={item} value={item} className="text-xs">
                  {t(`config.category.${item.toLowerCase()}`)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {!forcedCategory ? (
            <p className="text-[11px] text-muted-foreground">
              {t(`config.category_desc.${category.toLowerCase()}`)}
            </p>
          ) : null}
          {forcedCategory ? (
            <p className="text-[11px] text-muted-foreground">{t("transactions.form.mutual_fund_category_hint")}</p>
          ) : null}
        </div>
      ) : null}
    </>
  )
}
