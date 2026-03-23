export type SortMode = "alert_first" | "alphabetical" | "volatility"
export type FilterMode = "all" | "active_only"

export function isRateLimitError(err: unknown): boolean {
  if (err == null || typeof err !== "object") return false
  const obj = err as Record<string, unknown>
  if (obj.status === 429) return true
  if (obj.statusCode === 429) return true
  if (typeof obj.response === "object" && obj.response !== null) {
    const response = obj.response as Record<string, unknown>
    if (response.status === 429) return true
  }
  return false
}

export function getRetryAfterSeconds(err: unknown): number | null {
  if (err == null || typeof err !== "object") return null
  const obj = err as Record<string, unknown>

  const asPositiveInt = (value: unknown): number | null => {
    const n = typeof value === "string" ? Number.parseInt(value, 10) : Number(value)
    if (!Number.isFinite(n) || n <= 0) return null
    return Math.ceil(n)
  }

  const directRetry = asPositiveInt(obj.retry_after_seconds)
  if (directRetry !== null) return directRetry

  if (typeof obj.detail === "object" && obj.detail !== null) {
    const detail = obj.detail as Record<string, unknown>
    const detailRetry = asPositiveInt(detail.retry_after_seconds)
    if (detailRetry !== null) return detailRetry
  }

  if (typeof obj.response === "object" && obj.response !== null) {
    const response = obj.response as Record<string, unknown>
    const responseRetry = asPositiveInt(response.retry_after_seconds)
    if (responseRetry !== null) return responseRetry

    if (typeof response.headers === "object" && response.headers !== null) {
      const headers = response.headers as Record<string, unknown>
      const retryAfter =
        asPositiveInt(headers["retry-after"]) ?? asPositiveInt(headers["Retry-After"])
      if (retryAfter !== null) return retryAfter
    }
  }

  return null
}

/** Returns absolute (unsigned) % change — used for volatility sort. */
export function computeAbsChangePct(history: { close: number }[]): number | null {
  if (history.length < 2) return null
  const first = history[0].close
  const last = history[history.length - 1].close
  if (first <= 0) return null
  return Math.abs((last - first) / first) * 100
}
