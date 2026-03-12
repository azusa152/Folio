import { useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import {
  useAccounts,
  useAccountSummary,
  useCreateAccount,
  useDeactivateAccount,
  useUpdateAccount,
} from "@/api/hooks/useAccounts"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ACCOUNT_TYPES } from "@/lib/constants"
import { getErrorMessage } from "@/lib/utils"

interface Props {
  enabled: boolean
  onDepositToAccount?: (accountId: number, currency: string) => void
}

export function AccountsTab({ enabled, onDepositToAccount }: Props) {
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
  const [currency, setCurrency] = useState("USD")
  const [institution, setInstitution] = useState("")
  const [note, setNote] = useState("")

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

  const resetForm = () => {
    setEditingId(null)
    setName("")
    setBroker("")
    setAccountType("brokerage")
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

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div>
          <p className="text-sm font-semibold">{t("accounts.title")}</p>
          <p className="text-xs text-muted-foreground">{t("accounts.caption")}</p>
        </div>
        <Button className="text-xs min-h-[44px]" onClick={openCreate}>
          {t("accounts.add")}
        </Button>
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
          <div key={account.id} className="rounded-md border border-border p-3">
            <div className="flex items-center justify-between gap-2">
              <div>
                <p className="text-sm font-semibold">{account.name}</p>
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
              </div>
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
    </div>
  )
}
