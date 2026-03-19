/** Pure error-parsing utilities for transaction API responses. */

export function parseInsufficientBalance(err: unknown): { available: number; required: number } | null {
  const detail =
    err && typeof err === "object" && "detail" in err ? (err as { detail?: unknown }).detail : null
  if (!detail || typeof detail !== "object") return null
  const errorCode = "error_code" in detail ? (detail as { error_code?: unknown }).error_code : null
  if (errorCode !== "INSUFFICIENT_BALANCE") return null
  const available =
    "available" in detail && typeof (detail as { available?: unknown }).available === "number"
      ? (detail as { available: number }).available
      : 0
  const required =
    "required" in detail && typeof (detail as { required?: unknown }).required === "number"
      ? (detail as { required: number }).required
      : 0
  return { available, required }
}

export function parseEligibilityError(err: unknown): { reasons: string[]; suggestedWrapper?: string } | null {
  const detail =
    err && typeof err === "object" && "detail" in err ? (err as { detail?: unknown }).detail : null
  if (!detail || typeof detail !== "object") return null
  const errorCode = "error_code" in detail ? (detail as { error_code?: unknown }).error_code : null
  if (errorCode !== "ASSET_NOT_ELIGIBLE") return null
  const reasons =
    "reasons" in detail && Array.isArray((detail as { reasons?: unknown }).reasons)
      ? ((detail as { reasons: unknown[] }).reasons.filter((r) => typeof r === "string") as string[])
      : []
  const suggestedWrapper =
    "suggested_wrapper" in detail &&
    typeof (detail as { suggested_wrapper?: unknown }).suggested_wrapper === "string"
      ? (detail as { suggested_wrapper: string }).suggested_wrapper
      : undefined
  return { reasons, suggestedWrapper }
}
