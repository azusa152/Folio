import { describe, expect, it } from "vitest"
import {
  autoDetectTransactionColumns,
  isCashMovementRow,
  parseTransactionCsvText,
  transformTransactionRow,
  transformTransactionRows,
  validateTransactionRow,
  validateTransactionRows,
  type TransactionColumnMapping,
} from "@/lib/transaction-csv-import"

describe("transaction-csv-import", () => {
  describe("autoDetectTransactionColumns", () => {
    it("detects common column aliases", () => {
      const mapping = autoDetectTransactionColumns([
        "Trade Date",
        "Action",
        "Symbol",
        "Shares",
        "Unit Price",
        "Total Amount",
        "Currency",
        "Commission",
        "Memo",
      ])

      expect(mapping.dateColumn).toBe("Trade Date")
      expect(mapping.typeColumn).toBe("Action")
      expect(mapping.tickerColumn).toBe("Symbol")
      expect(mapping.quantityColumn).toBe("Shares")
      expect(mapping.priceColumn).toBe("Unit Price")
      expect(mapping.totalAmountColumn).toBe("Total Amount")
      expect(mapping.currencyColumn).toBe("Currency")
      expect(mapping.feeColumn).toBe("Commission")
      expect(mapping.noteColumn).toBe("Memo")
    })

    it("detects snake_case headers", () => {
      const mapping = autoDetectTransactionColumns([
        "transaction_date",
        "transaction_type",
        "ticker",
        "quantity",
        "price",
        "total_amount",
        "currency",
        "fee",
        "note",
      ])

      expect(mapping.dateColumn).toBe("transaction_date")
      expect(mapping.typeColumn).toBe("transaction_type")
      expect(mapping.tickerColumn).toBe("ticker")
    })

    it("returns undefined for unrecognized headers", () => {
      const mapping = autoDetectTransactionColumns(["foo", "bar"])
      expect(mapping.dateColumn).toBeUndefined()
      expect(mapping.typeColumn).toBeUndefined()
      expect(mapping.tickerColumn).toBeUndefined()
    })

    it("provides sensible defaults", () => {
      const mapping = autoDetectTransactionColumns([])
      expect(mapping.transactionTypeDefault).toBe("BUY")
      expect(mapping.currencyDefault).toBe("USD")
    })
  })

  describe("transformTransactionRow", () => {
    const baseMapping: TransactionColumnMapping = {
      dateColumn: "date",
      typeColumn: "type",
      tickerColumn: "ticker",
      quantityColumn: "qty",
      priceColumn: "price",
      totalAmountColumn: "total",
      currencyColumn: "ccy",
      feeColumn: "fee",
      noteColumn: "note",
      fxRateColumn: "fx",
      transactionTypeDefault: "BUY",
      currencyDefault: "USD",
    }

    it("transforms a standard BUY row", () => {
      const item = transformTransactionRow(
        {
          date: "2024-03-15",
          type: "BUY",
          ticker: "AAPL",
          qty: "10",
          price: "175.50",
          total: "1755",
          ccy: "usd",
          fee: "5.99",
          note: "quarterly buy",
          fx: "1.0",
        },
        baseMapping,
      )

      expect(item).toMatchObject({
        transaction_date: "2024-03-15",
        transaction_type: "BUY",
        ticker: "AAPL",
        quantity: 10,
        price: 175.5,
        total_amount: 1755,
        currency: "USD",
        fee: 5.99,
        note: "quarterly buy",
        fx_rate: 1.0,
      })
    })

    it("normalizes type aliases", () => {
      expect(
        transformTransactionRow({ ...row("purchase"), type: "purchase" }, baseMapping)
          .transaction_type,
      ).toBe("BUY")
      expect(
        transformTransactionRow({ ...row("cashin"), type: "cashin" }, baseMapping)
          .transaction_type,
      ).toBe("DEPOSIT")
      expect(
        transformTransactionRow({ ...row("cashout"), type: "cashout" }, baseMapping)
          .transaction_type,
      ).toBe("WITHDRAWAL")
    })

    it("uses transactionTypeDefault for unknown type", () => {
      const item = transformTransactionRow(
        { ...row("unknown"), type: "unknown_value" },
        { ...baseMapping, transactionTypeDefault: "SELL" },
      )
      expect(item.transaction_type).toBe("SELL")
    })

    it("falls back to currency as ticker for DEPOSIT", () => {
      const item = transformTransactionRow(
        { date: "2024-01-01", type: "deposit", qty: "", total: "5000", ccy: "JPY" },
        { ...baseMapping, tickerColumn: undefined },
      )
      expect(item.ticker).toBe("JPY")
      expect(item.quantity).toBe(1)
    })

    it("falls back to currency as ticker for WITHDRAWAL", () => {
      const item = transformTransactionRow(
        { date: "2024-01-01", type: "withdrawal", qty: "", total: "1000", ccy: "usd" },
        { ...baseMapping, tickerColumn: undefined },
      )
      expect(item.ticker).toBe("USD")
    })

    it("leaves ticker empty for non-cash row when ticker column is not mapped", () => {
      const item = transformTransactionRow(
        { date: "2024-01-01", type: "BUY", qty: "5", total: "500", ccy: "usd" },
        { ...baseMapping, tickerColumn: undefined },
      )
      expect(item.ticker).toBe("")
    })

    it("computes total_amount from quantity * price when total column is missing", () => {
      const item = transformTransactionRow(
        { date: "2024-01-01", type: "BUY", ticker: "MSFT", qty: "10", price: "400", ccy: "USD" },
        { ...baseMapping, totalAmountColumn: undefined },
      )
      expect(item.total_amount).toBe(4000)
    })

    it("normalizes ISO date format", () => {
      expect(
        transformTransactionRow(
          { ...row("date"), date: "2024-06-15" },
          baseMapping,
        ).transaction_date,
      ).toBe("2024-06-15")
    })

    it("normalizes slash-separated date format", () => {
      expect(
        transformTransactionRow(
        { ...row("date"), date: "2024/06/15" },
        baseMapping,
      ).transaction_date,
      ).toBe("2024-06-15")
    })

    it("returns empty string for invalid date", () => {
      const item = transformTransactionRow(
        { ...row("invalid-date"), date: "not-a-date" },
        baseMapping,
      )
      expect(item.transaction_date).toBe("")
    })

    it("handles comma-separated numbers", () => {
      const item = transformTransactionRow(
        {
          date: "2024-01-01",
          type: "BUY",
          ticker: "TSLA",
          qty: "1,000",
          price: "250.50",
          total: "250,500.00",
          ccy: "USD",
          fee: "9.99",
        },
        baseMapping,
      )
      expect(item.quantity).toBe(1000)
      expect(item.total_amount).toBe(250500)
    })
  })

  describe("transformTransactionRows", () => {
    it("maps all rows", () => {
      const mapping: TransactionColumnMapping = {
        dateColumn: "date",
        typeColumn: "type",
        tickerColumn: "ticker",
        totalAmountColumn: "total",
        transactionTypeDefault: "BUY",
        currencyDefault: "USD",
      }
      const items = transformTransactionRows(
        [
          { date: "2024-01-01", type: "BUY", ticker: "AAPL", total: "100" },
          { date: "2024-01-02", type: "SELL", ticker: "MSFT", total: "200" },
        ],
        mapping,
      )
      expect(items).toHaveLength(2)
      expect(items[0]?.ticker).toBe("AAPL")
      expect(items[1]?.ticker).toBe("MSFT")
    })
  })

  describe("isCashMovementRow", () => {
    it("returns true for DEPOSIT", () => {
      expect(
        isCashMovementRow({
          ticker: "USD",
          transaction_type: "DEPOSIT",
          quantity: 1,
          price: null,
          total_amount: 5000,
          currency: "USD",
          fx_rate: null,
          fee: 0,
          note: "",
          transaction_date: "2024-01-01",
        }),
      ).toBe(true)
    })

    it("returns true for WITHDRAWAL", () => {
      expect(
        isCashMovementRow({
          ticker: "USD",
          transaction_type: "WITHDRAWAL",
          quantity: 1,
          price: null,
          total_amount: 1000,
          currency: "USD",
          fx_rate: null,
          fee: 0,
          note: "",
          transaction_date: "2024-01-01",
        }),
      ).toBe(true)
    })

    it("returns false for BUY/SELL/DIVIDEND", () => {
      for (const type of ["BUY", "SELL", "DIVIDEND"]) {
        expect(
          isCashMovementRow({
            ticker: "AAPL",
            transaction_type: type,
            quantity: 10,
            price: 150,
            total_amount: 1500,
            currency: "USD",
            fx_rate: null,
            fee: 0,
            note: "",
            transaction_date: "2024-01-01",
          }),
        ).toBe(false)
      }
    })
  })

  describe("validateTransactionRow", () => {
    const validBuy = {
      ticker: "AAPL",
      transaction_type: "BUY",
      quantity: 10,
      price: 150,
      total_amount: 1500,
      currency: "USD",
      fx_rate: null,
      fee: 5,
      note: "",
      transaction_date: "2024-01-01",
    }

    it("returns no errors for a valid row", () => {
      expect(validateTransactionRow(validBuy)).toHaveLength(0)
    })

    it("requires transaction_date", () => {
      const errors = validateTransactionRow({ ...validBuy, transaction_date: "" })
      expect(errors.some((e) => e.code === "missing_date")).toBe(true)
    })

    it("requires ticker", () => {
      const errors = validateTransactionRow({ ...validBuy, ticker: "" })
      expect(errors.some((e) => e.code === "missing_ticker")).toBe(true)
    })

    it("requires positive quantity", () => {
      const errors = validateTransactionRow({ ...validBuy, quantity: 0 })
      expect(errors.some((e) => e.code === "invalid_quantity")).toBe(true)
    })

    it("requires positive total_amount", () => {
      const errors = validateTransactionRow({ ...validBuy, total_amount: -10 })
      expect(errors.some((e) => e.code === "invalid_total")).toBe(true)
    })

    it("requires 3-letter currency code", () => {
      const errors = validateTransactionRow({ ...validBuy, currency: "US" })
      expect(errors.some((e) => e.code === "invalid_currency")).toBe(true)
    })

    it("rejects invalid transaction type", () => {
      const errors = validateTransactionRow({ ...validBuy, transaction_type: "INVALID" })
      expect(errors.some((e) => e.code === "invalid_type")).toBe(true)
    })

    it("catches missing ticker on non-cash row with descriptive message", () => {
      const errors = validateTransactionRow({
        ...validBuy,
        ticker: "",
        transaction_type: "BUY",
      })
      const tickerErr = errors.find((e) => e.code === "missing_ticker")
      expect(tickerErr).toBeDefined()
      expect(tickerErr?.message).toBe("transactions.import.error_missing_ticker_non_cash")
    })

    it("catches missing ticker on cash row with descriptive message", () => {
      const errors = validateTransactionRow({
        ...validBuy,
        ticker: "",
        transaction_type: "DEPOSIT",
      })
      const tickerErr = errors.find((e) => e.code === "missing_ticker")
      expect(tickerErr).toBeDefined()
      expect(tickerErr?.message).toBe("transactions.import.error_missing_ticker_cash")
    })
  })

  describe("validateTransactionRows", () => {
    it("returns map keyed by row index", () => {
      const items = [
        {
          ticker: "AAPL",
          transaction_type: "BUY",
          quantity: 10,
          price: 150,
          total_amount: 1500,
          currency: "USD",
          fx_rate: null,
          fee: 0,
          note: "",
          transaction_date: "2024-01-01",
        },
        {
          ticker: "",
          transaction_type: "BUY",
          quantity: 0,
          price: null,
          total_amount: 0,
          currency: "XX",
          fx_rate: null,
          fee: 0,
          note: "",
          transaction_date: "",
        },
      ]
      const errors = validateTransactionRows(items)
      expect(errors.has(0)).toBe(false)
      expect(errors.has(1)).toBe(true)
      const rowErrors = errors.get(1) ?? []
      expect(rowErrors.length).toBeGreaterThan(0)
    })
  })

  describe("parseTransactionCsvText", () => {
    it("parses a standard CSV", async () => {
      const csv = "date,type,ticker,total\n2024-01-01,BUY,AAPL,1500\n"
      const result = await parseTransactionCsvText(csv)
      expect(result.headers).toEqual(["date", "type", "ticker", "total"])
      expect(result.rows).toHaveLength(1)
      expect(result.rows[0]?.ticker).toBe("AAPL")
    })

    it("strips BOM prefix", async () => {
      const csv = "\uFEFFdate,type,ticker,total\n2024-01-01,BUY,MSFT,200\n"
      const result = await parseTransactionCsvText(csv)
      expect(result.headers[0]).toBe("date")
    })

    it("skips empty lines", async () => {
      const csv = "date,type,ticker,total\n2024-01-01,BUY,AAPL,100\n\n\n"
      const result = await parseTransactionCsvText(csv)
      expect(result.rows).toHaveLength(1)
    })

    it("returns empty for empty input", async () => {
      const result = await parseTransactionCsvText("")
      expect(result.headers).toEqual([])
      expect(result.rows).toHaveLength(0)
    })
  })
})

function row(label: string): Record<string, string> {
  return {
    date: "2024-01-01",
    type: "BUY",
    ticker: "TEST",
    qty: "1",
    total: "100",
    ccy: "USD",
    fee: "0",
    note: label,
  }
}
