/**
 * Shared domain types for the transaction form layer.
 *
 * Defined here (rather than in useAddTransactionForm) so sub-hooks
 * (useTransactionFormState, useTransactionQueries, useTransactionSubmit,
 * useTransactionValidation) can import them without creating a circular
 * dependency back to their parent coordinator.
 *
 * useAddTransactionForm re-exports everything from this module so all
 * existing consumers are unaffected.
 */
import { STOCK_CATEGORIES } from "@/lib/constants"

export type TransactionType = "BUY" | "SELL" | "DIVIDEND" | "DEPOSIT" | "WITHDRAWAL"
export type StockCategory = (typeof STOCK_CATEGORIES)[number]

export interface FieldErrors {
  account?: string
  ticker?: string
  quantity?: string
  price?: string
  totalAmount?: string
  transactionDate?: string
  fxRate?: string
  fee?: string
}

export type NisaEligibleAssetItem = {
  ticker: string
  fund_name?: string | null
  asset_type?: string | null
  trust_fee_pct?: number | null
}

export type SellablePositionItem = {
  ticker: string
  fund_name: string
  quantity: number
  cost_basis?: number | null
  current_price?: number | null
  market_value?: number | null
  currency: string
  value_source?: "live_price" | "cost_basis" | "unavailable"
}

export type NisaAssetTypeFilter = "all" | "mutual_fund" | "etf" | "stock" | "reit"
