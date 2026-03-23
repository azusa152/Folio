import { useTranslation } from "react-i18next"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"
import { NisaAssetPicker } from "../../NisaAssetPicker"
import { SellablePositionPicker } from "../../SellablePositionPicker"
import type {
  TransactionType,
  NisaEligibleAssetItem,
  SellablePositionItem,
  NisaAssetTypeFilter,
  FieldErrors,
} from "@/hooks/useAddTransactionForm"
import type { UseQueryResult } from "@tanstack/react-query"

interface NisaEligibleAssetsData {
  items?: NisaEligibleAssetItem[]
}

export interface TickerInputProps {
  transactionType: TransactionType
  ticker: string
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
  fieldErrors: FieldErrors
  setTicker: (t: string) => void
  setNisaAssetTypeFilter: (f: NisaAssetTypeFilter) => void
  setNisaPickerOpen: (o: boolean) => void
  setNisaPickerSearch: (s: string) => void
  setSellPickerOpen: (o: boolean) => void
  setSellPickerSearch: (s: string) => void
  setFieldErrors: (updater: (prev: FieldErrors) => FieldErrors) => void
  setInsufficientBalance: (v: { available: number; required: number } | null) => void
  onSelectNisaAsset: (item: NisaEligibleAssetItem) => void
  onSelectSellablePosition: (item: SellablePositionItem) => void
  getSellValueSourceLabel: (valueSource?: SellablePositionItem["value_source"]) => string | null
}

export function TickerInput({
  transactionType,
  ticker,
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
  fieldErrors,
  setTicker,
  setNisaAssetTypeFilter,
  setNisaPickerOpen,
  setNisaPickerSearch,
  setSellPickerOpen,
  setSellPickerSearch,
  setFieldErrors,
  setInsufficientBalance,
  onSelectNisaAsset,
  onSelectSellablePosition,
  getSellValueSourceLabel,
}: TickerInputProps) {
  const { t } = useTranslation()

  return (
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
              {type === "all"
                ? t("nisa.eligible.filter_all")
                : t(`nisa.eligible.asset_type.${type}`)}
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
          <p className="text-[11px] text-muted-foreground">
            {t("nisa.eligible.listed_input_hint")}
          </p>
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

      {fieldErrors.ticker ? <p className="text-xs text-destructive">{fieldErrors.ticker}</p> : null}
    </div>
  )
}
