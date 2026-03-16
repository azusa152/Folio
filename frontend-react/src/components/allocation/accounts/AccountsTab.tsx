import { useMemo, useState } from "react"
import { Download, Info, Upload } from "lucide-react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import {
  useAccounts,
  useAccountPositions,
  useAccountSummary,
  useAccountTransactions,
  useCreateAccount,
  useDeactivateAccount,
  useUpdateAccount,
} from "@/api/hooks/useAccounts"
import { TransactionList } from "@/components/allocation/transactions/TransactionList"
import { TransactionCsvImportDialog } from "@/components/allocation/transactions/TransactionCsvImportDialog"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { useTransactions } from "@/api/hooks/useTransactions"
import {
  ACCOUNT_TYPES,
  isTaxWrapperType,
  TAX_WRAPPER_ICONS,
  TAX_WRAPPER_TYPES,
  type TaxWrapperType,
} from "@/lib/constants"
import { formatPrice, formatQuantity, getQuantityUnitKey } from "@/lib/format"
import { getErrorMessage } from "@/lib/utils"

interface Props {
  enabled: boolean
  onDepositToAccount?: (accountId: number, currency: string) => void
  onRecordTransaction?: (accountId: number, currency: string) => void
}

type AccountDetailView = "positions" | "transactions" | "summary"

export function AccountsTab({
  enabled,
  onDepositToAccount,
  onRecordTransaction,
}: Props) {
  const { t } = useTranslation()
  const { data: accounts, isLoading } = useAccounts(enabled)
  const { data: accountSummary } = useAccountSummary(enabled)
  const createAccount = useCreateAccount()
  const updateAccount = useUpdateAccount()
  const deactivateAccount = useDeactivateAccount()

  const [formOpen, setFormOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [name, setName] = useState("")
  const [broker, setBroker] = useState("")
  const [accountType, setAccountType] = useState<(typeof ACCOUNT_TYPES)[number]>("brokerage")
  const [taxWrapper, setTaxWrapper] = useState<TaxWrapperType | null>(null)
  const [currency, setCurrency] = useState("USD")
  const [institution, setInstitution] = useState("")
  const [note, setNote] = useState("")
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null)
  const [detailView, setDetailView] = useState<AccountDetailView>("positions")
  const [importDialogOpen, setImportDialogOpen] = useState(false)
  const [exportingCsv, setExportingCsv] = useState(false)
  const [exportScope, setExportScope] = useState<"selected" | "all">("selected")

  const sortedAccounts = useMemo(
    () => [...(accounts ?? [])].sort((a, b) => a.name.localeCompare(b.name)),
    [accounts],
  )
  const summaryByAccountId = useMemo(() => {
    const map = new Map<number, { holdings_count: number; cash_balances: Array<{ currency: string; balance: number }> }>()
    for (const item of accountSummary ?? []) {
      if (item.account?.id == null) continue
      map.set(item.account.id, {
        holdings_count: item.holdings_count,
        cash_balances: item.cash_balances ?? [],
      })
    }
    return map
  }, [accountSummary])
  const activeAccountId = useMemo(() => {
    if (sortedAccounts.length === 0) return null
    if (selectedAccountId == null) return sortedAccounts[0].id
    return sortedAccounts.some((account) => account.id === selectedAccountId)
      ? selectedAccountId
      : sortedAccounts[0].id
  }, [sortedAccounts, selectedAccountId])

  const selectedAccount = useMemo(
    () => sortedAccounts.find((account) => account.id === activeAccountId) ?? null,
    [sortedAccounts, activeAccountId],
  )
  const { data: selectedAccountPositions, isLoading: isPositionsLoading } = useAccountPositions(
    selectedAccount?.id ?? null,
    enabled && selectedAccount != null,
  )
  const { data: selectedAccountTransactions, isLoading: isTransactionsLoading } = useAccountTransactions(
    selectedAccount?.id ?? null,
    enabled && selectedAccount != null,
  )
  const { data: allTransactions } = useTransactions({ enabled, limit: 1 })
  const effectiveExportScope = exportScope === "selected" && selectedAccount?.id != null ? "selected" : "all"
  const selectedScopeHasTransactions = (selectedAccountTransactions?.length ?? 0) > 0
  const allScopeHasTransactions = (allTransactions?.length ?? 0) > 0
  const exportDisabled = exportingCsv || (effectiveExportScope === "selected"
    ? !selectedScopeHasTransactions
    : !allScopeHasTransactions)

  const resetForm = () => {
    setEditingId(null)
    setName("")
    setBroker("")
    setAccountType("brokerage")
    setTaxWrapper(null)
    setCurrency("USD")
    setInstitution("")
    setNote("")
  }

  const openCreate = () => {
    resetForm()
    setFormOpen(true)
  }

  const openEdit = (account: {
    id: number
    name: string
    broker: string
    account_type: string
    tax_wrapper?: string | null
    currency: string
    institution: string
    note: string
  }) => {
    setEditingId(account.id)
    setName(account.name)
    setBroker(account.broker)
    setAccountType(
      ACCOUNT_TYPES.includes(account.account_type as (typeof ACCOUNT_TYPES)[number])
        ? (account.account_type as (typeof ACCOUNT_TYPES)[number])
        : "other",
    )
    setTaxWrapper(
      isTaxWrapperType(account.tax_wrapper)
        ? account.tax_wrapper
        : null,
    )
    setCurrency(account.currency || "USD")
    setInstitution(account.institution || "")
    setNote(account.note || "")
    setFormOpen(true)
  }

  const submit = () => {
    if (!name.trim() || !broker.trim()) {
      toast.error(t("accounts.form.error_required"))
      return
    }

    const payload = {
      name: name.trim(),
      broker: broker.trim(),
      account_type: accountType,
      tax_wrapper: taxWrapper,
      currency: currency.trim().toUpperCase() || "USD",
      institution: institution.trim(),
      note: note.trim(),
    }

    if (editingId == null) {
      createAccount.mutate(payload, {
        onSuccess: (createdAccount) => {
          toast.success(t("accounts.toast.created"), {
            description: t("accounts.toast.created_deposit"),
            action: onDepositToAccount
              ? {
                  label: t("accounts.quick_deposit"),
                  onClick: () => onDepositToAccount(createdAccount.id, createdAccount.currency || "USD"),
                }
              : undefined,
          })
          setFormOpen(false)
          resetForm()
        },
        onError: (err: unknown) => {
          toast.error(getErrorMessage(err) || t("common.error"))
        },
      })
      return
    }

    updateAccount.mutate(
      { accountId: editingId, payload },
      {
        onSuccess: () => {
          toast.success(t("accounts.toast.updated"))
          setFormOpen(false)
          resetForm()
        },
        onError: (err: unknown) => {
          toast.error(getErrorMessage(err) || t("common.error"))
        },
      },
    )
  }

  const handleExportCsv = async () => {
    setExportingCsv(true)
    try {
      const headers: HeadersInit = {}
      const apiKey = import.meta.env.VITE_API_KEY
      if (apiKey) headers["X-API-Key"] = apiKey

      const params = new URLSearchParams()
      if (effectiveExportScope === "selected" && selectedAccount?.id != null) {
        params.set("account_id", String(selectedAccount.id))
      }
      const requestUrl = params.toString()
        ? `/api/transactions/export-csv?${params.toString()}`
        : "/api/transactions/export-csv"
      const response = await fetch(requestUrl, {
        headers,
      })
      if (!response.ok) throw new Error(response.statusText)

      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const link = document.createElement("a")
      const contentDisposition = response.headers.get("Content-Disposition") || ""
      const filenameMatch = contentDisposition.match(/filename="([^"]+)"/)
      link.download = filenameMatch?.[1] || "transactions.csv"
      link.href = url
      link.click()
      URL.revokeObjectURL(url)
    } catch {
      toast.error(t("transactions.export_error"))
    } finally {
      setExportingCsv(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div>
          <p className="text-sm font-semibold">{t("accounts.title")}</p>
          <p className="text-xs text-muted-foreground">{t("accounts.caption")}</p>
        </div>
        <div className="flex items-center gap-2">
          <select
            aria-label={t("transactions.filter.account")}
            value={exportScope}
            onChange={(event) => setExportScope(event.target.value as "selected" | "all")}
            className="h-9 rounded-md border border-border bg-background px-2 text-xs"
          >
            <option value="selected" disabled={selectedAccount == null}>
              {selectedAccount?.name ?? t("transactions.filter.account")}
            </option>
            <option value="all">{t("transactions.filter.all_accounts")}</option>
          </select>
          <Button
            variant="outline"
            size="sm"
            className="text-xs min-h-[44px]"
            onClick={() => setImportDialogOpen(true)}
          >
            <Upload className="mr-1 h-3.5 w-3.5" />
            {t("transactions.import_button")}
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="text-xs min-h-[44px]"
            onClick={handleExportCsv}
            disabled={exportDisabled}
          >
            <Download className="mr-1 h-3.5 w-3.5" />
            {t("transactions.export_button")}
          </Button>
          <Button className="text-xs min-h-[44px]" onClick={openCreate}>
            {t("accounts.add")}
          </Button>
        </div>
      </div>

      {formOpen ? (
        <div className="rounded-md border border-border p-3 space-y-3">
          <p className="text-xs font-semibold">
            {editingId == null ? t("accounts.form.create_title") : t("accounts.form.edit_title")}
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <Input
              aria-label={t("accounts.form.name")}
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder={t("accounts.form.name")}
              className="text-xs"
            />
            <Input
              aria-label={t("accounts.form.broker")}
              value={broker}
              onChange={(event) => setBroker(event.target.value)}
              placeholder={t("accounts.form.broker")}
              className="text-xs"
            />
            <select
              aria-label={t("accounts.form.account_type")}
              value={accountType}
              onChange={(event) => setAccountType(event.target.value as (typeof ACCOUNT_TYPES)[number])}
              className="w-full text-xs border border-border rounded px-2 py-1.5 bg-background"
            >
              {ACCOUNT_TYPES.map((value) => (
                <option key={value} value={value}>
                  {t(`config.account_type.${value}`)}
                </option>
              ))}
            </select>
            <select
              aria-label={t("wrapper.select_wrapper")}
              value={taxWrapper ?? ""}
              onChange={(event) => {
                const value = event.target.value
                setTaxWrapper(
                  isTaxWrapperType(value)
                    ? value
                    : null,
                )
              }}
              className="w-full text-xs border border-border rounded px-2 py-1.5 bg-background"
            >
              <option value="">{t("wrapper.no_wrapper")}</option>
              {TAX_WRAPPER_TYPES.map((value) => (
                <option key={value} value={value}>
                  {TAX_WRAPPER_ICONS[value]} {t(`wrapper.${value}`)}
                </option>
              ))}
            </select>
            <Input
              aria-label={t("accounts.form.currency")}
              value={currency}
              onChange={(event) => setCurrency(event.target.value.toUpperCase())}
              placeholder={t("accounts.form.currency")}
              className="text-xs"
            />
            <Input
              aria-label={t("accounts.form.institution")}
              value={institution}
              onChange={(event) => setInstitution(event.target.value)}
              placeholder={t("accounts.form.institution")}
              className="text-xs sm:col-span-2"
            />
            <Input
              aria-label={t("accounts.form.note")}
              value={note}
              onChange={(event) => setNote(event.target.value)}
              placeholder={t("accounts.form.note")}
              className="text-xs sm:col-span-2"
            />
          </div>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              onClick={submit}
              disabled={createAccount.isPending || updateAccount.isPending}
            >
              {t("accounts.form.save")}
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                setFormOpen(false)
                resetForm()
              }}
            >
              {t("common.cancel")}
            </Button>
          </div>
        </div>
      ) : null}

      {isLoading ? <p className="text-xs text-muted-foreground">{t("common.loading")}</p> : null}

      {!isLoading && sortedAccounts.length === 0 ? (
        <div className="rounded-md border border-dashed border-border bg-muted/20 p-5 space-y-2">
          <p className="text-sm font-semibold">{t("accounts.empty.title")}</p>
          <p className="text-xs text-muted-foreground">{t("accounts.empty.description")}</p>
        </div>
      ) : null}

      <div className="space-y-2">
        {sortedAccounts.map((account) => (
          <div
            key={account.id}
            className={`rounded-md border p-3 transition-colors ${
              activeAccountId === account.id
                ? "border-primary bg-primary/5"
                : "border-border"
            }`}
          >
            <div className="flex items-center justify-between gap-2">
              <button
                type="button"
                className="text-left flex-1"
                onClick={() => setSelectedAccountId(account.id)}
              >
                <div className="flex items-center gap-2">
                  <p className="text-sm font-semibold">{account.name}</p>
                  {isTaxWrapperType(account.tax_wrapper) ? (
                    <Badge variant="outline" className="text-[11px]">
                      {TAX_WRAPPER_ICONS[account.tax_wrapper]}{" "}
                      {t(`wrapper.${account.tax_wrapper}`)}
                    </Badge>
                  ) : null}
                </div>
                <p className="text-xs text-muted-foreground">
                  {account.broker} · {t(`config.account_type.${account.account_type}`)} · {account.currency}
                </p>
                <p className="text-[11px] text-muted-foreground mt-1">
                  {t("accounts.summary.positions", {
                    count: summaryByAccountId.get(account.id)?.holdings_count ?? 0,
                  })}
                </p>
                <p className="text-[11px] text-muted-foreground">
                  {t("accounts.summary.cash", {
                    balances:
                      (summaryByAccountId.get(account.id)?.cash_balances ?? [])
                        .map((item) => `${item.currency} ${item.balance.toLocaleString(undefined, { maximumFractionDigits: 2 })}`)
                        .join(" / ") || t("accounts.summary.no_cash"),
                  })}
                </p>
              </button>
              <div className="flex gap-2">
                {onDepositToAccount ? (
                  <Button
                    size="sm"
                    variant="secondary"
                    className="text-xs"
                    onClick={() => onDepositToAccount(account.id, account.currency || "USD")}
                  >
                    {t("accounts.quick_deposit")}
                  </Button>
                ) : null}
                {onRecordTransaction ? (
                  <Button
                    size="sm"
                    variant="outline"
                    className="text-xs"
                    onClick={() => onRecordTransaction(account.id, account.currency || "USD")}
                  >
                    {t("transactions.record_button")}
                  </Button>
                ) : null}
                <Button size="sm" variant="outline" className="text-xs" onClick={() => openEdit(account)}>
                  {t("common.edit")}
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  className="text-xs text-destructive"
                  onClick={() => {
                    deactivateAccount.mutate(account.id, {
                      onSuccess: () => toast.success(t("accounts.toast.deactivated")),
                      onError: (err: unknown) => toast.error(getErrorMessage(err) || t("common.error")),
                    })
                  }}
                >
                  {t("common.delete")}
                </Button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {selectedAccount ? (
        <div className="rounded-md border border-border p-3 space-y-3">
          <div>
            <div className="flex items-center gap-2">
              <p className="text-sm font-semibold">{selectedAccount.name}</p>
              {isTaxWrapperType(selectedAccount.tax_wrapper) ? (
                <Badge variant="outline" className="text-[11px]">
                  {TAX_WRAPPER_ICONS[selectedAccount.tax_wrapper]}{" "}
                  {t(`wrapper.${selectedAccount.tax_wrapper}`)}
                </Badge>
              ) : null}
            </div>
            <p className="text-xs text-muted-foreground">
              {selectedAccount.broker} · {t(`config.account_type.${selectedAccount.account_type}`)} · {selectedAccount.currency}
            </p>
          </div>

          <Tabs value={detailView} onValueChange={(value) => setDetailView(value as AccountDetailView)}>
            <TabsList className="flex-wrap h-auto min-h-[44px] gap-1">
              <TabsTrigger value="positions" className="min-h-[44px]">
                {t("accounts.detail.positions")}
              </TabsTrigger>
              <TabsTrigger value="transactions" className="min-h-[44px]">
                {t("accounts.detail.transactions")}
              </TabsTrigger>
              <TabsTrigger value="summary" className="min-h-[44px]">
                {t("accounts.detail.summary")}
              </TabsTrigger>
            </TabsList>

            <TabsContent value="positions" className="mt-3">
              {isPositionsLoading ? (
                <p className="text-xs text-muted-foreground">{t("common.loading")}</p>
              ) : (selectedAccountPositions?.length ?? 0) === 0 ? (
                <div className="rounded-md border border-dashed border-border bg-muted/20 p-4">
                  <p className="text-xs text-muted-foreground">{t("accounts.detail.empty_positions")}</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-muted-foreground border-b border-border">
                        <th className="text-left py-1.5 pr-2">{t("transactions.table.ticker")}</th>
                        <th className="text-left py-1.5 pr-2">{t("accounts.detail.category")}</th>
                        <th className="text-right py-1.5 pr-2">{t("transactions.table.quantity")}</th>
                        <th className="text-right py-1.5 pr-2">
                          <div className="inline-flex items-center justify-end gap-1">
                            <span>{t("accounts.detail.cost_basis")}</span>
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <Info
                                    className="h-3 w-3 cursor-help text-muted-foreground"
                                    aria-label={t("allocation.col.cost_tooltip")}
                                  />
                                </TooltipTrigger>
                                <TooltipContent>
                                  <p className="max-w-[220px]">{t("allocation.col.cost_tooltip")}</p>
                                </TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                          </div>
                        </th>
                        <th className="text-left py-1.5 pr-2">{t("transactions.form.currency")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(selectedAccountPositions ?? []).map((position) => {
                        const quantityUnit = getQuantityUnitKey(position.category, position.ticker)
                        const quantityText = t(quantityUnit.key, {
                          quantity: formatQuantity(position.quantity, {
                            category: position.category,
                            ticker: position.ticker,
                          }),
                          ...quantityUnit.params,
                        })

                        return (
                          <tr key={position.id} className="border-b border-border/50">
                            <td className="py-1.5 pr-2 font-medium">{position.ticker}</td>
                            <td className="py-1.5 pr-2">
                              <div className="flex items-center gap-1.5">
                                <Badge variant="secondary" className="text-[11px]">
                                  {t(`config.category.${String(position.category).toLowerCase()}`)}
                                </Badge>
                                {position.is_cash ? (
                                  <Badge variant="outline" className="text-[11px]">
                                    {t("accounts.detail.cash_position")}
                                  </Badge>
                                ) : null}
                              </div>
                            </td>
                            <td className="py-1.5 pr-2 text-right">{quantityText}</td>
                            <td className="py-1.5 pr-2 text-right">
                              {position.cost_basis != null
                                ? formatPrice(position.cost_basis, position.currency || selectedAccount.currency)
                                : "—"}
                            </td>
                            <td className="py-1.5 pr-2">{position.currency}</td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </TabsContent>

            <TabsContent value="transactions" className="mt-3">
              <TransactionList
                transactions={selectedAccountTransactions ?? []}
                accounts={selectedAccount ? [selectedAccount] : []}
                isLoading={isTransactionsLoading}
              />
            </TabsContent>

            <TabsContent value="summary" className="mt-3 space-y-1">
              <p className="text-xs text-muted-foreground">
                {t("accounts.summary.positions", {
                  count: summaryByAccountId.get(selectedAccount.id)?.holdings_count ?? 0,
                })}
              </p>
              <p className="text-xs text-muted-foreground">
                {t("accounts.summary.cash", {
                  balances:
                    (summaryByAccountId.get(selectedAccount.id)?.cash_balances ?? [])
                      .map(
                        (item) =>
                          `${item.currency} ${item.balance.toLocaleString(undefined, { maximumFractionDigits: 2 })}`,
                      )
                      .join(" / ") || t("accounts.summary.no_cash"),
                })}
              </p>
            </TabsContent>
          </Tabs>
        </div>
      ) : null}
      <TransactionCsvImportDialog
        open={importDialogOpen}
        onClose={() => setImportDialogOpen(false)}
        defaultAccountId={selectedAccount?.id ?? null}
      />
    </div>
  )
}
