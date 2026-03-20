import { Building2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { useAddTransactionForm, type TransactionType } from "@/hooks/useAddTransactionForm"
import { AccountSection } from "./sections/AccountSection"
import { AssetSection } from "./sections/AssetSection"
import { PriceSection } from "./sections/PriceSection"
import { DateSection } from "./sections/DateSection"

interface Props {
  open: boolean
  onClose: () => void
  defaultTicker?: string
  defaultHoldingId?: number
  defaultAccountId?: number
  defaultTransactionType?: TransactionType
  defaultCurrency?: string
  onOpenBuyForAccount?: (accountId: number, currency: string) => void
  onOpenAccounts?: () => void
}

export type { TransactionType }

export function AddTransactionSheet({
  open,
  onClose,
  defaultTicker,
  defaultHoldingId,
  defaultAccountId,
  defaultTransactionType,
  defaultCurrency,
  onOpenBuyForAccount,
  onOpenAccounts,
}: Props) {
  const { t } = useTranslation()
  const form = useAddTransactionForm({
    open,
    defaultTicker,
    defaultHoldingId,
    defaultAccountId,
    defaultTransactionType,
    defaultCurrency,
    onClose,
    onOpenBuyForAccount,
  })

  return (
    <Sheet open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <SheetContent side="right" className="w-80 sm:w-96 overflow-y-auto">
        <SheetHeader>
          <SheetTitle className="text-sm">{t("transactions.form.title")}</SheetTitle>
        </SheetHeader>

        {form.hasNoAccounts ? (
          <div className="mt-4 flex flex-col items-center justify-center gap-4 px-4 py-12 text-center">
            <div className="rounded-full bg-muted p-4">
              <Building2 className="h-8 w-8 text-muted-foreground" />
            </div>
            <div className="space-y-1">
              <p className="text-sm font-semibold">{t("transactions.empty_state.title")}</p>
              <p className="text-xs text-muted-foreground">{t("transactions.empty_state.description")}</p>
            </div>
            {onOpenAccounts ? (
              <Button size="sm" onClick={onOpenAccounts}>
                {t("transactions.empty_state.create_account")}
              </Button>
            ) : null}
          </div>
        ) : (
          <div className="mt-4 space-y-4">
            <AccountSection
              accountId={form.accountId}
              accounts={form.accounts}
              transactionType={form.transactionType}
              isCashMovement={form.isCashMovement}
              currency={form.currency}
              selectedAccountId={form.selectedAccountId}
              selectedCurrencyCashBalance={form.selectedCurrencyCashBalance}
              selectedAccount={form.selectedAccount}
              shouldShowQuotaSummary={form.shouldShowQuotaSummary}
              selectedWrapper={form.selectedWrapper}
              selectedQuota={form.selectedQuota}
              wrapperQuotaQuery={form.wrapperQuotaQuery}
              hasNoAccounts={form.hasNoAccounts}
              fieldErrors={form.fieldErrors}
              insufficientBalance={form.insufficientBalance}
              onOpenAccounts={onOpenAccounts}
              setAccountId={form.setAccountId}
              setCurrency={form.setCurrency}
              setTransactionType={form.setTransactionType}
              setQuantity={form.setQuantity}
              setPrice={form.setPrice}
              setManualTotal={form.setManualTotal}
              setTotalAmount={form.setTotalAmount}
              setInsufficientBalance={form.setInsufficientBalance}
              setFieldErrors={form.setFieldErrors}
              applyCashMovementDefaults={form.applyCashMovementDefaults}
              clearSellablePositionCache={form.clearSellablePositionCache}
            />

            <AssetSection
              transactionType={form.transactionType}
              isCashMovement={form.isCashMovement}
              currency={form.currency}
              ticker={form.ticker}
              thesis={form.thesis}
              category={form.category}
              forcedCategory={form.forcedCategory}
              isNewToRadar={form.isNewToRadar}
              shouldShowNisaPicker={form.shouldShowNisaPicker}
              shouldShowSellPicker={form.shouldShowSellPicker}
              nisaFreeTickerInput={form.nisaFreeTickerInput}
              selectedWrapper={form.selectedWrapper}
              nisaAssetTypeFilter={form.nisaAssetTypeFilter}
              nisaPickerOpen={form.nisaPickerOpen}
              nisaPickerSearch={form.nisaPickerSearch}
              nisaEligibleAssetsQuery={form.nisaEligibleAssetsQuery}
              selectedNisaAssetForDisplay={form.selectedNisaAssetForDisplay}
              isMobile={form.isMobile}
              commandListScrollFix={form.commandListScrollFix}
              sellPickerOpen={form.sellPickerOpen}
              sellPickerSearch={form.sellPickerSearch}
              filteredSellablePositions={form.filteredSellablePositions}
              selectedSellablePositionForDisplay={form.selectedSellablePositionForDisplay}
              sellablePositionsQuery={form.sellablePositionsQuery}
              eligibility={form.eligibility}
              eligibilityQueryIsLoading={form.eligibilityQuery.isLoading}
              suggestedAccount={form.suggestedAccount}
              routingSuggestionQuery={form.routingSuggestionQuery}
              routingSuggestedAccounts={form.routingSuggestedAccounts}
              canSplitPurchase={form.canSplitPurchase}
              splitSubmitting={form.splitSubmitting}
              addTransactionMutationIsPending={form.addTransactionMutation.isPending}
              fieldErrors={form.fieldErrors}
              setTransactionType={form.setTransactionType}
              setTicker={form.setTicker}
              setThesis={form.setThesis}
              setCategory={form.setCategory}
              setNisaAssetTypeFilter={form.setNisaAssetTypeFilter}
              setNisaPickerOpen={form.setNisaPickerOpen}
              setNisaPickerSearch={form.setNisaPickerSearch}
              setSellPickerOpen={form.setSellPickerOpen}
              setSellPickerSearch={form.setSellPickerSearch}
              setAccountId={form.setAccountId}
              setCurrency={form.setCurrency}
              setInsufficientBalance={form.setInsufficientBalance}
              setFieldErrors={form.setFieldErrors}
              applyCashMovementDefaults={form.applyCashMovementDefaults}
              onSelectNisaAsset={form.onSelectNisaAsset}
              onSelectSellablePosition={form.onSelectSellablePosition}
              getSellValueSourceLabel={form.getSellValueSourceLabel}
              createSplitTransactions={form.createSplitTransactions}
            />

            <PriceSection
              isCashMovement={form.isCashMovement}
              quantity={form.quantity}
              price={form.price}
              totalAmount={form.totalAmount}
              currency={form.currency}
              manualTotal={form.manualTotal}
              shouldShowSellPicker={form.shouldShowSellPicker}
              selectedSellablePositionForDisplay={form.selectedSellablePositionForDisplay}
              forcedCategory={form.forcedCategory}
              category={form.category}
              fieldErrors={form.fieldErrors}
              setQuantity={form.setQuantity}
              setPrice={form.setPrice}
              setTotalAmount={form.setTotalAmount}
              setCurrency={form.setCurrency}
              setManualTotal={form.setManualTotal}
              setFieldErrors={form.setFieldErrors}
              applyCashMovementDefaults={form.applyCashMovementDefaults}
              computeTotalAmount={form.computeTotalAmount}
            />

            <DateSection
              isCashMovement={form.isCashMovement}
              transactionDate={form.transactionDate}
              moreOptionsOpen={form.moreOptionsOpen}
              holdingId={form.holdingId}
              currency={form.currency}
              fxRate={form.fxRate}
              fee={form.fee}
              note={form.note}
              holdingOptions={form.holdingOptions}
              fieldErrors={form.fieldErrors}
              setTransactionDate={form.setTransactionDate}
              setMoreOptionsOpen={form.setMoreOptionsOpen}
              setHoldingId={form.setHoldingId}
              setCurrency={form.setCurrency}
              setFxRate={form.setFxRate}
              setFee={form.setFee}
              setNote={form.setNote}
              setFieldErrors={form.setFieldErrors}
            />

            <Button
              className="w-full"
              size="sm"
              disabled={form.splitSubmitting || form.addTransactionMutation.isPending || form.selectedAccountId == null}
              onClick={form.handleSubmit}
            >
              {t("transactions.form.submit")}
            </Button>
          </div>
        )}
      </SheetContent>
    </Sheet>
  )
}
