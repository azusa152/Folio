import Papa from "papaparse"
import type { components } from "@/api/types/generated"

export type TransactionImportItem = components["schemas"]["TransactionImportItem"]
export type CsvRow = Record<string, string>

type TransactionType = "BUY" | "SELL" | "DIVIDEND" | "DEPOSIT" | "WITHDRAWAL"

export interface TransactionColumnMapping {
  dateColumn?: string
  typeColumn?: string
  tickerColumn?: string
  quantityColumn?: string
  priceColumn?: string
  totalAmountColumn?: string
  currencyColumn?: string
  fxRateColumn?: string
  feeColumn?: string
  noteColumn?: string
  transactionTypeDefault?: TransactionType
  currencyDefault?: string
}

export interface CsvParseWarning {
  row: number
  code: string
  message: string
}

export interface ValidationError {
  code: string
  message: string
}

const SUPPORTED_TYPES = new Set<TransactionType>([
  "BUY",
  "SELL",
  "DIVIDEND",
  "DEPOSIT",
  "WITHDRAWAL",
])

const CASH_MOVEMENT_TYPES = new Set<TransactionType>(["DEPOSIT", "WITHDRAWAL"])

const TYPE_ALIASES: Record<string, TransactionType> = {
  buy: "BUY",
  purchase: "BUY",
  sell: "SELL",
  dividend: "DIVIDEND",
  deposit: "DEPOSIT",
  cash: "DEPOSIT",
  cashin: "DEPOSIT",
  withdrawal: "WITHDRAWAL",
  withdraw: "WITHDRAWAL",
  cashout: "WITHDRAWAL",
}

const COLUMN_ALIASES: Record<string, string[]> = {
  transaction_date: [
    "date",
    "transaction date",
    "trade date",
    "executed date",
    "executed at",
    "settled date",
  ],
  transaction_type: ["type", "action", "side", "transaction type"],
  ticker: ["ticker", "symbol", "stock"],
  quantity: ["quantity", "shares", "qty", "number of shares", "amount of shares", "units"],
  price: ["price", "unit price"],
  total_amount: [
    "total",
    "amount",
    "total amount",
    "total_amount",
    "total value",
    "market value",
    "cost",
    "proceeds",
  ],
  currency: ["currency", "ccy", "currency type", "currency code"],
  fx_rate: ["fx rate", "fx_rate", "exchange rate", "rate"],
  fee: ["fee", "commission"],
  note: ["note", "memo", "remarks"],
}

const TEMPLATE_HEADERS = [
  "transaction_date",
  "transaction_type",
  "ticker",
  "quantity",
  "price",
  "total_amount",
  "currency",
  "fx_rate",
  "fee",
  "note",
] as const

function normalizeHeader(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[_\s-]+/g, " ")
}

function pickColumn(headers: string[], aliases: string[]): string | undefined {
  const normalized = new Map(headers.map((h) => [normalizeHeader(h), h]))
  for (const alias of aliases) {
    const found = normalized.get(normalizeHeader(alias))
    if (found) return found
  }
  return undefined
}

function parseNumber(value: string | undefined): number | null {
  if (!value) return null
  const normalized = value.replace(/,/g, "").trim()
  if (!normalized) return null
  const parsed = Number(normalized)
  return Number.isFinite(parsed) ? parsed : null
}

function normalizeType(
  raw: string | undefined,
  fallback: TransactionType = "BUY",
): TransactionType {
  const value = (raw ?? "").trim().toLowerCase()
  if (!value) return fallback
  const mapped = TYPE_ALIASES[value]
  if (mapped) return mapped
  const upper = value.toUpperCase() as TransactionType
  return SUPPORTED_TYPES.has(upper) ? upper : fallback
}

function normalizeDate(raw: string | undefined): string {
  const value = (raw ?? "").trim()
  if (!value) return ""

  // Normalize YYYY-MM-DD or YYYY/MM/DD directly to avoid timezone drift.
  const isoLikeMatch = value.match(/^(\d{4})[-/](\d{2})[-/](\d{2})$/)
  if (isoLikeMatch) {
    const [, year, month, day] = isoLikeMatch
    return `${year}-${month}-${day}`
  }

  const dayMonthYearWithOptionalTime = value.match(
    /^(\d{1,2})[/-](\d{1,2})[/-](\d{4})(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?$/,
  )
  if (dayMonthYearWithOptionalTime) {
    const [, partA, partB, year] = dayMonthYearWithOptionalTime
    const a = Number(partA)
    const b = Number(partB)
    if (a >= 1 && a <= 31 && b >= 1 && b <= 31) {
      const assumeDayFirst = a > 12 || b <= 12
      const day = assumeDayFirst ? a : b
      const month = assumeDayFirst ? b : a
      if (month >= 1 && month <= 12 && day >= 1 && day <= 31) {
        return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`
      }
    }
  }

  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return ""
  return parsed.toISOString().slice(0, 10)
}

export function autoDetectTransactionColumns(headers: string[]): TransactionColumnMapping {
  return {
    dateColumn: pickColumn(headers, COLUMN_ALIASES.transaction_date),
    typeColumn: pickColumn(headers, COLUMN_ALIASES.transaction_type),
    tickerColumn: pickColumn(headers, COLUMN_ALIASES.ticker),
    quantityColumn: pickColumn(headers, COLUMN_ALIASES.quantity),
    priceColumn: pickColumn(headers, COLUMN_ALIASES.price),
    totalAmountColumn: pickColumn(headers, COLUMN_ALIASES.total_amount),
    currencyColumn: pickColumn(headers, COLUMN_ALIASES.currency),
    fxRateColumn: pickColumn(headers, COLUMN_ALIASES.fx_rate),
    feeColumn: pickColumn(headers, COLUMN_ALIASES.fee),
    noteColumn: pickColumn(headers, COLUMN_ALIASES.note),
    transactionTypeDefault: "BUY",
    currencyDefault: "USD",
  }
}

export function transformTransactionRow(
  row: CsvRow,
  mapping: TransactionColumnMapping,
): TransactionImportItem {
  let transactionType = normalizeType(
    mapping.typeColumn ? row[mapping.typeColumn] : undefined,
    mapping.transactionTypeDefault ?? "BUY",
  )
  const currency = (
    mapping.currencyColumn ? row[mapping.currencyColumn] : (mapping.currencyDefault ?? "USD")
  )
    .trim()
    .toUpperCase()
  const quantityFromCsv = parseNumber(
    mapping.quantityColumn ? row[mapping.quantityColumn] : undefined,
  )
  let quantity =
    quantityFromCsv ?? (transactionType === "DEPOSIT" || transactionType === "WITHDRAWAL" ? 1 : 0)
  let price = parseNumber(mapping.priceColumn ? row[mapping.priceColumn] : undefined)
  const totalFromCsv = parseNumber(
    mapping.totalAmountColumn ? row[mapping.totalAmountColumn] : undefined,
  )
  let totalAmount = totalFromCsv ?? (quantity > 0 && price != null ? quantity * price : 0)

  // Broker exports can represent cash in/out with sign only.
  // Normalize sign to positive amount and infer withdrawal from negative cash amount.
  if (CASH_MOVEMENT_TYPES.has(transactionType)) {
    const hasNegativeCashSignal =
      (price != null && price < 0) || (totalFromCsv != null && totalFromCsv < 0) || totalAmount < 0
    if (hasNegativeCashSignal) {
      transactionType = "WITHDRAWAL"
    }
    quantity = Math.abs(quantity)
    totalAmount = Math.abs(totalAmount)
    if (price != null) {
      price = Math.abs(price)
    }
  }
  const isCashMovement = CASH_MOVEMENT_TYPES.has(transactionType)
  const rawTicker = mapping.tickerColumn ? row[mapping.tickerColumn]?.trim() : ""
  const ticker = (rawTicker || (isCashMovement ? currency || "USD" : "")).trim()

  return {
    ticker: ticker.toUpperCase(),
    transaction_type: transactionType,
    quantity,
    price,
    total_amount: totalAmount,
    currency: currency || "USD",
    fx_rate: parseNumber(mapping.fxRateColumn ? row[mapping.fxRateColumn] : undefined),
    fee: parseNumber(mapping.feeColumn ? row[mapping.feeColumn] : undefined) ?? 0,
    note: mapping.noteColumn ? (row[mapping.noteColumn]?.trim() ?? "") : "",
    transaction_date: normalizeDate(mapping.dateColumn ? row[mapping.dateColumn] : undefined),
  }
}

export function transformTransactionRows(
  rows: CsvRow[],
  mapping: TransactionColumnMapping,
): TransactionImportItem[] {
  return rows.map((row) => transformTransactionRow(row, mapping))
}

export function isCashMovementRow(item: TransactionImportItem): boolean {
  return CASH_MOVEMENT_TYPES.has(item.transaction_type as TransactionType)
}

export function validateTransactionRow(item: TransactionImportItem): ValidationError[] {
  const errors: ValidationError[] = []
  if (!item.transaction_date) {
    errors.push({
      code: "missing_date",
      message: "transactions.import.error_missing_date",
    })
  }
  if (!item.ticker?.trim()) {
    errors.push({
      code: "missing_ticker",
      message: isCashMovementRow(item)
        ? "transactions.import.error_missing_ticker_cash"
        : "transactions.import.error_missing_ticker_non_cash",
    })
  }
  if (!SUPPORTED_TYPES.has(item.transaction_type as TransactionType)) {
    errors.push({
      code: "invalid_type",
      message: "transactions.import.error_invalid_type",
    })
  }
  if (!Number.isFinite(item.quantity) || item.quantity <= 0) {
    errors.push({
      code: "invalid_quantity",
      message: "transactions.import.error_invalid_quantity",
    })
  }
  if (!Number.isFinite(item.total_amount) || item.total_amount <= 0) {
    errors.push({
      code: "invalid_total",
      message: "transactions.import.error_invalid_total",
    })
  }
  if (!/^[A-Z]{3}$/.test(item.currency?.trim() ?? "")) {
    errors.push({
      code: "invalid_currency",
      message: "transactions.import.error_invalid_currency",
    })
  }
  return errors
}

export function validateTransactionRows(
  items: TransactionImportItem[],
): Map<number, ValidationError[]> {
  const byRow = new Map<number, ValidationError[]>()
  items.forEach((item, index) => {
    const errors = validateTransactionRow(item)
    if (errors.length > 0) {
      byRow.set(index, errors)
    }
  })
  return byRow
}

export function generateTransactionCsvTemplate(): string {
  const lines = [
    TEMPLATE_HEADERS.join(","),
    "2024-01-15,BUY,AAPL,10,150.00,1500.00,USD,,4.99,Example buy",
    "2024-01-15,DEPOSIT,,1,5000.00,5000.00,USD,,0,Initial deposit",
    "2024-01-20,WITHDRAWAL,,1,1200.00,1200.00,USD,,0,Cash withdrawal",
  ]
  return `\uFEFF${lines.join("\r\n")}\r\n`
}

export function parseTransactionCsvText(
  input: string,
): Promise<{ headers: string[]; rows: CsvRow[]; warnings: CsvParseWarning[] }> {
  return new Promise((resolve, reject) => {
    Papa.parse<CsvRow>(input, {
      header: true,
      skipEmptyLines: true,
      transformHeader: (header) => header.replace(/^\uFEFF/, "").trim(),
      complete: (result) => {
        const warnings: CsvParseWarning[] = result.errors.map((error) => ({
          row: error.row ?? -1,
          code: error.code,
          message: error.message,
        }))
        const rows = result.data.filter((row) =>
          Object.values(row).some((value) => (value ?? "").toString().trim() !== ""),
        )
        resolve({ headers: result.meta.fields ?? [], rows, warnings })
      },
      error: (error: Error) => reject(error),
    })
  })
}

export async function parseTransactionCSV(
  file: File,
): Promise<{ headers: string[]; rows: CsvRow[]; warnings: CsvParseWarning[] }> {
  const text = await file.text()
  return parseTransactionCsvText(text)
}
