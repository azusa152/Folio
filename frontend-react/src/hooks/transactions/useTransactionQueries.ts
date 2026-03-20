import { useMemo } from "react"
import { useAccountCashBalances, useAccountSellablePositions } from "@/api/hooks/useAccounts"
import { useEligibleAssets, useSuggestRouting, useWrapperEligibility, useWrapperQuota } from "@/api/hooks/useWrappers"
import type { AccountResponse } from "@/api/types/account"
import type { NisaAssetTypeFilter, StockCategory } from "./types"

interface Props {
  open: boolean
  accounts: AccountResponse[] | undefined
  selectedAccountId: number | null
  selectedWrapper: string
  selectedAccountBroker: string | undefined
  currency: string
  ticker: string
  totalAmount: string
  shouldShowNisaPicker: boolean
  shouldShowSellPicker: boolean
  shouldCheckEligibility: boolean
  shouldSuggestRouting: boolean
  shouldShowQuotaSummary: boolean
  nisaStockFreeInput: boolean
  nisaPickerSearch: string
  nisaAssetTypeFilter: NisaAssetTypeFilter
}

/**
 * Encapsulates all API query calls that depend on form-derived state values,
 * plus their immediately-computed derivatives (eligibility, routing plan, etc.)
 */
export function useTransactionQueries({
  open,
  accounts,
  selectedAccountId,
  selectedWrapper,
  selectedAccountBroker,
  currency,
  ticker,
  totalAmount,
  shouldShowNisaPicker,
  shouldShowSellPicker,
  shouldCheckEligibility,
  shouldSuggestRouting,
  shouldShowQuotaSummary,
  nisaStockFreeInput,
  nisaPickerSearch,
  nisaAssetTypeFilter,
}: Props) {
  const cashBalancesQuery = useAccountCashBalances(selectedAccountId, open)
  const selectedCurrencyCashBalance =
    (cashBalancesQuery.data ?? []).find((b) => b.currency.toUpperCase() === currency.toUpperCase())?.balance ?? null

  const nisaEligibleAssetsQuery = useEligibleAssets(shouldShowNisaPicker ? selectedWrapper : undefined, {
    search: nisaPickerSearch || undefined,
    assetType: nisaAssetTypeFilter === "all" ? undefined : nisaAssetTypeFilter,
    limit: 50,
    enabled: shouldShowNisaPicker && !nisaStockFreeInput,
  })
  const nisaReitFreeInput =
    shouldShowNisaPicker &&
    selectedWrapper === "nisa_growth" &&
    nisaAssetTypeFilter === "reit" &&
    nisaEligibleAssetsQuery.isFetched &&
    (nisaEligibleAssetsQuery.data?.items?.length ?? 0) === 0
  const nisaFreeTickerInput = nisaStockFreeInput || nisaReitFreeInput

  const sellablePositionsQuery = useAccountSellablePositions(selectedAccountId, shouldShowSellPicker)

  const routingSuggestionQuery = useSuggestRouting(
    ticker,
    Number.isFinite(Number(totalAmount)) ? Number(totalAmount) : null,
    shouldSuggestRouting,
  )

  const eligibilityQuery = useWrapperEligibility(
    selectedWrapper || undefined,
    ticker,
    selectedAccountBroker,
    shouldCheckEligibility,
  )
  const eligibility = eligibilityQuery.data

  const forcedCategory = useMemo<StockCategory | null>(() => {
    if (selectedWrapper === "nisa_tsumitate") return "Mutual_Fund"
    if (eligibility?.asset_type === "mutual_fund") return "Mutual_Fund"
    return null
  }, [eligibility?.asset_type, selectedWrapper])

  const suggestedAccount = useMemo(() => {
    const suggestedWrapper = eligibility?.suggested_wrapper
    if (!suggestedWrapper) return null
    return (accounts ?? []).find((account) => {
      if (account.id == null || account.id === selectedAccountId) return false
      const wrapper = typeof account.tax_wrapper === "string" ? account.tax_wrapper.toLowerCase() : ""
      return wrapper === suggestedWrapper
    })
  }, [accounts, eligibility?.suggested_wrapper, selectedAccountId])

  const routingSuggestedAccounts = useMemo(() => {
    const byWrapper = new Map<string, { id: number; currency: string }>()
    for (const account of accounts ?? []) {
      if (account.id == null) continue
      const wrapper = typeof account.tax_wrapper === "string" ? account.tax_wrapper.toLowerCase() : ""
      if (!wrapper || byWrapper.has(wrapper)) continue
      byWrapper.set(wrapper, { id: account.id, currency: (account.currency || "USD").toUpperCase() })
    }
    return byWrapper
  }, [accounts])

  const splitRoutingPlan = useMemo(() => {
    const suggestions = routingSuggestionQuery.data?.suggestions ?? []
    return suggestions
      .map((item) => ({
        wrapper: item.wrapper,
        amount: Number(item.amount),
        account: routingSuggestedAccounts.get(item.wrapper) ?? null,
      }))
      .filter((item) => item.amount > 0)
  }, [routingSuggestionQuery.data?.suggestions, routingSuggestedAccounts])

  const wrapperQuotaQuery = useWrapperQuota(shouldShowQuotaSummary)
  const selectedQuota = shouldShowQuotaSummary ? wrapperQuotaQuery.data?.quotas?.[selectedWrapper] : undefined

  return {
    cashBalancesQuery,
    selectedCurrencyCashBalance,
    nisaEligibleAssetsQuery,
    nisaReitFreeInput,
    nisaFreeTickerInput,
    sellablePositionsQuery,
    routingSuggestionQuery,
    eligibilityQuery,
    eligibility,
    forcedCategory,
    suggestedAccount,
    routingSuggestedAccounts,
    splitRoutingPlan,
    canSplitPurchase:
      splitRoutingPlan.length >= 2 && splitRoutingPlan.every((item) => item.account != null),
    wrapperQuotaQuery,
    selectedQuota,
  }
}
