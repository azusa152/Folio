import type { components } from "./generated"

export type TransactionRequest = components["schemas"]["TransactionRequest"] & {
  account_id?: number
}
export type TransactionResponse = components["schemas"]["TransactionResponse"] & {
  account_id?: number | null
}
