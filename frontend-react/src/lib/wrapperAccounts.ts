import type { AccountResponse } from "@/api/types/account"

const JAPANESE_WRAPPERS = new Set(["nisa_growth", "nisa_tsumitate", "ideco", "tokutei"])

export function isJapaneseWrapperAccount(account: AccountResponse): boolean {
  const wrapper = (account.tax_wrapper ?? "").trim().toLowerCase()
  const market = (account.market ?? "").trim().toUpperCase()
  return JAPANESE_WRAPPERS.has(wrapper) && market === "JP"
}

export function getPreferredWrapperAccountMap(accounts: AccountResponse[] | undefined) {
  const map = new Map<string, { id: number; currency: string }>()
  for (const account of accounts ?? []) {
    if (account.id == null || !isJapaneseWrapperAccount(account)) continue
    const wrapper = (account.tax_wrapper ?? "").trim().toLowerCase()
    const currency = (account.currency || "JPY").toUpperCase()
    const existing = map.get(wrapper)
    // Keep the smallest account id to make selection deterministic.
    if (!existing || account.id < existing.id) {
      map.set(wrapper, { id: account.id, currency })
    }
  }
  return map
}
