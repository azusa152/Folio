import { fireEvent, render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { ContributionsTab } from "../ContributionsTab"

const { refetchMock, useWrapperContributionsMock } = vi.hoisted(() => ({
  refetchMock: vi.fn(),
  useWrapperContributionsMock: vi.fn(),
}))

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, string>) =>
      params?.amount ? `${key}:${params.amount}` : key,
    i18n: { language: "en" },
  }),
}))

vi.mock("@/api/hooks/useWrappers", () => ({
  useWrapperContributions: (...args: unknown[]) => useWrapperContributionsMock(...args),
}))

describe("ContributionsTab", () => {
  it("shows explicit error state and supports retry", () => {
    useWrapperContributionsMock.mockReturnValue({
      isLoading: false,
      isError: true,
      data: undefined,
      refetch: refetchMock,
    })

    render(<ContributionsTab />)

    expect(screen.getByText("nisa.contributions.error_title")).toBeInTheDocument()
    expect(screen.getByText("nisa.contributions.error_hint")).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: "nisa.contributions.retry" }))
    expect(refetchMock).toHaveBeenCalledTimes(1)
  })

  it("shows empty state only when request succeeds with no rows", () => {
    useWrapperContributionsMock.mockReturnValue({
      isLoading: false,
      isError: false,
      data: { count: 0, items: [] },
      refetch: refetchMock,
    })

    render(<ContributionsTab />)

    expect(screen.getByText("nisa.contributions.empty")).toBeInTheDocument()
    expect(screen.queryByText("nisa.contributions.error_title")).not.toBeInTheDocument()
  })
})
