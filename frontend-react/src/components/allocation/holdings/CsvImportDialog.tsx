import { useMemo, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { useAccounts } from "@/api/hooks/useAccounts"
import { useImportHoldings } from "@/api/hooks/useAllocation"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { CsvColumnMapper } from "@/components/allocation/holdings/CsvColumnMapper"
import { CsvPreviewTable } from "@/components/allocation/holdings/CsvPreviewTable"
import {
  autoDetectColumns,
  parseCSV,
  isCashRow,
  transformRows,
  validateRows,
  type CsvParseWarning,
  type ColumnMapping,
  type CsvRow,
} from "@/lib/csv-import"

interface Props {
  open: boolean
  onClose: () => void
}

type Step = "select" | "map" | "preview"
type ImportMode = "replace_all" | "replace_account" | "append"

const TEMPLATE_URL = "/templates/holdings_csv_template.csv"

export function CsvImportDialog({ open, onClose }: Props) {
  const { t } = useTranslation()
  const importMutation = useImportHoldings()
  const { data: accounts } = useAccounts(open, true)
  const fileRef = useRef<HTMLInputElement>(null)

  const [step, setStep] = useState<Step>("select")
  const [headers, setHeaders] = useState<string[]>([])
  const [rows, setRows] = useState<CsvRow[]>([])
  const [mapping, setMapping] = useState<ColumnMapping>({
    categoryDefault: "Growth",
    currencyDefault: "USD",
  })
  const [feedback, setFeedback] = useState<string | null>(null)
  const [parseWarnings, setParseWarnings] = useState<CsvParseWarning[]>([])
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null)
  const [importMode, setImportMode] = useState<ImportMode>("append")
  const [destructiveConfirmed, setDestructiveConfirmed] = useState(false)

  const selectedAccount = useMemo(
    () => (accounts ?? []).find((account) => account.id === selectedAccountId) ?? null,
    [accounts, selectedAccountId],
  )
  const items = useMemo(() => transformRows(rows, mapping), [rows, mapping])
  const itemsWithAccount = useMemo(
    () =>
      items.map((item) => ({
        ...item,
        account_id: selectedAccountId,
      })),
    [items, selectedAccountId],
  )
  const errors = useMemo(() => validateRows(itemsWithAccount), [itemsWithAccount])
  const hasBlockingErrors = errors.size > 0
  const hasNoRowsToImport = itemsWithAccount.length === 0
  const isDestructiveMode = importMode === "replace_all" || importMode === "replace_account"

  const reset = () => {
    setStep("select")
    setHeaders([])
    setRows([])
    setFeedback(null)
    setParseWarnings([])
    setSelectedAccountId(null)
    setImportMode("append")
    setDestructiveConfirmed(false)
    setMapping({ categoryDefault: "Growth", currencyDefault: "USD" })
  }

  const handleClose = () => {
    reset()
    onClose()
  }

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      const parsed = await parseCSV(file)
      if (!parsed.headers.length) {
        setFeedback(t("allocation.csv_import.missing_headers"))
        return
      }
      setHeaders(parsed.headers)
      setRows(parsed.rows)
      setParseWarnings(parsed.warnings)
      setMapping((prev) => ({ ...autoDetectColumns(parsed.headers), categoryDefault: prev.categoryDefault ?? "Growth", currencyDefault: prev.currencyDefault ?? "USD" }))
      setFeedback(null)
      setStep("map")
    } catch {
      setFeedback(t("allocation.csv_import.parse_error"))
    } finally {
      e.target.value = ""
    }
  }

  const validateRequiredMappings = () => {
    if (!mapping.quantityColumn) {
      setFeedback(t("allocation.csv_import.missing_required_mapping_quantity"))
      return false
    }
    if (!mapping.categoryColumn && !mapping.categoryDefault) {
      setFeedback(t("allocation.csv_import.missing_required_mapping_category"))
      return false
    }
    const hasNonCashRows = items.some((item) => !isCashRow(item))
    if (hasNonCashRows && !mapping.tickerColumn) {
      setFeedback(t("allocation.csv_import.missing_required_mapping_ticker_non_cash"))
      return false
    }
    return true
  }

  const goToPreview = () => {
    if (importMode === "replace_account" && selectedAccountId == null) {
      setFeedback(t("allocation.csv_import.select_account_for_replace"))
      return
    }
    if (!validateRequiredMappings()) return
    setFeedback(null)
    setStep("preview")
  }

  const handleImport = () => {
    if (hasBlockingErrors) return
    if (hasNoRowsToImport) {
      setFeedback(t("allocation.csv_import.no_rows_to_import"))
      return
    }
    if (importMode === "replace_account" && selectedAccountId == null) {
      setFeedback(t("allocation.csv_import.select_account_for_replace"))
      return
    }
    if (isDestructiveMode && !destructiveConfirmed) {
      setFeedback(t("allocation.csv_import.confirm_destructive_required"))
      return
    }
    importMutation.mutate(
      {
        mode: importMode,
        account_id: selectedAccountId,
        items: itemsWithAccount,
      },
      {
      onSuccess: () => {
        toast.success(t("allocation.csv_import.import_success"))
        handleClose()
      },
      onError: () => {
        toast.error(t("allocation.csv_import.import_error"))
      },
      },
    )
  }

  return (
    <Dialog open={open} onOpenChange={(next) => !next && handleClose()}>
      <DialogContent className="max-w-5xl">
        <DialogHeader>
          <DialogTitle>{t("allocation.csv_import.title")}</DialogTitle>
          <DialogDescription>{t("allocation.csv_import.description")}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <p className="text-xs text-muted-foreground">
            {step === "select" && t("allocation.csv_import.step_select")}
            {step === "map" && t("allocation.csv_import.step_map")}
            {step === "preview" && t("allocation.csv_import.step_preview")}
          </p>

          {step === "select" && (
            <div className="space-y-3">
              <input
                ref={fileRef}
                type="file"
                accept=".csv,.tsv,text/csv,text/tab-separated-values"
                className="hidden"
                onChange={handleFileChange}
              />
              <div className="flex gap-2">
                <Button type="button" onClick={() => fileRef.current?.click()}>
                  {t("allocation.csv_import.select_file")}
                </Button>
                <Button asChild variant="outline">
                  <a href={TEMPLATE_URL} download>
                    {t("allocation.csv_import.download_template")}
                  </a>
                </Button>
              </div>
            </div>
          )}

          {step === "map" && (
            <div className="space-y-3">
              <div className="space-y-1">
                <p className="text-sm font-medium">{t("allocation.csv_import.account")}</p>
                <select
                  aria-label={t("allocation.csv_import.account")}
                  value={selectedAccountId ?? ""}
                  onChange={(event) => {
                    const value = event.target.value
                    const nextAccountId = value ? Number(value) : null
                    setSelectedAccountId(nextAccountId)
                    const account = (accounts ?? []).find((item) => item.id === nextAccountId)
                    setMapping((prev) => ({
                      ...prev,
                      brokerDefault: account?.broker ?? prev.brokerDefault,
                    }))
                  }}
                  className="w-full rounded border border-border bg-background px-3 py-2 text-sm"
                >
                  <option value="">{t("allocation.csv_import.account_optional")}</option>
                  {(accounts ?? []).map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.name}
                    </option>
                  ))}
                </select>
              </div>
              <CsvColumnMapper headers={headers} mapping={mapping} onMappingChange={setMapping} />
            </div>
          )}

          {step === "preview" && (
            <div className="space-y-3">
              <CsvPreviewTable items={items} errors={errors} parseWarnings={parseWarnings} />
              <div className="space-y-2 rounded-md border p-3">
                <p className="text-sm font-medium">{t("allocation.csv_import.import_mode")}</p>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="radio"
                    name="import-mode"
                    value="append"
                    checked={importMode === "append"}
                    onChange={() => { setImportMode("append"); setDestructiveConfirmed(false) }}
                  />
                  {t("allocation.csv_import.mode_append")}
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="radio"
                    name="import-mode"
                    value="replace_account"
                    checked={importMode === "replace_account"}
                    disabled={!selectedAccount}
                    onChange={() => { setImportMode("replace_account"); setDestructiveConfirmed(false) }}
                  />
                  {t("allocation.csv_import.mode_replace_account")}
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="radio"
                    name="import-mode"
                    value="replace_all"
                    checked={importMode === "replace_all"}
                    onChange={() => { setImportMode("replace_all"); setDestructiveConfirmed(false) }}
                  />
                  {t("allocation.csv_import.mode_replace_all")}
                </label>
                {isDestructiveMode && (
                  <label className="mt-2 flex items-center gap-2 rounded-md border border-amber-300 bg-amber-50/70 p-2 text-sm text-amber-800 dark:border-amber-600 dark:bg-amber-900/30 dark:text-amber-300">
                    <input
                      type="checkbox"
                      checked={destructiveConfirmed}
                      onChange={(e) => setDestructiveConfirmed(e.target.checked)}
                    />
                    {importMode === "replace_all"
                      ? t("allocation.csv_import.confirm_replace_all")
                      : t("allocation.csv_import.confirm_replace_account")}
                  </label>
                )}
              </div>
            </div>
          )}

          {feedback ? <p className="text-sm text-destructive">{feedback}</p> : null}
        </div>

        <DialogFooter>
          {step !== "select" ? (
            <Button type="button" variant="outline" onClick={() => setStep(step === "preview" ? "map" : "select")}>
              {t("allocation.csv_import.back")}
            </Button>
          ) : null}
          {step === "select" ? (
            <Button type="button" variant="outline" onClick={handleClose}>
              {t("allocation.csv_import.close")}
            </Button>
          ) : null}
          {step === "map" ? (
            <Button type="button" onClick={goToPreview}>
              {t("allocation.csv_import.next")}
            </Button>
          ) : null}
          {step === "preview" ? (
            <Button
              type="button"
              onClick={handleImport}
              disabled={hasBlockingErrors || importMutation.isPending || hasNoRowsToImport}
            >
              {t("allocation.csv_import.confirm_import", { count: itemsWithAccount.length })}
            </Button>
          ) : null}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
