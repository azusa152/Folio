import { useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import type { AccountResponse } from "@/api/types/account"
import { useDeleteTransaction } from "@/api/hooks/useTransactions"
import type { TransactionResponse } from "@/api/types/transaction"
import {
  formatCurrency,
  formatQuantity,
  getTransactionQuantityUnitKey,
} from "@/lib/format"
import { getErrorMessage } from "@/lib/utils"

interface Props {
  transactions: TransactionResponse[]
  accounts: AccountResponse[]
  isLoading: boolean
}

function typeBadgeClass(type: string): string {
  if (type === "BUY") return "bg-emerald-600/15 text-emerald-700 dark:text-emerald-300"
  if (type === "SELL") return "bg-rose-600/15 text-rose-700 dark:text-rose-300"
  if (type === "DIVIDEND") return "bg-sky-600/15 text-sky-700 dark:text-sky-300"
  if (type === "DEPOSIT") return "bg-violet-600/15 text-violet-700 dark:text-violet-300"
  return "bg-amber-600/15 text-amber-700 dark:text-amber-300"
}

export function TransactionList({ transactions, accounts, isLoading }: Props) {
  const { t } = useTranslation()
  const deleteMutation = useDeleteTransaction()
  const [pendingDeleteId, setPendingDeleteId] = useState<number | null>(null)
  const accountMap = new Map(accounts.map((account) => [account.id, account.name]))

  if (isLoading) {
    return <p className="text-xs text-muted-foreground">{t("common.loading")}</p>
  }

  if (transactions.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-border bg-muted/20 p-5 space-y-2">
        <p className="text-sm font-semibold">{t("transactions.empty.title")}</p>
        <p className="text-xs text-muted-foreground">{t("transactions.empty.description")}</p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="text-muted-foreground border-b border-border">
            <th className="text-left py-1.5 pr-2">{t("transactions.table.date")}</th>
            <th className="text-left py-1.5 pr-2">{t("transactions.table.ticker")}</th>
            <th className="text-left py-1.5 pr-2">{t("transactions.table.account")}</th>
            <th className="text-left py-1.5 pr-2">{t("transactions.table.type")}</th>
            <th className="text-right py-1.5 pr-2">{t("transactions.table.quantity")}</th>
            <th className="text-right py-1.5 pr-2">{t("transactions.table.price")}</th>
            <th className="text-right py-1.5 pr-2">{t("transactions.table.total_amount")}</th>
            <th className="text-right py-1.5">{t("transactions.table.actions")}</th>
          </tr>
        </thead>
        <tbody>
          {transactions.map((transaction) => {
            const quantityUnit = getTransactionQuantityUnitKey({
              transactionType: transaction.transaction_type,
              category: transaction.category,
              ticker: transaction.ticker,
              currency: transaction.currency,
              isCash: transaction.is_cash,
            })
            const quantityText = t(quantityUnit.key, {
              quantity: formatQuantity(transaction.quantity, {
                category: transaction.category ?? undefined,
                ticker: transaction.ticker,
              }),
              ...quantityUnit.params,
            })

            return (
              <tr key={transaction.id} className="border-b border-border/50">
                <td className="py-1.5 pr-2 whitespace-nowrap">{transaction.transaction_date}</td>
                <td className="py-1.5 pr-2 font-medium">{transaction.ticker}</td>
                <td className="py-1.5 pr-2">
                  {transaction.account_id != null ? accountMap.get(transaction.account_id) ?? "—" : "—"}
                </td>
                <td className="py-1.5 pr-2">
                  <Badge variant="secondary" className={typeBadgeClass(transaction.transaction_type)}>
                    {t(`transactions.type.${transaction.transaction_type.toLowerCase()}`)}
                  </Badge>
                </td>
                <td className="py-1.5 pr-2 text-right">{quantityText}</td>
                <td className="py-1.5 pr-2 text-right">
                  {transaction.price != null
                    ? formatCurrency(transaction.price, transaction.currency || "USD")
                    : "—"}
                </td>
                <td className="py-1.5 pr-2 text-right">
                  {formatCurrency(transaction.total_amount, transaction.currency || "USD")}
                </td>
                <td className="py-1.5 text-right whitespace-nowrap">
                  {pendingDeleteId === transaction.id ? (
                    <div className="inline-flex items-center gap-1">
                      <Button
                        size="sm"
                        variant="destructive"
                        className="h-7 text-[11px]"
                        disabled={deleteMutation.isPending}
                        onClick={() => {
                          deleteMutation.mutate(transaction.id, {
                            onSuccess: () => {
                              setPendingDeleteId(null)
                              toast.success(t("transactions.toast.deleted"))
                            },
                            onError: (err: unknown) => {
                              toast.error(getErrorMessage(err) || t("common.error"))
                            },
                          })
                        }}
                      >
                        {t("common.confirm")}
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-7 text-[11px]"
                        onClick={() => setPendingDeleteId(null)}
                      >
                        {t("common.cancel")}
                      </Button>
                    </div>
                  ) : (
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-7 text-[11px] text-destructive"
                      onClick={() => setPendingDeleteId(transaction.id)}
                    >
                      {t("transactions.table.delete")}
                    </Button>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
