import { MemoryRouter, Route, Routes } from "react-router-dom"
import { render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import Allocation from "../Allocation"

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: "en" },
  }),
}))

vi.mock("@/api/hooks/useAccounts", () => ({
  useAccounts: () => ({ data: [] }),
}))

vi.mock("@/api/hooks/useDashboard", () => ({
  useHoldings: () => ({ data: [], isLoading: false, dataUpdatedAt: Date.now() }),
  useProfile: () => ({ data: { id: 1, config: "{}", is_active: true }, isLoading: false }),
}))

vi.mock("@/api/hooks/useAllocation", () => ({
  useAllocRebalance: () => ({ data: null }),
  useCurrencyExposure: () => ({ data: null }),
  useStressTest: () => ({ data: null }),
  useWithdraw: () => ({ mutate: vi.fn() }),
}))

vi.mock("@/hooks/usePrivacyMode", () => ({
  usePrivacyMode: () => [false, vi.fn()],
}))

vi.mock("@/components/allocation/analysis/RebalanceAnalysis", () => ({
  RebalanceAnalysis: () => <div>rebalance-analysis</div>,
}))

vi.mock("@/components/allocation/tools/CurrencyExposure", () => ({
  CurrencyExposure: () => <div>currency-exposure</div>,
}))

vi.mock("@/components/allocation/tools/StressTest", () => ({
  StressTest: () => <div>stress-test</div>,
}))

vi.mock("@/components/allocation/tools/SmartWithdrawal", () => ({
  SmartWithdrawal: () => <div>smart-withdrawal</div>,
}))

vi.mock("@/components/allocation/tools/TargetAllocation", () => ({
  TargetAllocation: () => <div>target-allocation</div>,
}))

vi.mock("@/components/allocation/holdings/HoldingsManager", () => ({
  HoldingsManager: () => <div>holdings-manager</div>,
}))

vi.mock("@/components/allocation/settings/TelegramSettings", () => ({
  TelegramSettings: () => <div>telegram-settings</div>,
}))

vi.mock("@/components/allocation/settings/NotificationPreferences", () => ({
  NotificationPreferences: () => <div>notification-prefs</div>,
}))

vi.mock("@/components/allocation/settings/TerminologySettings", () => ({
  TerminologySettings: () => <div>terminology-settings</div>,
}))

vi.mock("@/components/allocation/accounts/AccountsTab", () => ({
  AccountsTab: () => <div>accounts-tab</div>,
}))

vi.mock("@/components/allocation/wrappers/QuotaDashboard", () => ({
  QuotaDashboard: () => <div>quota-dashboard</div>,
}))

vi.mock("@/components/allocation/transactions/AddTransactionSheet", () => ({
  AddTransactionSheet: () => null,
}))

function renderWithRoute(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/allocation" element={<Allocation />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe("Allocation page", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("does not render NISA wrapper cards in the actions tab", () => {
    renderWithRoute("/allocation?tab=actions")
    expect(screen.queryByText("smart-action-cards-content")).not.toBeInTheDocument()
    expect(screen.queryByText("asset-location-content")).not.toBeInTheDocument()
    expect(screen.queryByText("tsumitate-migration-content")).not.toBeInTheDocument()
  })

  it("renders actions tab teaser with description text", () => {
    renderWithRoute("/allocation?tab=actions")
    expect(screen.getByText("allocation.tab_teaser.actions_desc")).toBeInTheDocument()
  })
})
