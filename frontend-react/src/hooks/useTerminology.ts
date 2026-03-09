import { useCallback } from "react"
import { useTranslation } from "react-i18next"
import { usePreferences } from "@/api/hooks/useAllocation"

/**
 * Returns a term resolver that picks expert or simplified labels
 * based on the user's terminology_mode preference.
 *
 * Usage:
 *   const { term } = useTerminology()
 *   <span>{term("twr")}</span>
 *   // → "TWR" in expert mode, "Portfolio Return" in simplified mode
 */
export function useTerminology() {
  const { t } = useTranslation()
  const { data: prefs } = usePreferences()
  const mode = prefs?.terminology_mode ?? "simplified"

  const term = useCallback(
    (key: string, fallback?: string): string => {
      if (mode === "simplified") {
        const simplified = t(`simple.${key}`, { defaultValue: "" })
        if (simplified) return simplified
      }
      return fallback ?? t(key)
    },
    [mode, t],
  )

  return { term, isSimplified: mode === "simplified" }
}
