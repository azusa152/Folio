import { MemoryRouter, Route, Routes } from "react-router-dom"
import { render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import Nisa from "../Nisa"

const mockUseAccounts = vi.fn()
const mockUseAllocRebalance = vi.fn()

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}))

vi.mock("@/api/hooks/useWrappers", () => ({
  useEligibleAssetsMetadata: () => ({ data: { last_refreshed_at: null } }),
  useSyncNav: () => ({ mutate: vi.fn(), isPending: false }),
}))

vi.mock("@/api/hooks/useAccounts", () => ({
  useAccounts: () => mockUseAccounts(),
}))

vi.mock("@/api/hooks/useAllocation", () => ({
  useAllocRebalance: (...args: unknown[]) => mockUseAllocRebalance(...args),
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

vi.mock("@/components/allocation/wrappers/SmartActionCards", () => ({
  SmartActionCards: (props: { forceHideActions?: boolean; emptyHintKey?: string }) =>
    props.forceHideActions ? <div>{props.emptyHintKey ?? "nisa.actions.empty"}</div> : <div>smart-action-cards-content</div>,
}))

vi.mock("@/components/allocation/wrappers/AssetLocationViz", () => ({
  AssetLocationViz: () => <div>asset-location-content</div>,
}))

vi.mock("@/components/allocation/wrappers/TsumitateMigrationCard", () => ({
  TsumitateMigrationCard: () => <div>tsumitate-migration-content</div>,
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
  beforeEach(() => {
    mockUseAccounts.mockReset()
    mockUseAllocRebalance.mockReset()
    mockUseAllocRebalance.mockReturnValue({
      data: {
        wrapper_allocations: [{ wrapper: "nisa_growth", amount: 120000, ratio: 0.5 }],
        placement_suggestions: [],
        tax_efficiency_score: 70,
        tax_savings_estimate: 12345,
        tsumitate_migration: null,
      },
    })
  })

  it("defaults to eligible tab when query tab is missing/invalid", () => {
    mockUseAccounts.mockReturnValue({ data: [] })
    renderWithRoute("/nisa?tab=unknown")
    expect(screen.getByText("eligible-tab-content")).toBeInTheDocument()
    expect(screen.queryByText("data-tab-content")).not.toBeInTheDocument()
  })

  it("opens data tab when ?tab=data is provided", () => {
    mockUseAccounts.mockReturnValue({ data: [] })
    renderWithRoute("/nisa?tab=data")
    expect(screen.getByText("data-tab-content")).toBeInTheDocument()
    expect(screen.queryByText("eligible-tab-content")).not.toBeInTheDocument()
  })

  it("opens actions tab when ?tab=actions is provided", () => {
    mockUseAccounts.mockReturnValue({
      data: [{ id: 1, tax_wrapper: "nisa_growth", currency: "JPY", market: "JP" }],
    })
    renderWithRoute("/nisa?tab=actions")
    expect(screen.getByText("smart-action-cards-content")).toBeInTheDocument()
    expect(screen.getByText("asset-location-content")).toBeInTheDocument()
  })

  it("shows empty hint in actions tab when JP wrapper account is missing", () => {
    mockUseAccounts.mockReturnValue({
      data: [{ id: 1, tax_wrapper: "nisa_growth", currency: "JPY", market: "US" }],
    })
    renderWithRoute("/nisa?tab=actions")
    expect(screen.getByText("nisa.actions.empty")).toBeInTheDocument()
    expect(mockUseAllocRebalance).toHaveBeenCalledWith("JPY", false)
  })
})
