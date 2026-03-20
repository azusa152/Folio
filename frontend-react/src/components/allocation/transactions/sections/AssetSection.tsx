import { useTranslation } from "react-i18next"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Input } from "@/components/ui/input"
import { STOCK_CATEGORIES } from "@/lib/constants"
import { TransactionTypePicker } from "./asset/TransactionTypePicker"
import { TickerInput } from "./asset/TickerInput"
import { RoutingSuggestion } from "./asset/RoutingSuggestion"
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

interface RoutingSuggestionData {
  suggestions?: Array<{ wrapper: string; amount: number; reason: string }>
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
      <TransactionTypePicker
        transactionType={transactionType}
        currency={currency}
        setTransactionType={setTransactionType}
        setSellPickerOpen={setSellPickerOpen}
        setSellPickerSearch={setSellPickerSearch}
        setInsufficientBalance={setInsufficientBalance}
        setFieldErrors={setFieldErrors}
        applyCashMovementDefaults={applyCashMovementDefaults}
      />

      {!isCashMovement ? (
        <>
          <TickerInput
            transactionType={transactionType}
            ticker={ticker}
            shouldShowNisaPicker={shouldShowNisaPicker}
            shouldShowSellPicker={shouldShowSellPicker}
            nisaFreeTickerInput={nisaFreeTickerInput}
            selectedWrapper={selectedWrapper}
            nisaAssetTypeFilter={nisaAssetTypeFilter}
            nisaPickerOpen={nisaPickerOpen}
            nisaPickerSearch={nisaPickerSearch}
            nisaEligibleAssetsQuery={nisaEligibleAssetsQuery}
            selectedNisaAssetForDisplay={selectedNisaAssetForDisplay}
            isMobile={isMobile}
            commandListScrollFix={commandListScrollFix}
            sellPickerOpen={sellPickerOpen}
            sellPickerSearch={sellPickerSearch}
            filteredSellablePositions={filteredSellablePositions}
            selectedSellablePositionForDisplay={selectedSellablePositionForDisplay}
            sellablePositionsQuery={sellablePositionsQuery}
            fieldErrors={fieldErrors}
            setTicker={setTicker}
            setNisaAssetTypeFilter={setNisaAssetTypeFilter}
            setNisaPickerOpen={setNisaPickerOpen}
            setNisaPickerSearch={setNisaPickerSearch}
            setSellPickerOpen={setSellPickerOpen}
            setSellPickerSearch={setSellPickerSearch}
            setFieldErrors={setFieldErrors}
            setInsufficientBalance={setInsufficientBalance}
            onSelectNisaAsset={onSelectNisaAsset}
            onSelectSellablePosition={onSelectSellablePosition}
            getSellValueSourceLabel={getSellValueSourceLabel}
          />

          <RoutingSuggestion
            transactionType={transactionType}
            selectedWrapper={selectedWrapper}
            eligibility={eligibility}
            eligibilityQueryIsLoading={eligibilityQueryIsLoading}
            suggestedAccount={suggestedAccount}
            routingSuggestionQuery={routingSuggestionQuery}
            routingSuggestedAccounts={routingSuggestedAccounts}
            canSplitPurchase={canSplitPurchase}
            splitSubmitting={splitSubmitting}
            addTransactionMutationIsPending={addTransactionMutationIsPending}
            setAccountId={setAccountId}
            setCurrency={setCurrency}
            setInsufficientBalance={setInsufficientBalance}
            createSplitTransactions={createSplitTransactions}
          />
        </>
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
