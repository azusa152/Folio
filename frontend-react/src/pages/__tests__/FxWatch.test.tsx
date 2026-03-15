import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import FxWatch from "../FxWatch"

const mockUseCurrencyExposure = vi.fn()
const mockMutateProfile = vi.fn()

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: "en" },
  }),
}))

vi.mock("react-router-dom", () => ({
  useSearchParams: () => [new URLSearchParams("tab=overview"), vi.fn()],
}))

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

vi.mock("@/api/hooks/useFxWatch", () => ({
  useFxWatches: () => ({ data: [], isLoading: false, isError: false }),
  useFxAnalysis: () => ({ data: { by_watch_id: {} }, isLoading: false }),
  useCheckFxWatches: () => ({ mutate: vi.fn(), isPending: false }),
  useAlertFxWatches: () => ({ mutate: vi.fn(), isPending: false }),
  useFxHistoryMap: () => ({ data: {} }),
  useRefreshFxRates: () => ({ mutate: vi.fn(), isPending: false }),
}))

vi.mock("@/api/hooks/useAllocation", () => ({
  useCurrencyExposure: (...args: unknown[]) => mockUseCurrencyExposure(...args),
  useUpdateProfile: () => ({ mutate: mockMutateProfile, isPending: false }),
}))

vi.mock("@/api/hooks/useDashboard", () => ({
  useProfile: () => ({ data: { id: 1, home_currency: "USD" } }),
}))

vi.mock("@/hooks/usePrivacyMode", () => ({
  usePrivacyMode: () => false,
}))

vi.mock("@/components/fxwatch/WatchCard", () => ({
  WatchCard: () => null,
}))

vi.mock("@/components/fxwatch/AddWatchDialog", () => ({
  AddWatchDialog: () => null,
}))

vi.mock("@/components/allocation/tools/CurrencyExposure", () => ({
  CurrencyExposure: () => null,
}))

vi.mock("@/components/fxwatch/PortfolioImpactSnapshot", () => ({
  PortfolioImpactSnapshot: (props: {
    selectedCurrency: string
    onCurrencyChange: (currency: string) => void
    showSaveDefault?: boolean
    onSaveDefault?: () => void
    showResetCurrency?: boolean
    onResetCurrency?: () => void
  }) => (
    <div>
      <p data-testid="selected-currency">{props.selectedCurrency}</p>
      <button onClick={() => props.onCurrencyChange("JPY")}>change-currency</button>
      {props.showSaveDefault ? <button onClick={props.onSaveDefault}>save-default</button> : null}
      {props.showResetCurrency ? <button onClick={props.onResetCurrency}>reset-currency</button> : null}
    </div>
  ),
}))

describe("FxWatch home currency behavior", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseCurrencyExposure.mockReturnValue({
      data: {
        home_currency: "USD",
        total_value_home: 0,
        breakdown: [],
        non_home_pct: 0,
        cash_breakdown: [],
        cash_non_home_pct: 0,
        total_cash_home: 0,
        fx_movements: [],
        fx_rate_alerts: [],
        risk_level: "low",
        advice: [],
        calculated_at: "2026-03-15T00:00:00Z",
      },
    })
  })

  it("applies temporary currency override and allows reset", async () => {
    render(<FxWatch />)

    expect(mockUseCurrencyExposure).toHaveBeenCalledWith(true, "USD")
    expect(screen.getByTestId("selected-currency")).toHaveTextContent("USD")
    expect(screen.queryByText("save-default")).not.toBeInTheDocument()
    expect(screen.queryByText("reset-currency")).not.toBeInTheDocument()

    fireEvent.click(screen.getByText("change-currency"))

    await waitFor(() => expect(mockUseCurrencyExposure).toHaveBeenLastCalledWith(true, "JPY"))
    expect(screen.getByTestId("selected-currency")).toHaveTextContent("JPY")
    expect(screen.getByText("save-default")).toBeInTheDocument()
    expect(screen.getByText("reset-currency")).toBeInTheDocument()

    fireEvent.click(screen.getByText("reset-currency"))
    await waitFor(() => expect(mockUseCurrencyExposure).toHaveBeenLastCalledWith(true, "USD"))
    expect(screen.getByTestId("selected-currency")).toHaveTextContent("USD")
  })

  it("saves selected currency as new default", async () => {
    render(<FxWatch />)

    fireEvent.click(screen.getByText("change-currency"))
    fireEvent.click(await screen.findByText("save-default"))

    expect(mockMutateProfile).toHaveBeenCalledWith(
      { id: 1, payload: { home_currency: "JPY" } },
      expect.objectContaining({
        onSuccess: expect.any(Function),
        onError: expect.any(Function),
      }),
    )
  })
})
