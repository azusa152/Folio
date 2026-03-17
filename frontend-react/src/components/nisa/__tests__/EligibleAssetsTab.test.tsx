import { fireEvent, render, screen, waitFor } from "@testing-library/react"
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

    render(<EligibleAssetsTab />)

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
})
