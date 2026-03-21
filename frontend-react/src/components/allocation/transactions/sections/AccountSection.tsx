import { useTranslation } from "react-i18next"
import type { TransactionType } from "@/hooks/useAddTransactionForm"
import type { FieldErrors } from "@/hooks/useAddTransactionForm"
import type { UseQueryResult } from "@tanstack/react-query"

interface WrapperQuotaData {
  quotas?: Record<string, { wrapper_annual_remaining: number; wrapper_annual_used: number }>
}

interface AccountItem {
  id?: number
  name?: string
  broker?: string
  currency?: string
  tax_wrapper?: string | null
}

interface AccountSectionProps {
  accountId: string
  accounts: AccountItem[] | undefined
  transactionType: TransactionType
  isCashMovement: boolean
  currency: string
  selectedAccountId: number | null
  selectedCurrencyCashBalance: number | null
  selectedAccount: AccountItem | undefined
  shouldShowQuotaSummary: boolean
  selectedWrapper: string
  selectedQuota: { wrapper_annual_remaining: number; wrapper_annual_used: number } | undefined
  wrapperQuotaQuery: UseQueryResult<WrapperQuotaData>
  hasNoAccounts: boolean
  fieldErrors: FieldErrors
  insufficientBalance: { available: number; required: number } | null
  onOpenAccounts?: () => void
  setAccountId: (id: string) => void
  setCurrency: (c: string) => void
  setTransactionType: (t: TransactionType) => void
  setQuantity: (q: string) => void
  setPrice: (p: string) => void
  setManualTotal: (m: boolean) => void
  setTotalAmount: (a: string) => void
  setInsufficientBalance: (v: { available: number; required: number } | null) => void
  setFieldErrors: (updater: (prev: FieldErrors) => FieldErrors) => void
  applyCashMovementDefaults: (currency: string) => void
  clearSellablePositionCache: () => void
}

export function AccountSection({
  accountId,
  accounts,
  transactionType,
  isCashMovement,
  currency,
  selectedAccountId,
  selectedCurrencyCashBalance,
  selectedAccount,
  shouldShowQuotaSummary,
  selectedWrapper,
  selectedQuota,
  wrapperQuotaQuery,
  hasNoAccounts,
  fieldErrors,
  insufficientBalance,
  onOpenAccounts,
  setAccountId,
  setCurrency,
  setTransactionType,
  setQuantity,
  setPrice,
  setManualTotal,
  setTotalAmount,
  setInsufficientBalance,
  setFieldErrors,
  applyCashMovementDefaults,
  clearSellablePositionCache,
}: AccountSectionProps) {
  const { t } = useTranslation()

  return (
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
                  annual: (
                    selectedQuota.wrapper_annual_used + selectedQuota.wrapper_annual_remaining
                  ).toLocaleString(undefined, { maximumFractionDigits: 0 }),
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
            <button type="button" className="text-primary hover:underline" onClick={onOpenAccounts}>
              {t("transactions.form.create_account")}
            </button>
          ) : null}
        </div>
      ) : null}
      {fieldErrors.account ? (
        <p className="text-xs text-destructive">{fieldErrors.account}</p>
      ) : null}
      {transactionType === "BUY" &&
      selectedAccountId != null &&
      (selectedCurrencyCashBalance ?? 0) <= 0 ? (
        <p className="text-[11px] text-muted-foreground">
          {t("transactions.form.buy_no_balance_hint")}
        </p>
      ) : null}
      {selectedAccountId != null &&
      (transactionType === "SELL" || transactionType === "DIVIDEND") ? (
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
              available: insufficientBalance.available.toLocaleString(undefined, {
                maximumFractionDigits: 2,
              }),
              required: insufficientBalance.required.toLocaleString(undefined, {
                maximumFractionDigits: 2,
              }),
              currency,
            })}
          </p>
          <button
            type="button"
            className="text-[11px] text-primary hover:underline"
            onClick={() => {
              const shortfall = Math.max(
                0,
                insufficientBalance.required - insufficientBalance.available,
              )
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
  )
}
