import { apiFetch } from "@/api/client"

/**
 * Download a CSV file from the given API path.
 *
 * Uses `apiFetch` so auth headers and the 30 s timeout are applied
 * consistently with all other API calls.  Falls back to the path stem
 * as the filename when no Content-Disposition header is present.
 */
export async function downloadCsvFromApi(
  path: string,
  params?: Record<string, string>,
  fallbackFilename = "export.csv",
): Promise<void> {
  const url = params
    ? `${path}?${new URLSearchParams(params).toString()}`
    : path

  const response = await apiFetch(url)
  if (!response.ok) throw new Error(response.statusText)

  const blob = await response.blob()
  const objectUrl = URL.createObjectURL(blob)
  const link = document.createElement("a")

  const contentDisposition = response.headers.get("Content-Disposition") ?? ""
  const filenameMatch = contentDisposition.match(/filename="([^"]+)"/)
  link.download = filenameMatch?.[1] ?? fallbackFilename
  link.href = objectUrl
  link.click()
  URL.revokeObjectURL(objectUrl)
}
