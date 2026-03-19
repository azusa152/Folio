import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { QuotaDashboard } from "../QuotaDashboard"

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: "en" },
  }),
}))

vi.mock("@/api/hooks/useWrappers", () => ({
  useWrapperQuota: () => ({
    data: {
      restoration_policy: "next_year",
      quotas: {
        nisa_tsumitate: {
          wrapper: "nisa_tsumitate",
          wrapper_annual_used: 50000,
          wrapper_annual_remaining: 70000,
          lifetime_used: 200000,
          lifetime_remaining: 1600000,
        },
        nisa_growth: {
          wrapper: "nisa_growth",
          wrapper_annual_used: 100000,
          wrapper_annual_remaining: 140000,
          lifetime_used: 200000,
          lifetime_remaining: 1600000,
          growth_sub_limit_used: 80000,
          growth_sub_limit_remaining: 1120000,
        },
      },
    },
    isLoading: false,
  }),
  useRestorationForecast: () => ({
    data: { pending: [] },
    isLoading: false,
  }),
}))

describe("QuotaDashboard tooltip accessibility", () => {
  it("renders progress bars as focusable buttons with aria-labels", () => {
    render(<QuotaDashboard />)

    const progressButtons = screen.getAllByRole("button")
    expect(progressButtons.length).toBeGreaterThanOrEqual(4)

    for (const button of progressButtons) {
      expect(button).toHaveAttribute("aria-label")
      expect(button.getAttribute("aria-label")).toContain("wrapper.dashboard.progress_tooltip")
    }
  })
})
