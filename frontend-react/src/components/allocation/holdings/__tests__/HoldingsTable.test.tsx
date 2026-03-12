import type { ComponentProps } from "react"
import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { HoldingsTable } from "../HoldingsTable"

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}))

vi.mock("@/hooks/useTerminology", () => ({
  useTerminology: () => ({
    term: (_key: string, fallback: string) => fallback,
  }),
}))

describe("HoldingsTable", () => {
  it("renders translated category key for holdings rows", () => {
    render(
      <HoldingsTable
        holdings={[
          {
            ticker: "AAPL",
            category: "Growth",
            quantity: 2,
            market_value: 200,
            weight_pct: 10,
            cost_total: 180,
            change_pct: 5,
            currency: "USD",
          } as unknown as ComponentProps<typeof HoldingsTable>["holdings"][number],
        ]}
        privacyMode={false}
        displayCurrency="USD"
      />,
    )

    expect(screen.getByText("config.category.growth")).toBeInTheDocument()
  })
})
