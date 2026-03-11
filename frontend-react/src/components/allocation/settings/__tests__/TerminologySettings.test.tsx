import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { TerminologySettings } from "../TerminologySettings"

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}))

const mockMutate = vi.fn()

vi.mock("@/api/hooks/useAllocation", () => ({
  usePreferences: () => ({
    data: { terminology_mode: "simplified" },
  }),
  useSavePreferences: () => ({
    mutate: mockMutate,
    isPending: false,
  }),
}))

vi.mock("@/hooks/usePrivacyMode", () => ({
  useIsPrivate: () => false,
}))

describe("TerminologySettings", () => {
  it("renders the hint text", () => {
    render(<TerminologySettings />)
    expect(screen.getByText("terminology_settings.terminology_hint")).toBeInTheDocument()
  })

  it("shows simplified as the default selected value", () => {
    render(<TerminologySettings />)
    expect(screen.getByText("terminology_settings.mode_simplified")).toBeInTheDocument()
  })
})
