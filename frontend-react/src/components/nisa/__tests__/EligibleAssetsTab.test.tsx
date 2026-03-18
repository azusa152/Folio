import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import { describe, expect, it, vi } from "vitest"
import { EligibleAssetsTab } from "../EligibleAssetsTab"

const { useEligibleAssetsMock, useEligibleAssetsMetadataMock } = vi.hoisted(() => ({
  useEligibleAssetsMock: vi.fn(),
  useEligibleAssetsMetadataMock: vi.fn(),
}))

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, number>) =>
      params ? `${key}:${params.count ?? ""}:${params.total ?? ""}` : key,
  }),
}))

vi.mock("@/api/hooks/useWrappers", () => ({
  useEligibleAssets: (...args: unknown[]) => useEligibleAssetsMock(...args),
  useEligibleAssetsMetadata: (...args: unknown[]) =>
    useEligibleAssetsMetadataMock(...args),
}))

function renderTab() {
  return render(
    <MemoryRouter>
      <EligibleAssetsTab />
    </MemoryRouter>,
  )
}

describe("EligibleAssetsTab", () => {
  it("shows both wrapper counts on initial render using metadata fallback", () => {
    useEligibleAssetsMock.mockImplementation((wrapper: string) => {
      if (wrapper === "nisa_tsumitate") {
        return {
          isLoading: false,
          isFetching: false,
          data: {
            count: 2,
            total_count: 325,
            items: [
              {
                ticker: "AAA",
                fund_name: "Alpha Fund",
                asset_type: "mutual_fund",
                trust_fee_pct: 0.1,
              },
            ],
          },
        }
      }
      return {
        isLoading: false,
        isFetching: false,
        data: undefined,
      }
    })
    useEligibleAssetsMetadataMock.mockImplementation((wrapper: string) => {
      if (wrapper === "nisa_tsumitate") {
        return { data: { wrapper: "nisa_tsumitate", count: 325 } }
      }
      return { data: { wrapper: "nisa_growth", count: 2702 } }
    })

    renderTab()

    expect(screen.getByText("325")).toBeInTheDocument()
    expect(screen.getByText("2702")).toBeInTheDocument()
  })

  it("applies asset-type filter and supports load-more pagination", async () => {
    useEligibleAssetsMetadataMock.mockImplementation((wrapper: string) => {
      if (wrapper === "nisa_tsumitate") {
        return { data: { wrapper: "nisa_tsumitate", count: 325 } }
      }
      return { data: { wrapper: "nisa_growth", count: 0 } }
    })
    useEligibleAssetsMock.mockImplementation(
      (wrapper: string, options: { limit?: number; assetType?: string }) => {
        const allItems = [
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
        ]
        const items = options?.assetType
          ? allItems.filter((item) => item.asset_type === options.assetType)
          : allItems
      if (wrapper === "nisa_tsumitate") {
        return {
          isLoading: false,
          isFetching: false,
          data: {
            count: items.length,
            total_count: options?.assetType ? items.length : 200,
            items,
          },
          options,
        }
      }
      return {
        isLoading: false,
        isFetching: false,
        data: { count: 0, total_count: 0, items: [] },
        options,
      }
      },
    )

    renderTab()

    expect(screen.getByText("325")).toBeInTheDocument()
    expect(screen.getByText("nisa.eligible.showing_count:2:200")).toBeInTheDocument()
    expect(screen.getByText("Alpha Fund")).toBeInTheDocument()
    expect(screen.getByText("Beta ETF")).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: "nisa.eligible.load_more" }))
    await waitFor(() => {
      expect(useEligibleAssetsMock).toHaveBeenCalledWith(
        "nisa_tsumitate",
        expect.objectContaining({ limit: 100 }),
      )
    })

    fireEvent.change(screen.getByLabelText("nisa.eligible.filter_asset_type"), {
      target: { value: "etf" },
    })
    expect(screen.queryByText("Alpha Fund")).not.toBeInTheDocument()
    expect(screen.getByText("Beta ETF")).toBeInTheDocument()
    expect(useEligibleAssetsMock).toHaveBeenCalledWith(
      "nisa_tsumitate",
      expect.objectContaining({ assetType: "etf" }),
    )
  })

  it("passes selected asset type to eligible-assets query", async () => {
    useEligibleAssetsMetadataMock.mockReturnValue({ data: { wrapper: "nisa_tsumitate", count: 1 } })
    useEligibleAssetsMock.mockImplementation((_wrapper: string, options?: { assetType?: string }) => ({
      isLoading: false,
      isFetching: false,
      data: {
        count: options?.assetType === "etf" ? 1 : 0,
        total_count: options?.assetType === "etf" ? 1 : 0,
        items:
          options?.assetType === "etf"
            ? [{ ticker: "BBB", fund_name: "Beta ETF", asset_type: "etf", trust_fee_pct: 0.2 }]
            : [],
      },
    }))

    renderTab()
    fireEvent.change(screen.getByLabelText("nisa.eligible.filter_asset_type"), {
      target: { value: "etf" },
    })

    await waitFor(() => {
      expect(useEligibleAssetsMock).toHaveBeenCalledWith(
        "nisa_tsumitate",
        expect.objectContaining({ assetType: "etf" }),
      )
    })
  })

  it("shows filter-mismatch empty state when data exists but filter excludes all", () => {
    useEligibleAssetsMetadataMock.mockReturnValue({ data: { wrapper: "nisa_tsumitate", count: 1 } })
    useEligibleAssetsMock.mockImplementation((wrapper: string, options?: { assetType?: string }) => {
      if (wrapper === "nisa_tsumitate") {
        const items =
          options?.assetType === "etf"
            ? []
            : [{ ticker: "AAA", fund_name: "Alpha Fund", asset_type: "mutual_fund", trust_fee_pct: 0.1 }]
        return {
          isLoading: false,
          isFetching: false,
          data: {
            count: items.length,
            total_count: items.length,
            items,
          },
        }
      }
      return { isLoading: false, isFetching: false, data: { count: 0, total_count: 0, items: [] } }
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
    useEligibleAssetsMetadataMock.mockReturnValue({ data: { wrapper: "nisa_tsumitate", count: 0 } })
    useEligibleAssetsMock.mockReturnValue({
      isLoading: false,
      isFetching: false,
      data: { count: 0, total_count: 0, items: [] },
    })

    renderTab()

    expect(screen.getByText("nisa.eligible.empty_title")).toBeInTheDocument()
    expect(screen.getByText("nisa.eligible.empty")).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "nisa.eligible.empty_cta" })).toHaveAttribute("href", "/nisa?tab=data")
  })

  it("clears filter when clear-filter button is clicked", () => {
    useEligibleAssetsMetadataMock.mockReturnValue({ data: { wrapper: "nisa_tsumitate", count: 1 } })
    useEligibleAssetsMock.mockImplementation((wrapper: string, options?: { assetType?: string }) => {
      if (wrapper === "nisa_tsumitate") {
        const items =
          options?.assetType === "etf"
            ? []
            : [{ ticker: "AAA", fund_name: "Alpha Fund", asset_type: "mutual_fund", trust_fee_pct: 0.1 }]
        return {
          isLoading: false,
          isFetching: false,
          data: {
            count: items.length,
            total_count: items.length,
            items,
          },
        }
      }
      return { isLoading: false, isFetching: false, data: { count: 0, total_count: 0, items: [] } }
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
    useEligibleAssetsMetadataMock.mockReturnValue({ data: { wrapper: "nisa_tsumitate", count: 1 } })
    useEligibleAssetsMock.mockImplementation((_wrapper: string, options?: { search?: string }) => ({
      isLoading: false,
      isFetching: false,
      data: options?.search
        ? { count: 0, total_count: 0, items: [] }
        : {
            count: 1,
            total_count: 1,
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
