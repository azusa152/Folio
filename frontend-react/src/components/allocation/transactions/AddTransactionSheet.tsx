import { Building2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Button } from "@/components/ui/button"
import { EligibilityBadge } from "@/components/common/EligibilityBadge"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { DISPLAY_CURRENCIES, ELIGIBILITY_CHECK_WRAPPERS, STOCK_CATEGORIES } from "@/lib/constants"
import { cn } from "@/lib/utils"
import { NisaAssetPicker } from "./NisaAssetPicker"
import { SellablePositionPicker } from "./SellablePositionPicker"
import { useAddTransactionForm, type TransactionType } from "@/hooks/useAddTransactionForm"

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

  const {
    transactionType, setTransactionType,
    accountId, setAccountId,
    ticker, setTicker,
    holdingId, setHoldingId,
    quantity, setQuantity,
    price, setPrice,
    totalAmount, setTotalAmount,
    currency, setCurrency,
    fxRate, setFxRate,
    fee, setFee,
    note, setNote,
    thesis, setThesis,
    category, setCategory,
    transactionDate, setTransactionDate,
    manualTotal, setManualTotal,
    moreOptionsOpen, setMoreOptionsOpen,
    fieldErrors, setFieldErrors,
    insufficientBalance, setInsufficientBalance,
    splitSubmitting,
    nisaPickerOpen, setNisaPickerOpen,
    nisaPickerSearch, setNisaPickerSearch,
    nisaAssetTypeFilter, setNisaAssetTypeFilter,
    sellPickerOpen, setSellPickerOpen,
    sellPickerSearch, setSellPickerSearch,
    // Computed
    selectedAccountId,
    selectedAccount,
    selectedWrapper,
    selectedCurrencyCashBalance,
    hasNoAccounts,
    isCashMovement,
    isNewToRadar,
    shouldShowNisaPicker,
    shouldShowSellPicker,
    nisaFreeTickerInput,
    filteredSellablePositions,
    selectedSellablePositionForDisplay,
    selectedNisaAssetForDisplay,
    eligibility,
    forcedCategory,
    suggestedAccount,
    routingSuggestedAccounts,
    canSplitPurchase,
    holdingOptions,
    shouldShowQuotaSummary,
    selectedQuota,
    // Queries
    accounts,
    nisaEligibleAssetsQuery,
    sellablePositionsQuery,
    routingSuggestionQuery,
    wrapperQuotaQuery,
    // Helpers
    addTransactionMutation,
    isMobile,
    commandListScrollFix,
    // Handlers
    applyCashMovementDefaults,
    computeTotalAmount,
    createSplitTransactions,
    handleSubmit,
    getSellValueSourceLabel,
    onSelectNisaAsset,
    onSelectSellablePosition,
    clearSellablePositionCache,
  } = form

  return (
    <Sheet open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <SheetContent side="right" className="w-80 sm:w-96 overflow-y-auto">
        <SheetHeader>
          <SheetTitle className="text-sm">{t("transactions.form.title")}</SheetTitle>
        </SheetHeader>

        {hasNoAccounts ? (
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
            <div className="space-y-1">
              <p className="text-xs font-medium">{t("transactions.form.account")}</p>
              <select
                aria-label={t("transactions.form.account")}
                value={accountId}
                onChange={(event) => {
                  setAccountId(event.target.value)
                  clearSellablePositionCache()
                  const nextAccountId = Number(event.target.value)
                  const account = (accounts ?? []).find((item) => item.id === nextAccountId)
                  if (account?.currency) {
                    const accountCurrency = account.currency.toUpperCase()
                    setCurrency(accountCurrency)
                    if (isCashMovement) applyCashMovementDefaults(accountCurrency)
                  }
                  setInsufficientBalance(null)
                  setFieldErrors((prev) => ({ ...prev, account: undefined }))
                }}
                className="w-full text-xs border border-border rounded px-2 py-1.5 bg-background"
              >
                <option value="">{t("transactions.form.account_required")}</option>
                {(accounts ?? []).map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.name} ({account.broker})
                  </option>
                ))}
              </select>
              {selectedAccountId != null ? (
                <p className="text-[11px] text-muted-foreground">
                  {t("transactions.form.available_cash", {
                    currency,
                    amount: (selectedCurrencyCashBalance ?? 0).toLocaleString(undefined, {
                      maximumFractionDigits: 2,
                    }),
                  })}
                </p>
              ) : null}
              {shouldShowQuotaSummary ? (
                <p className="text-[11px] text-muted-foreground">
                  {wrapperQuotaQuery.isLoading
                    ? t("common.loading")
                    : selectedQuota
                      ? t("transactions.form.nisa_quota_summary", {
                          wrapper: t(`wrapper.${selectedWrapper}`),
                          remaining: selectedQuota.wrapper_annual_remaining.toLocaleString(undefined, {
                            maximumFractionDigits: 0,
                          }),
                          annual: (selectedQuota.wrapper_annual_used + selectedQuota.wrapper_annual_remaining).toLocaleString(
                            undefined,
                            { maximumFractionDigits: 0 },
                          ),
                        })
                      : t("transactions.form.nisa_quota_unavailable")}
                </p>
              ) : null}
              {transactionType === "BUY" && hasNoAccounts ? (
                <div className="rounded-md border border-amber-500/40 bg-amber-500/10 px-2 py-2 space-y-1">
                  <p className="text-[11px] text-amber-800 dark:text-amber-300">
                    {t("transactions.form.buy_no_account_banner")}
                  </p>
                  {onOpenAccounts ? (
                    <button
                      type="button"
                      className="text-[11px] text-primary hover:underline"
                      onClick={onOpenAccounts}
                    >
                      {t("transactions.form.create_account")}
                    </button>
                  ) : null}
                </div>
              ) : null}
              {transactionType !== "BUY" && hasNoAccounts ? (
                <div className="text-[11px] text-muted-foreground">
                  <p>{t("transactions.form.account_empty_hint")}</p>
                  {onOpenAccounts ? (
                    <button
                      type="button"
                      className="text-primary hover:underline"
                      onClick={onOpenAccounts}
                    >
                      {t("transactions.form.create_account")}
                    </button>
                  ) : null}
                </div>
              ) : null}
              {fieldErrors.account ? <p className="text-xs text-destructive">{fieldErrors.account}</p> : null}
              {transactionType === "BUY" && selectedAccountId != null && (selectedCurrencyCashBalance ?? 0) <= 0 ? (
                <p className="text-[11px] text-muted-foreground">{t("transactions.form.buy_no_balance_hint")}</p>
              ) : null}
              {selectedAccountId != null && (transactionType === "SELL" || transactionType === "DIVIDEND") ? (
                <p className="text-[11px] text-muted-foreground">
                  {t("transactions.form.proceeds_hint", {
                    account: selectedAccount?.name ?? t("transactions.form.account_required"),
                  })}
                </p>
              ) : null}
              {insufficientBalance ? (
                <div className="rounded-md border border-amber-500/40 bg-amber-500/10 px-2 py-1.5 space-y-1">
                  <p className="text-[11px] text-amber-800 dark:text-amber-300">
                    {t("transactions.form.insufficient_balance", {
                      available: insufficientBalance.available.toLocaleString(undefined, { maximumFractionDigits: 2 }),
                      required: insufficientBalance.required.toLocaleString(undefined, { maximumFractionDigits: 2 }),
                      currency,
                    })}
                  </p>
                  <button
                    type="button"
                    className="text-[11px] text-primary hover:underline"
                    onClick={() => {
                      const shortfall = Math.max(0, insufficientBalance.required - insufficientBalance.available)
                      setTransactionType("DEPOSIT")
                      setQuantity("1")
                      setPrice("")
                      setManualTotal(true)
                      setTotalAmount(shortfall > 0 ? String(shortfall) : "")
                      setInsufficientBalance(null)
                    }}
                  >
                    {t("transactions.form.deposit_cash")}
                  </button>
                </div>
              ) : null}
            </div>

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
                      setFieldErrors({})
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
                    <EligibilityBadge
                      result={eligibility}
                      loading={form.eligibilityQuery.isLoading}
                    />
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
                        disabled={splitSubmitting || addTransactionMutation.isPending}
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
                  onValueChange={(value) => setCategory(value as typeof category)}
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

            {!isCashMovement ? (
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-xs font-medium">{t("transactions.form.quantity")}</p>
                    {shouldShowSellPicker && selectedSellablePositionForDisplay ? (
                      <button
                        type="button"
                        className="text-[11px] text-primary hover:underline"
                        onClick={() => {
                          const maxQuantity = String(selectedSellablePositionForDisplay.quantity)
                          setQuantity(maxQuantity)
                          if (!manualTotal) setTotalAmount(computeTotalAmount(maxQuantity, price))
                          setFieldErrors((prev) => ({ ...prev, quantity: undefined }))
                        }}
                      >
                        {t("transactions.sell_picker.max")}
                      </button>
                    ) : null}
                  </div>
                  <Input
                    type="number"
                    step="any"
                    aria-label={t("transactions.form.quantity")}
                    value={quantity}
                    onChange={(event) => {
                      const nextQuantity = event.target.value
                      setQuantity(nextQuantity)
                      if (!manualTotal) setTotalAmount(computeTotalAmount(nextQuantity, price))
                      setFieldErrors((prev) => ({ ...prev, quantity: undefined }))
                    }}
                    className="text-xs"
                  />
                  {shouldShowSellPicker && selectedSellablePositionForDisplay ? (
                    <p className="text-[11px] text-muted-foreground">
                      {t("transactions.sell_picker.available", {
                        quantity: selectedSellablePositionForDisplay.quantity.toLocaleString(undefined, {
                          maximumFractionDigits: 6,
                        }),
                        unit:
                          (forcedCategory ?? category) === "Mutual_Fund"
                            ? t("transactions.sell_picker.unit_units")
                            : t("transactions.sell_picker.unit_shares"),
                      })}
                    </p>
                  ) : null}
                  {fieldErrors.quantity ? <p className="text-xs text-destructive">{fieldErrors.quantity}</p> : null}
                </div>
                <div className="space-y-1">
                  <p className="text-xs font-medium">{t("transactions.form.price")}</p>
                  <Input
                    type="number"
                    step="any"
                    aria-label={t("transactions.form.price")}
                    value={price}
                    onChange={(event) => {
                      const nextPrice = event.target.value
                      setPrice(nextPrice)
                      if (!manualTotal) setTotalAmount(computeTotalAmount(quantity, nextPrice))
                      setFieldErrors((prev) => ({ ...prev, price: undefined }))
                    }}
                    className="text-xs"
                  />
                  <p className="text-[11px] text-muted-foreground">{t("transactions.form.price_hint")}</p>
                  {fieldErrors.price ? <p className="text-xs text-destructive">{fieldErrors.price}</p> : null}
                </div>
              </div>
            ) : null}

            <div className="space-y-1">
              <p className="text-xs font-medium">
                {isCashMovement ? t("transactions.form.deposit_amount") : t("transactions.form.total_amount")}
              </p>
              <Input
                type="number"
                step="any"
                aria-label={t("transactions.form.total_amount")}
                value={totalAmount}
                onChange={(event) => {
                  setManualTotal(true)
                  setTotalAmount(event.target.value)
                  setFieldErrors((prev) => ({ ...prev, totalAmount: undefined }))
                }}
                className="text-xs"
              />
              {!isCashMovement ? (
                <div className="flex items-center justify-between gap-2">
                  {!manualTotal ? (
                    <p className="text-[11px] text-muted-foreground">{t("transactions.form.total_auto")}</p>
                  ) : (
                    <p className="text-[11px] text-muted-foreground">{t("transactions.form.total_manual")}</p>
                  )}
                  <button
                    type="button"
                    className="text-[11px] text-primary hover:underline"
                    onClick={() => {
                      setManualTotal(false)
                      setTotalAmount(computeTotalAmount(quantity, price))
                    }}
                  >
                    {t("transactions.form.use_auto_total")}
                  </button>
                </div>
              ) : null}
              {fieldErrors.totalAmount ? <p className="text-xs text-destructive">{fieldErrors.totalAmount}</p> : null}
            </div>

            {isCashMovement ? (
              <div className="space-y-1">
                <p className="text-xs font-medium">{t("transactions.form.currency")}</p>
                <select
                  aria-label={t("transactions.form.currency")}
                  value={currency}
                  onChange={(event) => {
                    const nextCurrency = event.target.value
                    setCurrency(nextCurrency)
                    applyCashMovementDefaults(nextCurrency)
                  }}
                  className="w-full text-xs border border-border rounded px-2 py-1.5 bg-background"
                >
                  {DISPLAY_CURRENCIES.map((displayCurrency) => (
                    <option key={displayCurrency} value={displayCurrency}>
                      {displayCurrency}
                    </option>
                  ))}
                </select>
              </div>
            ) : null}

            <div className="space-y-1">
              <p className="text-xs font-medium">{t("transactions.form.date")}</p>
              <Input
                type="date"
                aria-label={t("transactions.form.date")}
                value={transactionDate}
                onChange={(event) => {
                  setTransactionDate(event.target.value)
                  setFieldErrors((prev) => ({ ...prev, transactionDate: undefined }))
                }}
                className="text-xs"
              />
              {fieldErrors.transactionDate ? (
                <p className="text-xs text-destructive">{fieldErrors.transactionDate}</p>
              ) : null}
            </div>

            <div className="space-y-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="w-full text-xs"
                onClick={() => setMoreOptionsOpen((prev) => !prev)}
              >
                {moreOptionsOpen ? t("transactions.form.hide_more") : t("transactions.form.show_more")}
              </Button>

              {moreOptionsOpen ? (
                <div className="space-y-3 rounded-md border border-border p-3">
                  <div className="space-y-1">
                    <p className="text-xs font-medium">{t("transactions.form.holding_link")}</p>
                    <select
                      aria-label={t("transactions.form.holding_link")}
                      value={holdingId}
                      onChange={(event) => setHoldingId(event.target.value)}
                      className="w-full text-xs border border-border rounded px-2 py-1.5 bg-background"
                    >
                      <option value="">{t("transactions.form.holding_optional")}</option>
                      {holdingOptions.map((option) => (
                        <option key={option.id} value={option.id}>
                          {option.ticker}
                        </option>
                      ))}
                    </select>
                  </div>

                  {!isCashMovement ? (
                    <div className="space-y-1">
                      <p className="text-xs font-medium">{t("transactions.form.currency")}</p>
                      <select
                        aria-label={t("transactions.form.currency")}
                        value={currency}
                        onChange={(event) => {
                          setCurrency(event.target.value)
                        }}
                        className="w-full text-xs border border-border rounded px-2 py-1.5 bg-background"
                      >
                        {DISPLAY_CURRENCIES.map((displayCurrency) => (
                          <option key={displayCurrency} value={displayCurrency}>
                            {displayCurrency}
                          </option>
                        ))}
                      </select>
                    </div>
                  ) : null}

                  <div className="grid grid-cols-2 gap-2">
                    <div className="space-y-1">
                      <p className="text-xs font-medium">{t("transactions.form.fx_rate")}</p>
                      <Input
                        type="number"
                        step="any"
                        aria-label={t("transactions.form.fx_rate")}
                        value={fxRate}
                        onChange={(event) => {
                          setFxRate(event.target.value)
                          setFieldErrors((prev) => ({ ...prev, fxRate: undefined }))
                        }}
                        className="text-xs"
                      />
                      {fieldErrors.fxRate ? <p className="text-xs text-destructive">{fieldErrors.fxRate}</p> : null}
                    </div>
                    <div className="space-y-1">
                      <p className="text-xs font-medium">{t("transactions.form.fee")}</p>
                      <Input
                        type="number"
                        step="any"
                        aria-label={t("transactions.form.fee")}
                        value={fee}
                        onChange={(event) => {
                          setFee(event.target.value)
                          setFieldErrors((prev) => ({ ...prev, fee: undefined }))
                        }}
                        className="text-xs"
                      />
                      {fieldErrors.fee ? <p className="text-xs text-destructive">{fieldErrors.fee}</p> : null}
                    </div>
                  </div>

                  <div className="space-y-1">
                    <p className="text-xs font-medium">{t("transactions.form.note")}</p>
                    <textarea
                      value={note}
                      onChange={(event) => setNote(event.target.value)}
                      maxLength={500}
                      className="w-full min-h-[88px] rounded-md border border-border bg-background px-2 py-1.5 text-xs"
                      placeholder={t("transactions.form.note_placeholder")}
                    />
                  </div>
                </div>
              ) : null}
            </div>

            <Button
              className="w-full"
              size="sm"
              disabled={splitSubmitting || addTransactionMutation.isPending || selectedAccountId == null}
              onClick={handleSubmit}
            >
              {t("transactions.form.submit")}
            </Button>
          </div>
        )}
      </SheetContent>
    </Sheet>
  )
}
