import { describe, expect, it, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { AddStockDrawer } from "../AddStockDrawer"

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

vi.mock("@/api/hooks/useRadar", () => ({
  useAddStock: () => ({ mutate: vi.fn(), isPending: false }),
  useTriggerScan: () => ({ mutate: vi.fn(), isPending: false }),
  useImportStocks: () => ({ mutate: vi.fn(), isPending: false }),
}))

vi.mock("@/api/hooks/useCrypto", () => ({
  useCryptoSearch: () => ({ data: [] }),
}))

describe("AddStockDrawer category rendering", () => {
  it("renders category description below select", () => {
    render(<AddStockDrawer open={true} onClose={() => undefined} isScanning={false} />)
    expect(screen.getByText("config.category_desc.growth")).toBeInTheDocument()
  })

  it("shows i18n category label without prefix icon in the trigger", () => {
    render(<AddStockDrawer open={true} onClose={() => undefined} isScanning={false} />)
    const trigger = screen.getByRole("combobox", { name: "radar.form.category" })
    expect(trigger.textContent).toContain("config.category.growth")
    expect(trigger.textContent).not.toMatch(/🚀.*config\.category/)
  })
})
