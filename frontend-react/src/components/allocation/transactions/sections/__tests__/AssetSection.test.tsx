import { render, screen, fireEvent } from "@testing-library/react"
import { describe, it, expect, vi, beforeEach } from "vitest"
import { AssetSection } from "../AssetSection"
import type { UseQueryResult } from "@tanstack/react-query"

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}))

// Stub pickers that require complex contexts
vi.mock("../../NisaAssetPicker", () => ({
  NisaAssetPicker: () => <div data-testid="nisa-picker" />,
}))

vi.mock("../../SellablePositionPicker", () => ({
  SellablePositionPicker: () => <div data-testid="sell-picker" />,
}))

const noop = vi.fn()

function makeQuery<T>(data?: T): UseQueryResult<T> {
  return {
    data,
    isLoading: false,
    isFetched: data !== undefined,
  } as unknown as UseQueryResult<T>
}

const defaultProps = {
  transactionType: "BUY" as const,
  isCashMovement: false,
  currency: "USD",
  ticker: "",
  thesis: "",
  category: "Growth" as const,
  forcedCategory: null,
  isNewToRadar: false,
  shouldShowNisaPicker: false,
  shouldShowSellPicker: false,
  nisaFreeTickerInput: false,
  selectedWrapper: "tokutei",
  nisaAssetTypeFilter: "all" as const,
  nisaPickerOpen: false,
  nisaPickerSearch: "",
  nisaEligibleAssetsQuery: makeQuery({ items: [] }),
  selectedNisaAssetForDisplay: null,
  isMobile: false,
  commandListScrollFix: {},
  sellPickerOpen: false,
  sellPickerSearch: "",
  filteredSellablePositions: [],
  selectedSellablePositionForDisplay: null,
  sellablePositionsQuery: makeQuery(),
  eligibility: null,
  eligibilityQueryIsLoading: false,
  suggestedAccount: null,
  routingSuggestionQuery: makeQuery({ suggestions: [] }),
  routingSuggestedAccounts: new Map(),
  canSplitPurchase: false,
  splitSubmitting: false,
  addTransactionMutationIsPending: false,
  fieldErrors: {},
  setTransactionType: noop,
  setTicker: noop,
  setThesis: noop,
  setCategory: noop,
  setNisaAssetTypeFilter: noop,
  setNisaPickerOpen: noop,
  setNisaPickerSearch: noop,
  setSellPickerOpen: noop,
  setSellPickerSearch: noop,
  setAccountId: noop,
  setCurrency: noop,
  setInsufficientBalance: noop,
  setFieldErrors: noop,
  applyCashMovementDefaults: noop,
  onSelectNisaAsset: noop,
  onSelectSellablePosition: noop,
  getSellValueSourceLabel: () => null,
  createSplitTransactions: async () => {},
}

describe("AssetSection", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe("TransactionTypePicker", () => {
    it("renders all 5 transaction type buttons", () => {
      render(<AssetSection {...defaultProps} />)
      expect(screen.getByText("transactions.type.buy")).toBeInTheDocument()
      expect(screen.getByText("transactions.type.sell")).toBeInTheDocument()
      expect(screen.getByText("transactions.type.dividend")).toBeInTheDocument()
      expect(screen.getByText("transactions.type.deposit")).toBeInTheDocument()
      expect(screen.getByText("transactions.type.withdrawal")).toBeInTheDocument()
    })

    it("calls setTransactionType when a type button is clicked", () => {
      const setTransactionType = vi.fn()
      render(<AssetSection {...defaultProps} setTransactionType={setTransactionType} />)
      fireEvent.click(screen.getByText("transactions.type.sell"))
      expect(setTransactionType).toHaveBeenCalledWith("SELL")
    })

    it("calls applyCashMovementDefaults when DEPOSIT is selected", () => {
      const applyCashMovementDefaults = vi.fn()
      render(
        <AssetSection
          {...defaultProps}
          currency="JPY"
          applyCashMovementDefaults={applyCashMovementDefaults}
        />,
      )
      fireEvent.click(screen.getByText("transactions.type.deposit"))
      expect(applyCashMovementDefaults).toHaveBeenCalledWith("JPY")
    })

    it("calls applyCashMovementDefaults when WITHDRAWAL is selected", () => {
      const applyCashMovementDefaults = vi.fn()
      render(
        <AssetSection {...defaultProps} applyCashMovementDefaults={applyCashMovementDefaults} />,
      )
      fireEvent.click(screen.getByText("transactions.type.withdrawal"))
      expect(applyCashMovementDefaults).toHaveBeenCalledWith("USD")
    })

    it("resets field errors when type is changed", () => {
      const setFieldErrors = vi.fn()
      render(<AssetSection {...defaultProps} setFieldErrors={setFieldErrors} />)
      fireEvent.click(screen.getByText("transactions.type.sell"))
      expect(setFieldErrors).toHaveBeenCalled()
    })

    it("resets sell picker when type is changed", () => {
      const setSellPickerOpen = vi.fn()
      const setSellPickerSearch = vi.fn()
      render(
        <AssetSection
          {...defaultProps}
          setSellPickerOpen={setSellPickerOpen}
          setSellPickerSearch={setSellPickerSearch}
        />,
      )
      fireEvent.click(screen.getByText("transactions.type.buy"))
      expect(setSellPickerOpen).toHaveBeenCalledWith(false)
      expect(setSellPickerSearch).toHaveBeenCalledWith("")
    })
  })

  describe("TickerInput visibility", () => {
    it("renders ticker input for BUY (non-cash) transaction", () => {
      render(<AssetSection {...defaultProps} transactionType="BUY" isCashMovement={false} />)
      expect(screen.getByRole("textbox", { name: "transactions.form.ticker" })).toBeInTheDocument()
    })

    it("hides ticker input for cash movements", () => {
      render(<AssetSection {...defaultProps} transactionType="DEPOSIT" isCashMovement={true} />)
      expect(
        screen.queryByRole("textbox", { name: "transactions.form.ticker" }),
      ).not.toBeInTheDocument()
    })

    it("shows NISA picker when shouldShowNisaPicker is true", () => {
      render(
        <AssetSection
          {...defaultProps}
          shouldShowNisaPicker={true}
          selectedWrapper="nisa_growth"
        />,
      )
      expect(screen.getByTestId("nisa-picker")).toBeInTheDocument()
    })

    it("shows sell picker when shouldShowSellPicker is true", () => {
      render(<AssetSection {...defaultProps} transactionType="SELL" shouldShowSellPicker={true} />)
      expect(screen.getByTestId("sell-picker")).toBeInTheDocument()
    })
  })

  describe("ticker input behavior", () => {
    it("updates ticker with normalized value", () => {
      const setTicker = vi.fn()
      render(<AssetSection {...defaultProps} setTicker={setTicker} />)
      const input = screen.getByRole("textbox", { name: "transactions.form.ticker" })
      fireEvent.change(input, { target: { value: "aapl" } })
      expect(setTicker).toHaveBeenCalledWith("AAPL")
    })

    it("shows ticker field error when present", () => {
      render(<AssetSection {...defaultProps} fieldErrors={{ ticker: "Ticker required" }} />)
      expect(screen.getByText("Ticker required")).toBeInTheDocument()
    })
  })

  describe("new-to-radar section", () => {
    it("shows thesis and category inputs when isNewToRadar is true", () => {
      render(<AssetSection {...defaultProps} isNewToRadar={true} />)
      expect(screen.getByRole("textbox", { name: "transactions.form.thesis" })).toBeInTheDocument()
    })

    it("hides thesis when isCashMovement is true", () => {
      render(<AssetSection {...defaultProps} isNewToRadar={true} isCashMovement={true} />)
      expect(
        screen.queryByRole("textbox", { name: "transactions.form.thesis" }),
      ).not.toBeInTheDocument()
    })

    it("updates thesis value", () => {
      const setThesis = vi.fn()
      render(<AssetSection {...defaultProps} isNewToRadar={true} setThesis={setThesis} />)
      const input = screen.getByRole("textbox", { name: "transactions.form.thesis" })
      fireEvent.change(input, { target: { value: "Long-term compounding" } })
      expect(setThesis).toHaveBeenCalledWith("Long-term compounding")
    })
  })
})
