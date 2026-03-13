import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { TransactionCsvImportDialog } from "../TransactionCsvImportDialog"

const mutateMock = vi.fn()
const { parseTransactionCSVMock } = vi.hoisted(() => ({
  parseTransactionCSVMock: vi.fn(),
}))

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: { count?: number }) =>
      typeof opts?.count === "number" ? `${key}:${opts.count}` : key,
  }),
}))

vi.mock("@/api/hooks/useTransactions", () => ({
  useImportTransactions: () => ({
    mutate: mutateMock,
    isPending: false,
  }),
}))

vi.mock("@/api/hooks/useAccounts", () => ({
  useAccounts: () => ({
    data: [{ id: 1, name: "IB US" }],
  }),
}))

vi.mock("@/lib/transaction-csv-import", async () => {
  const actual = await vi.importActual<typeof import("@/lib/transaction-csv-import")>(
    "@/lib/transaction-csv-import",
  )
  return {
    ...actual,
    parseTransactionCSV: parseTransactionCSVMock.mockResolvedValue({
      headers: ["date", "type", "ticker", "qty", "total", "currency"],
      rows: [
        {
          date: "2024-01-15",
          type: "BUY",
          ticker: "AAPL",
          qty: "10",
          total: "1500",
          currency: "USD",
        },
      ],
      warnings: [],
    }),
  }
})

function renderDialog() {
  const client = new QueryClient()
  return render(
    <QueryClientProvider client={client}>
      <TransactionCsvImportDialog open onClose={vi.fn()} />
    </QueryClientProvider>,
  )
}

function uploadFile() {
  const input = document.querySelector("input[type='file']") as HTMLInputElement
  const file = new File(
    ["date,type,ticker,qty,total,currency\n2024-01-15,BUY,AAPL,10,1500,USD"],
    "transactions.csv",
    { type: "text/csv" },
  )
  fireEvent.change(input, { target: { files: [file] } })
}

describe("TransactionCsvImportDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    parseTransactionCSVMock.mockResolvedValue({
      headers: ["date", "type", "ticker", "qty", "total", "currency"],
      rows: [
        {
          date: "2024-01-15",
          type: "BUY",
          ticker: "AAPL",
          qty: "10",
          total: "1500",
          currency: "USD",
        },
      ],
      warnings: [],
    })
  })

  it("renders select step by default", () => {
    renderDialog()
    expect(screen.getByText("transactions.import.title")).toBeInTheDocument()
    expect(screen.getByText("transactions.import.step_select")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "transactions.import.download_template" })).toBeInTheDocument()
    expect(screen.getByText("transactions.import.download_template_hint")).toBeInTheDocument()
  })

  it("downloads template with expected filename when clicked", () => {
    const originalCreateObjectURL = (URL as { createObjectURL?: (obj: Blob) => string }).createObjectURL
    const originalRevokeObjectURL = (URL as { revokeObjectURL?: (url: string) => void })
      .revokeObjectURL
    const createObjectURLMock = vi.fn(() => "blob:template-url")
    const revokeObjectURLMock = vi.fn()
    Object.defineProperty(URL, "createObjectURL", {
      writable: true,
      configurable: true,
      value: createObjectURLMock,
    })
    Object.defineProperty(URL, "revokeObjectURL", {
      writable: true,
      configurable: true,
      value: revokeObjectURLMock,
    })
    const originalCreateElement = document.createElement.bind(document)
    const anchorClick = vi.fn()
    const capturedAnchorRef: { current: HTMLAnchorElement | null } = { current: null }

    const createElementSpy = vi.spyOn(document, "createElement").mockImplementation((tagName: string) => {
      const element = originalCreateElement(tagName) as HTMLElement
      if (tagName.toLowerCase() === "a") {
        capturedAnchorRef.current = element as HTMLAnchorElement
        capturedAnchorRef.current.click = anchorClick
      }
      return element
    })

    renderDialog()
    fireEvent.click(screen.getByRole("button", { name: "transactions.import.download_template" }))

    expect(createObjectURLMock).toHaveBeenCalledTimes(1)
    if (!capturedAnchorRef.current) {
      throw new Error("Expected anchor element to be created")
    }
    const anchor = capturedAnchorRef.current
    expect(anchor.download).toBe("folio-transaction-template.csv")
    expect(anchor.href).toContain("blob:template-url")
    expect(anchorClick).toHaveBeenCalledTimes(1)
    expect(revokeObjectURLMock).toHaveBeenCalledWith("blob:template-url")

    createElementSpy.mockRestore()
    Object.defineProperty(URL, "createObjectURL", {
      writable: true,
      configurable: true,
      value: originalCreateObjectURL,
    })
    Object.defineProperty(URL, "revokeObjectURL", {
      writable: true,
      configurable: true,
      value: originalRevokeObjectURL,
    })
  })

  it("progresses through select → map → preview", async () => {
    renderDialog()
    uploadFile()

    await waitFor(() =>
      expect(screen.getByText("transactions.import.step_map")).toBeInTheDocument(),
    )

    fireEvent.click(screen.getByRole("button", { name: "transactions.import.next" }))
    await waitFor(() =>
      expect(screen.getByText("transactions.import.step_preview")).toBeInTheDocument(),
    )
  })

  it("blocks navigation to preview when date mapping is missing", async () => {
    parseTransactionCSVMock.mockResolvedValue({
      headers: ["foo", "bar"],
      rows: [{ foo: "x", bar: "y" }],
      warnings: [],
    })

    renderDialog()
    uploadFile()

    await waitFor(() =>
      expect(screen.getByText("transactions.import.step_map")).toBeInTheDocument(),
    )

    fireEvent.click(screen.getByRole("button", { name: "transactions.import.next" }))
    await waitFor(() =>
      expect(
        screen.getByText("transactions.import.missing_required_mapping_date"),
      ).toBeInTheDocument(),
    )
  })

  it("allows preview when total is skipped but price and quantity are mapped", async () => {
    parseTransactionCSVMock.mockResolvedValue({
      headers: ["date", "type", "ticker", "qty", "price", "currency"],
      rows: [
        {
          date: "2024-01-15",
          type: "BUY",
          ticker: "AAPL",
          qty: "10",
          price: "150",
          currency: "USD",
        },
      ],
      warnings: [],
    })

    renderDialog()
    uploadFile()

    await waitFor(() =>
      expect(screen.getByText("transactions.import.step_map")).toBeInTheDocument(),
    )
    expect(screen.getByText("transactions.import.total_amount_auto_hint")).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: "transactions.import.next" }))
    await waitFor(() =>
      expect(screen.getByText("transactions.import.step_preview")).toBeInTheDocument(),
    )
  })

  it("sends correct payload shape on import", async () => {
    renderDialog()
    uploadFile()

    await waitFor(() =>
      expect(screen.getByText("transactions.import.step_map")).toBeInTheDocument(),
    )

    fireEvent.click(screen.getByRole("button", { name: "transactions.import.next" }))
    await waitFor(() =>
      expect(screen.getByText("transactions.import.step_preview")).toBeInTheDocument(),
    )

    const importButton = screen.getByRole("button", {
      name: "transactions.import.confirm_import:1",
    })
    expect(importButton).not.toBeDisabled()
    fireEvent.click(importButton)

    expect(mutateMock).toHaveBeenCalledTimes(1)
    const [payload] = mutateMock.mock.calls[0]
    expect(payload).toHaveProperty("items")
    expect(payload).toHaveProperty("account_id", null)
    expect(payload).toHaveProperty("mode", "append")
    expect(payload.items).toHaveLength(1)
    expect(payload.items[0]).toHaveProperty("ticker", "AAPL")
    expect(payload.items[0]).toHaveProperty("transaction_type", "BUY")
  })

  it("passes selected account_id in payload", async () => {
    renderDialog()
    uploadFile()

    await waitFor(() =>
      expect(screen.getByText("transactions.import.step_map")).toBeInTheDocument(),
    )

    const accountSelect = screen.getByLabelText("transactions.import.account")
    fireEvent.change(accountSelect, { target: { value: "1" } })

    fireEvent.click(screen.getByRole("button", { name: "transactions.import.next" }))
    await waitFor(() =>
      expect(screen.getByText("transactions.import.step_preview")).toBeInTheDocument(),
    )

    fireEvent.click(
      screen.getByRole("button", { name: "transactions.import.confirm_import:1" }),
    )

    expect(mutateMock).toHaveBeenCalledTimes(1)
    const [payload] = mutateMock.mock.calls[0]
    expect(payload.account_id).toBe(1)
    expect(payload.mode).toBe("append")
  })

  it("requires account selection before enabling replace mode", async () => {
    renderDialog()
    uploadFile()

    await waitFor(() =>
      expect(screen.getByText("transactions.import.step_map")).toBeInTheDocument(),
    )

    const replaceRadio = screen.getByRole("radio", {
      name: "transactions.import.mode_replace_account",
    })
    expect(replaceRadio).toBeDisabled()

    const accountSelect = screen.getByLabelText("transactions.import.account")
    fireEvent.change(accountSelect, { target: { value: "1" } })

    expect(replaceRadio).not.toBeDisabled()
  })

  it("requires destructive confirmation and includes replace mode in payload", async () => {
    renderDialog()
    uploadFile()

    await waitFor(() =>
      expect(screen.getByText("transactions.import.step_map")).toBeInTheDocument(),
    )

    const accountSelect = screen.getByLabelText("transactions.import.account")
    fireEvent.change(accountSelect, { target: { value: "1" } })

    fireEvent.click(
      screen.getByRole("radio", { name: "transactions.import.mode_replace_account" }),
    )

    fireEvent.click(screen.getByRole("button", { name: "transactions.import.next" }))
    await waitFor(() =>
      expect(screen.getByText("transactions.import.step_preview")).toBeInTheDocument(),
    )

    fireEvent.click(
      screen.getByRole("button", { name: "transactions.import.confirm_import:1" }),
    )
    expect(mutateMock).not.toHaveBeenCalled()
    expect(
      screen.getByText("transactions.import.confirm_destructive_required"),
    ).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: "transactions.import.back" }))
    await waitFor(() =>
      expect(screen.getByText("transactions.import.step_map")).toBeInTheDocument(),
    )
    fireEvent.click(screen.getByRole("checkbox"))
    fireEvent.click(screen.getByRole("button", { name: "transactions.import.next" }))
    await waitFor(() =>
      expect(screen.getByText("transactions.import.step_preview")).toBeInTheDocument(),
    )

    fireEvent.click(
      screen.getByRole("button", { name: "transactions.import.confirm_import:1" }),
    )

    expect(mutateMock).toHaveBeenCalledTimes(1)
    const [payload] = mutateMock.mock.calls[0]
    expect(payload.account_id).toBe(1)
    expect(payload.mode).toBe("replace_account")
  })

  it("disables import when all rows have errors", async () => {
    parseTransactionCSVMock.mockResolvedValue({
      headers: ["date", "type", "ticker", "qty", "total", "currency"],
      rows: [
        { date: "", type: "INVALID", ticker: "", qty: "0", total: "0", currency: "XX" },
      ],
      warnings: [],
    })

    renderDialog()
    uploadFile()

    await waitFor(() =>
      expect(screen.getByText("transactions.import.step_map")).toBeInTheDocument(),
    )

    fireEvent.click(screen.getByRole("button", { name: "transactions.import.next" }))
    await waitFor(() =>
      expect(screen.getByText("transactions.import.step_preview")).toBeInTheDocument(),
    )

    const importButton = screen.getByRole("button", {
      name: "transactions.import.confirm_import:1",
    })
    expect(importButton).toBeDisabled()
    expect(mutateMock).not.toHaveBeenCalled()
  })

  it("allows navigating back from preview to map", async () => {
    renderDialog()
    uploadFile()

    await waitFor(() =>
      expect(screen.getByText("transactions.import.step_map")).toBeInTheDocument(),
    )

    fireEvent.click(screen.getByRole("button", { name: "transactions.import.next" }))
    await waitFor(() =>
      expect(screen.getByText("transactions.import.step_preview")).toBeInTheDocument(),
    )

    fireEvent.click(screen.getByRole("button", { name: "transactions.import.back" }))
    await waitFor(() =>
      expect(screen.getByText("transactions.import.step_map")).toBeInTheDocument(),
    )
  })
})
