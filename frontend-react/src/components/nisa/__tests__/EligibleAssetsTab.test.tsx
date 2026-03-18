import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { describe, expect, it, vi } from "vitest"
import { EligibleAssetsTab } from "../EligibleAssetsTab"

const { useEligibleAssetsMock } = vi.hoisted(() => ({
  useEligibleAssetsMock: vi.fn(),
}))

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, number>) =>
      params ? `${key}:${params.count ?? ""}:${params.total ?? ""}` : key,
  }),
}))

vi.mock("@/api/hooks/useWrappers", () => ({
  useEligibleAssets: (...args: unknown[]) => useEligibleAssetsMock(...args),
}))

function renderTab() {
  return render(
    <MemoryRouter>
      <EligibleAssetsTab />
    </MemoryRouter>,
  )
}

describe("EligibleAssetsTab", () => {
  it("applies asset-type filter and supports load-more pagination", async () => {
    useEligibleAssetsMock.mockImplementation((wrapper: string, options: { limit?: number }) => {
      if (wrapper === "nisa_tsumitate") {
        return {
          isLoading: false,
          isFetching: false,
          data: {
            count: 200,
            items: [
              {
                ticker: "AAA",
                fund_name: "Alpha Fund",
                asset_type: "mutual_fund",
                trust_fee_pct: 0.1,
              },
              {
                ticker: "BBB",
                fund_name: "Beta ETF",
                asset_type: "etf",
                trust_fee_pct: 0.2,
              },
            ],
          },
          options,
        }
      }
      return {
        isLoading: false,
        isFetching: false,
        data: { count: 0, items: [] },
        options,
      }
    })

    renderTab()

    expect(screen.getByText("Alpha Fund")).toBeInTheDocument()
    expect(screen.getByText("Beta ETF")).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText("nisa.eligible.filter_asset_type"), {
      target: { value: "etf" },
    })
    expect(screen.queryByText("Alpha Fund")).not.toBeInTheDocument()
    expect(screen.getByText("Beta ETF")).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: "nisa.eligible.load_more" }))
    await waitFor(() => {
      expect(useEligibleAssetsMock).toHaveBeenCalledWith(
        "nisa_tsumitate",
        expect.objectContaining({ limit: 100 }),
      )
    })
  })

  it("shows filter-mismatch empty state when data exists but filter excludes all", () => {
    useEligibleAssetsMock.mockImplementation((wrapper: string) => {
      if (wrapper === "nisa_tsumitate") {
        return {
          isLoading: false,
          isFetching: false,
          data: {
            count: 1,
            items: [
              { ticker: "AAA", fund_name: "Alpha Fund", asset_type: "mutual_fund", trust_fee_pct: 0.1 },
            ],
          },
        }
      }
      return { isLoading: false, isFetching: false, data: { count: 0, items: [] } }
    })

    renderTab()

    fireEvent.change(screen.getByLabelText("nisa.eligible.filter_asset_type"), {
      target: { value: "etf" },
    })

    expect(screen.getByText("nisa.eligible.filter_no_match_title")).toBeInTheDocument()
    expect(screen.getByText("nisa.eligible.filter_no_match")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "nisa.eligible.clear_filter" })).toBeInTheDocument()
  })

  it("shows data-empty state when API returns no items", () => {
    useEligibleAssetsMock.mockReturnValue({
      isLoading: false,
      isFetching: false,
      data: { count: 0, items: [] },
    })

    renderTab()

    expect(screen.getByText("nisa.eligible.empty_title")).toBeInTheDocument()
    expect(screen.getByText("nisa.eligible.empty")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "nisa.eligible.empty_cta" })).toHaveAttribute("href", "/nisa?tab=data")
  })

  it("clears filter when clear-filter button is clicked", () => {
    useEligibleAssetsMock.mockImplementation((wrapper: string) => {
      if (wrapper === "nisa_tsumitate") {
        return {
          isLoading: false,
          isFetching: false,
          data: {
            count: 1,
            items: [
              { ticker: "AAA", fund_name: "Alpha Fund", asset_type: "mutual_fund", trust_fee_pct: 0.1 },
            ],
          },
        }
      }
      return { isLoading: false, isFetching: false, data: { count: 0, items: [] } }
    })

    renderTab()

    fireEvent.change(screen.getByLabelText("nisa.eligible.filter_asset_type"), {
      target: { value: "etf" },
    })
    expect(screen.getByText("nisa.eligible.filter_no_match_title")).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: "nisa.eligible.clear_filter" }))
    expect(screen.getByText("Alpha Fund")).toBeInTheDocument()
  })

  it("shows search no-match state and clears search query", () => {
    useEligibleAssetsMock.mockImplementation((_wrapper: string, options?: { search?: string }) => ({
      isLoading: false,
      isFetching: false,
      data: options?.search
        ? { count: 0, items: [] }
        : {
            count: 1,
            items: [{ ticker: "AAA", fund_name: "Alpha Fund", asset_type: "mutual_fund", trust_fee_pct: 0.1 }],
          },
    }))

    renderTab()

    fireEvent.change(screen.getByPlaceholderText("nisa.eligible.search_placeholder"), {
      target: { value: "zzz" },
    })

    expect(screen.getByText("nisa.eligible.filter_no_match_title")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "nisa.eligible.clear_search" }))
    expect(screen.getByText("Alpha Fund")).toBeInTheDocument()
  })
})
