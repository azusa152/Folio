import { useTranslation } from "react-i18next"
import type { TransactionType, FieldErrors } from "@/hooks/useAddTransactionForm"

interface Props {
  transactionType: TransactionType
  currency: string
  setTransactionType: (t: TransactionType) => void
  setSellPickerOpen: (o: boolean) => void
  setSellPickerSearch: (s: string) => void
  setInsufficientBalance: (v: { available: number; required: number } | null) => void
  setFieldErrors: (updater: (prev: FieldErrors) => FieldErrors) => void
  applyCashMovementDefaults: (currency: string) => void
}

const TRANSACTION_TYPES: TransactionType[] = ["BUY", "SELL", "DIVIDEND", "DEPOSIT", "WITHDRAWAL"]

export function TransactionTypePicker({
  transactionType,
  currency,
  setTransactionType,
  setSellPickerOpen,
  setSellPickerSearch,
  setInsufficientBalance,
  setFieldErrors,
  applyCashMovementDefaults,
}: Props) {
  const { t } = useTranslation()

  return (
    <div className="space-y-1">
      <p className="text-xs font-medium">{t("transactions.form.type")}</p>
      <div className="grid grid-cols-2 gap-1">
        {TRANSACTION_TYPES.map((type) => (
          <button
            key={type}
            type="button"
            onClick={() => {
              setTransactionType(type)
              setSellPickerOpen(false)
              setSellPickerSearch("")
              setInsufficientBalance(null)
              setFieldErrors(() => ({}))
              if (type === "DEPOSIT" || type === "WITHDRAWAL") {
                applyCashMovementDefaults(currency)
              }
            }}
            className={`text-xs py-1.5 rounded border transition-colors ${
              transactionType === type
                ? "bg-primary text-primary-foreground border-primary"
                : "border-border hover:bg-muted/30"
            }`}
          >
            {t(`transactions.type.${type.toLowerCase()}`)}
          </button>
        ))}
      </div>
    </div>
  )
}
