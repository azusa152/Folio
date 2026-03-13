import { useEffect, useMemo, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { useAccounts } from "@/api/hooks/useAccounts"
import { useImportTransactions } from "@/api/hooks/useTransactions"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  autoDetectTransactionColumns,
  generateTransactionCsvTemplate,
  parseTransactionCSV,
  transformTransactionRows,
  validateTransactionRows,
  type CsvParseWarning,
  type CsvRow,
  type TransactionColumnMapping,
} from "@/lib/transaction-csv-import"

interface Props {
  open: boolean
  onClose: () => void
  defaultAccountId?: number | null
}

type Step = "select" | "map" | "preview"
type ImportMode = "append" | "replace_account"
const SKIP = "__skip__"

export function TransactionCsvImportDialog({ open, onClose, defaultAccountId }: Props) {
  const { t } = useTranslation()
  const { data: accounts } = useAccounts(open)
  const importMutation = useImportTransactions()
  const fileRef = useRef<HTMLInputElement>(null)

  const [step, setStep] = useState<Step>("select")
  const [headers, setHeaders] = useState<string[]>([])
  const [rows, setRows] = useState<CsvRow[]>([])
  const [mapping, setMapping] = useState<TransactionColumnMapping>({
    transactionTypeDefault: "BUY",
    currencyDefault: "USD",
  })
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null)
  const [importMode, setImportMode] = useState<ImportMode>("append")
  const [destructiveConfirmed, setDestructiveConfirmed] = useState(false)
  const [feedback, setFeedback] = useState<string | null>(null)
  const [parseWarnings, setParseWarnings] = useState<CsvParseWarning[]>([])

  useEffect(() => {
    if (open) {
      setSelectedAccountId(defaultAccountId ?? null)
    }
  }, [defaultAccountId, open])

  const items = useMemo(
    () => transformTransactionRows(rows, mapping),
    [rows, mapping],
  )
  const errors = useMemo(() => validateTransactionRows(items), [items])
  const hasBlockingErrors = errors.size > 0
  const hasNoRowsToImport = items.length === 0

  const reset = () => {
    setStep("select")
    setHeaders([])
    setRows([])
    setMapping({ transactionTypeDefault: "BUY", currencyDefault: "USD" })
    setSelectedAccountId(null)
    setImportMode("append")
    setDestructiveConfirmed(false)
    setFeedback(null)
    setParseWarnings([])
  }

  const handleClose = () => {
    reset()
    onClose()
  }

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    try {
      const parsed = await parseTransactionCSV(file)
      if (!parsed.headers.length) {
        setFeedback(t("transactions.import.missing_headers"))
        return
      }
      setHeaders(parsed.headers)
      setRows(parsed.rows)
      setParseWarnings(parsed.warnings)
      setMapping((prev) => ({
        ...autoDetectTransactionColumns(parsed.headers),
        transactionTypeDefault: prev.transactionTypeDefault ?? "BUY",
        currencyDefault: prev.currencyDefault ?? "USD",
      }))
      setFeedback(null)
      setStep("map")
    } catch {
      setFeedback(t("transactions.import.parse_error"))
    } finally {
      event.target.value = ""
    }
  }

  const handleDownloadTemplate = () => {
    const csv = generateTransactionCsvTemplate()
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" })
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.href = url
    link.download = "folio-transaction-template.csv"
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  const validateRequiredMappings = () => {
    if (!mapping.dateColumn) {
      setFeedback(t("transactions.import.missing_required_mapping_date"))
      return false
    }
    if (!mapping.typeColumn) {
      setFeedback(t("transactions.import.missing_required_mapping_type"))
      return false
    }
    if (!mapping.totalAmountColumn && (!mapping.priceColumn || !mapping.quantityColumn)) {
      setFeedback(t("transactions.import.missing_required_mapping_total_or_price_qty"))
      return false
    }
    if (importMode === "replace_account" && selectedAccountId == null) {
      setFeedback(t("transactions.import.select_account_for_replace"))
      return false
    }
    return true
  }

  const handleImport = () => {
    if (hasBlockingErrors || hasNoRowsToImport) return
    if (importMode === "replace_account") {
      if (selectedAccountId == null) {
        setFeedback(t("transactions.import.select_account_for_replace"))
        return
      }
      if (!destructiveConfirmed) {
        setFeedback(t("transactions.import.confirm_destructive_required"))
        return
      }
    }
    importMutation.mutate(
      {
        account_id: selectedAccountId,
        mode: importMode,
        items,
      },
      {
        onSuccess: (result) => {
          toast.success(t("transactions.import.import_success"))
          const deleted =
            typeof result === "object" &&
            result !== null &&
            "deleted" in result &&
            typeof result.deleted === "number"
              ? result.deleted
              : 0
          if (deleted > 0) {
            toast.info(t("transactions.import.replaced_count", { count: deleted }))
          }
          handleClose()
        },
        onError: () => {
          toast.error(t("transactions.import.import_error"))
        },
      },
    )
  }

  return (
    <Dialog open={open} onOpenChange={(next) => !next && handleClose()}>
      <DialogContent className="max-w-5xl">
        <DialogHeader>
          <DialogTitle>{t("transactions.import.title")}</DialogTitle>
          <DialogDescription>{t("transactions.import.description")}</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <p className="text-xs text-muted-foreground">
            {step === "select" && t("transactions.import.step_select")}
            {step === "map" && t("transactions.import.step_map")}
            {step === "preview" && t("transactions.import.step_preview")}
          </p>

          {step === "select" ? (
            <div className="space-y-3">
              <input
                ref={fileRef}
                type="file"
                accept=".csv,.tsv,text/csv,text/tab-separated-values"
                className="hidden"
                onChange={handleFileChange}
              />
              <Button type="button" onClick={() => fileRef.current?.click()}>
                {t("transactions.import.select_file")}
              </Button>
              <div className="space-y-2">
                <Button type="button" variant="outline" onClick={handleDownloadTemplate}>
                  {t("transactions.import.download_template")}
                </Button>
                <p className="text-xs text-muted-foreground">
                  {t("transactions.import.download_template_hint")}
                </p>
              </div>
            </div>
          ) : null}

          {step === "map" ? (
            <div className="space-y-3">
              <div className="space-y-1">
                <p className="text-sm font-medium">{t("transactions.import.account")}</p>
                <select
                  aria-label={t("transactions.import.account")}
                  value={selectedAccountId ?? ""}
                  onChange={(event) => {
                    const value = event.target.value
                    const nextAccountId = value ? Number(value) : null
                    setSelectedAccountId(nextAccountId)
                    if (nextAccountId == null && importMode === "replace_account") {
                      setImportMode("append")
                      setDestructiveConfirmed(false)
                    }
                  }}
                  className="w-full rounded border border-border bg-background px-3 py-2 text-sm"
                >
                  <option value="">{t("transactions.import.account_optional")}</option>
                  {(accounts ?? []).map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-2 rounded-md border p-3">
                <p className="text-sm font-medium">{t("transactions.import.import_mode")}</p>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="radio"
                    name="transaction-import-mode"
                    value="append"
                    checked={importMode === "append"}
                    onChange={() => {
                      setImportMode("append")
                      setDestructiveConfirmed(false)
                    }}
                  />
                  {t("transactions.import.mode_append")}
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="radio"
                    name="transaction-import-mode"
                    value="replace_account"
                    checked={importMode === "replace_account"}
                    disabled={selectedAccountId == null}
                    onChange={() => {
                      setImportMode("replace_account")
                      setDestructiveConfirmed(false)
                    }}
                  />
                  {t("transactions.import.mode_replace_account")}
                </label>
                {importMode === "replace_account" ? (
                  <label className="mt-2 flex items-center gap-2 rounded-md border border-amber-300 bg-amber-50/70 p-2 text-sm text-amber-800 dark:border-amber-600 dark:bg-amber-900/30 dark:text-amber-300">
                    <input
                      type="checkbox"
                      checked={destructiveConfirmed}
                      onChange={(event) => setDestructiveConfirmed(event.target.checked)}
                    />
                    {t("transactions.import.confirm_replace_account")}
                  </label>
                ) : null}
              </div>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                {(
                  [
                    ["dateColumn", "transactions.import.mapping_date"],
                    ["typeColumn", "transactions.import.mapping_type"],
                    ["tickerColumn", "transactions.import.mapping_ticker"],
                    ["quantityColumn", "transactions.import.mapping_quantity"],
                    ["priceColumn", "transactions.import.mapping_price"],
                    ["totalAmountColumn", "transactions.import.mapping_total_amount"],
                    ["currencyColumn", "transactions.import.mapping_currency"],
                    ["fxRateColumn", "transactions.import.mapping_fx_rate"],
                    ["feeColumn", "transactions.import.mapping_fee"],
                    ["noteColumn", "transactions.import.mapping_note"],
                  ] as [keyof TransactionColumnMapping, string][]
                ).map(([key, label]) => (
                  <div key={key} className="space-y-1">
                    <p className="text-xs text-muted-foreground">{t(label)}</p>
                    <select
                      value={(mapping[key] as string | undefined) ?? SKIP}
                      onChange={(event) => {
                        const nextValue = event.target.value
                        setMapping((prev) => ({
                          ...prev,
                          [key]: nextValue === SKIP ? undefined : nextValue,
                        }))
                      }}
                      className="w-full rounded border border-border bg-background px-3 py-2 text-sm"
                    >
                      <option value={SKIP}>{t("transactions.import.skip_column")}</option>
                      {headers.map((header) => (
                        <option key={`${key}-${header}`} value={header}>
                          {header}
                        </option>
                      ))}
                    </select>
                    {key === "totalAmountColumn" &&
                    !mapping.totalAmountColumn &&
                    mapping.priceColumn &&
                    mapping.quantityColumn ? (
                      <p className="text-[11px] text-muted-foreground">
                        {t("transactions.import.total_amount_auto_hint")}
                      </p>
                    ) : null}
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          {step === "preview" ? (
            <div className="space-y-3">
              <p className="text-sm font-semibold">{t("transactions.import.preview_title")}</p>
              <p className="text-xs text-muted-foreground">
                {t("transactions.import.total_rows", { count: items.length })} /{" "}
                {t("transactions.import.error_rows", { count: errors.size })}
              </p>
              {parseWarnings.length > 0 ? (
                <div className="rounded-md border border-amber-300 bg-amber-50/70 p-3 text-xs">
                  <p className="font-medium">{t("transactions.import.parse_warnings_title")}</p>
                  {parseWarnings.slice(0, 5).map((warning) => (
                    <p key={`${warning.row}-${warning.code}`}>
                      {t("transactions.import.parse_warning_item", {
                        row: warning.row,
                        code: warning.code,
                        message: warning.message,
                      })}
                    </p>
                  ))}
                </div>
              ) : null}
              <div className="max-h-72 overflow-auto rounded-md border">
                <table className="w-full text-xs">
                  <thead className="bg-muted/60">
                    <tr>
                      <th className="px-2 py-2 text-left">{t("transactions.import.mapping_date")}</th>
                      <th className="px-2 py-2 text-left">{t("transactions.import.mapping_type")}</th>
                      <th className="px-2 py-2 text-left">{t("transactions.import.mapping_ticker")}</th>
                      <th className="px-2 py-2 text-left">{t("transactions.import.mapping_total_amount")}</th>
                      <th className="px-2 py-2 text-left">{t("transactions.import.status")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.slice(0, 30).map((item, index) => (
                      <tr key={`${item.ticker}-${index}`} className="border-t">
                        <td className="px-2 py-1.5">{item.transaction_date}</td>
                        <td className="px-2 py-1.5">{item.transaction_type}</td>
                        <td className="px-2 py-1.5">{item.ticker}</td>
                        <td className="px-2 py-1.5">{item.total_amount}</td>
                        <td className="px-2 py-1.5">
                          {errors.has(index)
                            ? errors
                                .get(index)
                                ?.map((error) => t(error.message))
                                .join(" ")
                            : t("transactions.import.valid")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}

          {feedback ? <p className="text-sm text-destructive">{feedback}</p> : null}
        </div>

        <DialogFooter>
          {step !== "select" ? (
            <Button
              type="button"
              variant="outline"
              onClick={() => setStep(step === "preview" ? "map" : "select")}
            >
              {t("transactions.import.back")}
            </Button>
          ) : (
            <Button type="button" variant="outline" onClick={handleClose}>
              {t("transactions.import.close")}
            </Button>
          )}
          {step === "map" ? (
            <Button
              type="button"
              onClick={() => {
                if (!validateRequiredMappings()) return
                setFeedback(null)
                setStep("preview")
              }}
            >
              {t("transactions.import.next")}
            </Button>
          ) : null}
          {step === "preview" ? (
            <Button
              type="button"
              onClick={handleImport}
              disabled={hasBlockingErrors || hasNoRowsToImport || importMutation.isPending}
            >
              {t("transactions.import.confirm_import", { count: items.length })}
            </Button>
          ) : null}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
