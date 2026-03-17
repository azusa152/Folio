import { MemoryRouter, Route, Routes } from "react-router-dom"
import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import Nisa from "../Nisa"

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}))

vi.mock("@/api/hooks/useWrappers", () => ({
  useEligibleAssetsMetadata: () => ({ data: { last_refreshed_at: null } }),
}))

vi.mock("@/components/nisa/EligibleAssetsTab", () => ({
  EligibleAssetsTab: () => <div>eligible-tab-content</div>,
}))

vi.mock("@/components/nisa/ContributionsTab", () => ({
  ContributionsTab: () => <div>contributions-tab-content</div>,
}))

vi.mock("@/components/nisa/DataManagementTab", () => ({
  DataManagementTab: () => <div>data-tab-content</div>,
}))

vi.mock("@/components/allocation/wrappers/QuotaDashboard", () => ({
  QuotaDashboard: () => <div>quota-tab-content</div>,
}))

vi.mock("@/components/nisa/NisaEducationCard", () => ({
  NisaEducationCard: () => <div>education-card-content</div>,
}))

function renderWithRoute(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/nisa" element={<Nisa />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe("Nisa page tab routing", () => {
  it("defaults to eligible tab when query tab is missing/invalid", () => {
    renderWithRoute("/nisa?tab=unknown")
    expect(screen.getByText("eligible-tab-content")).toBeInTheDocument()
    expect(screen.queryByText("data-tab-content")).not.toBeInTheDocument()
  })

  it("opens data tab when ?tab=data is provided", () => {
    renderWithRoute("/nisa?tab=data")
    expect(screen.getByText("data-tab-content")).toBeInTheDocument()
    expect(screen.queryByText("eligible-tab-content")).not.toBeInTheDocument()
  })
})
