import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook } from "@testing-library/react"

const mockT = vi.fn((key: string, opts?: { defaultValue?: string }) => {
  const translations: Record<string, string> = {
    "simple.twr": "Portfolio Return",
    "simple.drift": "Balance Gap",
    "simple.cost_basis": "Purchase Cost",
  }
  return translations[key] ?? opts?.defaultValue ?? key
})

const mockPrefs = vi.fn<() => { data: { terminology_mode: string } | undefined }>(() => ({
  data: { terminology_mode: "simplified" },
}))

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: mockT }),
}))

vi.mock("@/api/hooks/useAllocation", () => ({
  usePreferences: () => mockPrefs(),
}))

import { useTerminology } from "../useTerminology"

beforeEach(() => {
  vi.clearAllMocks()
  mockPrefs.mockReturnValue({ data: { terminology_mode: "simplified" } })
})

describe("useTerminology", () => {
  it("returns simplified term when mode is 'simplified'", () => {
    const { result } = renderHook(() => useTerminology())
    expect(result.current.term("twr")).toBe("Portfolio Return")
    expect(result.current.isSimplified).toBe(true)
  })

  it("returns fallback when simplified translation is missing", () => {
    const { result } = renderHook(() => useTerminology())
    expect(result.current.term("unknown_key", "Fallback Label")).toBe("Fallback Label")
  })

  it("returns expert term (falls through to fallback) in expert mode", () => {
    mockPrefs.mockReturnValue({ data: { terminology_mode: "expert" } })
    const { result } = renderHook(() => useTerminology())
    expect(result.current.term("twr", "TWR")).toBe("TWR")
    expect(result.current.isSimplified).toBe(false)
  })

  it("defaults to simplified when prefs are undefined", () => {
    mockPrefs.mockReturnValue({ data: undefined })
    const { result } = renderHook(() => useTerminology())
    expect(result.current.isSimplified).toBe(true)
    expect(result.current.term("drift", "Drift")).toBe("Balance Gap")
  })

  it("returns i18n key as last resort when no fallback given", () => {
    mockPrefs.mockReturnValue({ data: { terminology_mode: "expert" } })
    const { result } = renderHook(() => useTerminology())
    expect(result.current.term("no_such_key")).toBe("no_such_key")
  })
})
