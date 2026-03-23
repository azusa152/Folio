import { useTranslation } from "react-i18next"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  ACCOUNT_TYPES,
  isTaxWrapperType,
  TAX_WRAPPER_ICONS,
  TAX_WRAPPER_TYPES,
  type TaxWrapperType,
} from "@/lib/constants"

interface Props {
  editingId: number | null
  name: string
  broker: string
  accountType: (typeof ACCOUNT_TYPES)[number]
  taxWrapper: TaxWrapperType | null
  currency: string
  market: string
  institution: string
  note: string
  isSaving: boolean
  onNameChange: (v: string) => void
  onBrokerChange: (v: string) => void
  onAccountTypeChange: (v: (typeof ACCOUNT_TYPES)[number]) => void
  onTaxWrapperChange: (v: TaxWrapperType | null) => void
  onCurrencyChange: (v: string) => void
  onMarketChange: (v: string) => void
  onInstitutionChange: (v: string) => void
  onNoteChange: (v: string) => void
  onSubmit: () => void
  onCancel: () => void
}

export function AccountFormPanel({
  editingId,
  name,
  broker,
  accountType,
  taxWrapper,
  currency,
  market,
  institution,
  note,
  isSaving,
  onNameChange,
  onBrokerChange,
  onAccountTypeChange,
  onTaxWrapperChange,
  onCurrencyChange,
  onMarketChange,
  onInstitutionChange,
  onNoteChange,
  onSubmit,
  onCancel,
}: Props) {
  const { t } = useTranslation()

  return (
    <div className="rounded-md border border-border p-3 space-y-3">
      <p className="text-xs font-semibold">
        {editingId == null ? t("accounts.form.create_title") : t("accounts.form.edit_title")}
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        <Input
          aria-label={t("accounts.form.name")}
          value={name}
          onChange={(e) => onNameChange(e.target.value)}
          placeholder={t("accounts.form.name")}
          className="text-xs"
        />
        <Input
          aria-label={t("accounts.form.broker")}
          value={broker}
          onChange={(e) => onBrokerChange(e.target.value)}
          placeholder={t("accounts.form.broker")}
          className="text-xs"
        />
        <select
          aria-label={t("accounts.form.account_type")}
          value={accountType}
          onChange={(e) => onAccountTypeChange(e.target.value as (typeof ACCOUNT_TYPES)[number])}
          className="w-full text-xs border border-border rounded px-2 py-1.5 bg-background"
        >
          {ACCOUNT_TYPES.map((v) => (
            <option key={v} value={v}>
              {t(`config.account_type.${v}`)}
            </option>
          ))}
        </select>
        <select
          aria-label={t("wrapper.select_wrapper")}
          value={taxWrapper ?? ""}
          onChange={(e) => {
            const v = e.target.value
            onTaxWrapperChange(isTaxWrapperType(v) ? v : null)
          }}
          className="w-full text-xs border border-border rounded px-2 py-1.5 bg-background"
        >
          <option value="">{t("wrapper.no_wrapper")}</option>
          {TAX_WRAPPER_TYPES.map((v) => (
            <option key={v} value={v}>
              {TAX_WRAPPER_ICONS[v]} {t(`wrapper.${v}`)}
            </option>
          ))}
        </select>
        <Input
          aria-label={t("accounts.form.currency")}
          value={currency}
          onChange={(e) => onCurrencyChange(e.target.value.toUpperCase())}
          placeholder={t("accounts.form.currency")}
          className="text-xs"
        />
        <Input
          aria-label={t("accounts.form.market")}
          value={market}
          onChange={(e) => onMarketChange(e.target.value.toUpperCase())}
          placeholder={t("accounts.form.market")}
          className="text-xs"
        />
        <Input
          aria-label={t("accounts.form.institution")}
          value={institution}
          onChange={(e) => onInstitutionChange(e.target.value)}
          placeholder={t("accounts.form.institution")}
          className="text-xs sm:col-span-2"
        />
        <Input
          aria-label={t("accounts.form.note")}
          value={note}
          onChange={(e) => onNoteChange(e.target.value)}
          placeholder={t("accounts.form.note")}
          className="text-xs sm:col-span-2"
        />
      </div>
      <div className="flex items-center gap-2">
        <Button size="sm" onClick={onSubmit} disabled={isSaving}>
          {t("accounts.form.save")}
        </Button>
        <Button size="sm" variant="outline" onClick={onCancel}>
          {t("common.cancel")}
        </Button>
      </div>
    </div>
  )
}
