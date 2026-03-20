import { useTranslation } from "react-i18next"
import { Button } from "@/components/ui/button"
import { EligibilityBadge } from "@/components/common/EligibilityBadge"
import { ELIGIBILITY_CHECK_WRAPPERS } from "@/lib/constants"
import type { UseQueryResult } from "@tanstack/react-query"
import type { TransactionType } from "@/hooks/useAddTransactionForm"

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
  currency?: string
}

interface RoutingSuggestionItem {
  wrapper: string
  amount: number
  reason: string
}

interface RoutingSuggestionData {
  suggestions?: RoutingSuggestionItem[]
}

interface Props {
  transactionType: TransactionType
  selectedWrapper: string
  eligibility: EligibilityResult | undefined | null
  eligibilityQueryIsLoading: boolean
  suggestedAccount: AccountItem | null | undefined
  routingSuggestionQuery: UseQueryResult<RoutingSuggestionData>
  routingSuggestedAccounts: Map<string, { id: number; currency: string }>
  canSplitPurchase: boolean
  splitSubmitting: boolean
  addTransactionMutationIsPending: boolean
  setAccountId: (id: string) => void
  setCurrency: (c: string) => void
  setInsufficientBalance: (v: { available: number; required: number } | null) => void
  createSplitTransactions: () => Promise<void>
}

export function RoutingSuggestion({
  transactionType,
  selectedWrapper,
  eligibility,
  eligibilityQueryIsLoading,
  suggestedAccount,
  routingSuggestionQuery,
  routingSuggestedAccounts,
  canSplitPurchase,
  splitSubmitting,
  addTransactionMutationIsPending,
  setAccountId,
  setCurrency,
  setInsufficientBalance,
  createSplitTransactions,
}: Props) {
  const { t } = useTranslation()

  const showEligibility = transactionType === "BUY" && ELIGIBILITY_CHECK_WRAPPERS.has(selectedWrapper)
  const suggestions = routingSuggestionQuery.data?.suggestions

  if (!showEligibility && !suggestions?.length) return null

  return (
    <div className="space-y-1">
      {showEligibility ? (
        <>
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
                      const nextCurrency = (suggestedAccount.currency || "USD").toUpperCase()
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
        </>
      ) : null}

      {transactionType === "BUY" && suggestions?.length ? (
        <div className="pt-1 space-y-1">
          <p className="text-[11px] font-medium">{t("routing.suggest_title")}</p>
          <div className="space-y-1">
            {suggestions.map((item, idx) => {
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
    </div>
  )
}
