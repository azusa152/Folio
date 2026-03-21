import createClient, { type Middleware } from "openapi-fetch"
import type { paths } from "./types/generated"

const REQUEST_TIMEOUT_MS = 30_000

// GET endpoints that need a longer timeout because they may compute on first load.
// Only applied to GET; POST sub-routes (e.g. /rebalance/drift-alert) remain at the default.
// Keyed by URL substring → timeout in ms.
const GET_TIMEOUT_OVERRIDES: Array<[string, number]> = [
  ["/rebalance", 120_000],
  ["/analytics/insights", 120_000],
]

function resolveTimeout(url: string, method: string): number {
  if (method === "GET") {
    for (const [pattern, ms] of GET_TIMEOUT_OVERRIDES) {
      if (url.includes(pattern)) return ms
    }
  }
  return REQUEST_TIMEOUT_MS
}

const client = createClient<paths>({ baseUrl: "/api" })

const authMiddleware: Middleware = {
  onRequest({ request }) {
    const apiKey = import.meta.env.VITE_API_KEY
    if (apiKey) {
      request.headers.set("X-API-Key", apiKey)
    }
    return request
  },
}

const timeoutMiddleware: Middleware = {
  onRequest({ request }) {
    const timeoutMs = resolveTimeout(request.url, request.method)
    const controller = new AbortController()
    const timerId = setTimeout(() => controller.abort(), timeoutMs)
    // Propagate cancellation from the original signal (e.g. React Query unmount)
    // and clear the timer to avoid a no-op abort after the request is gone.
    request.signal.addEventListener("abort", () => {
      clearTimeout(timerId)
      controller.abort()
    })
    return new Request(request, { signal: controller.signal })
  },
}

client.use(authMiddleware)
client.use(timeoutMiddleware)

export async function apiFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const controller = new AbortController()
  const timerId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
  const upstreamSignal = init?.signal
  if (upstreamSignal) {
    upstreamSignal.addEventListener("abort", () => controller.abort(), { once: true })
  }

  const headers = new Headers(init?.headers)
  const apiKey = import.meta.env.VITE_API_KEY
  if (apiKey) {
    headers.set("X-API-Key", apiKey)
  }

  try {
    return await fetch(input, {
      ...init,
      headers,
      signal: controller.signal,
    })
  } finally {
    clearTimeout(timerId)
  }
}

export default client
