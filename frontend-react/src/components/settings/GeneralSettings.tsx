import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { Switch } from "@/components/ui/switch"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useLanguage } from "@/hooks/useLanguage"
import { usePrivacyMode } from "@/hooks/usePrivacyMode"
import { useTheme } from "@/hooks/useTheme"
import { useDefaultCurrency } from "@/hooks/useDefaultCurrency"
import { usePreferences, useSavePreferences, useUpdateProfile } from "@/api/hooks/useAllocation"
import { useProfile } from "@/api/hooks/useDashboard"
import { getErrorMessage } from "@/lib/utils"
import { DISPLAY_CURRENCIES } from "@/lib/constants"

interface SettingRowProps {
  label: string
  hint: string
  children: React.ReactNode
}

function SettingRow({ label, hint, children }: SettingRowProps) {
  return (
    <div className="flex items-start justify-between gap-4 py-4 border-b border-border last:border-0">
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium">{label}</p>
        <p className="text-xs text-muted-foreground mt-0.5">{hint}</p>
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  )
}

export function GeneralSettings() {
  const { t } = useTranslation()
  const { language, changeLanguage, LANGUAGE_OPTIONS } = useLanguage()
  const { isPrivate, toggle } = usePrivacyMode()
  const { theme, setTheme } = useTheme()
  const { defaultDisplayCurrency, setDefaultDisplayCurrency } = useDefaultCurrency()
  const { data: prefs } = usePreferences()
  const { data: profile } = useProfile()
  const saveMutation = useSavePreferences()
  const updateProfileMutation = useUpdateProfile()

  const saveField = (patch: Record<string, unknown>) => {
    saveMutation.mutate(
      { privacy_mode: isPrivate, ...patch },
      {
        onSuccess: () => toast.success(t("common.success")),
        onError: (err: unknown) => toast.error(getErrorMessage(err) || t("common.error")),
      },
    )
  }

  const handlePrivacyToggle = () => {
    const next = !isPrivate
    toggle()
    saveField({ privacy_mode: next })
  }

  const handleDisplayCurrencyChange = (value: string) => {
    setDefaultDisplayCurrency(value)
    saveField({ default_display_currency: value })
  }

  const handleHomeCurrencyChange = (value: string) => {
    if (!profile) return
    updateProfileMutation.mutate(
      { id: profile.id, payload: { home_currency: value } },
      {
        onSuccess: () => toast.success(t("common.success")),
        onError: (err: unknown) => toast.error(getErrorMessage(err) || t("common.error")),
      },
    )
  }

  const handleTerminologyChange = (value: string) => {
    saveField({ terminology_mode: value })
  }

  return (
    <div className="space-y-6">
      {/* Language & Region */}
      <section>
        <p className="text-xs uppercase tracking-wide text-muted-foreground mb-1">
          {t("settings.section_language")}
        </p>
        <div className="rounded-md border border-border px-4">
          <SettingRow label={t("settings.language_label")} hint={t("settings.language_hint")}>
            <Select value={language} onValueChange={changeLanguage}>
              <SelectTrigger className="w-44 min-h-[44px] text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(LANGUAGE_OPTIONS).map(([code, label]) => (
                  <SelectItem key={code} value={code} className="text-xs">
                    {label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </SettingRow>
        </div>
      </section>

      {/* Appearance */}
      <section>
        <p className="text-xs uppercase tracking-wide text-muted-foreground mb-1">
          {t("settings.section_appearance")}
        </p>
        <div className="rounded-md border border-border px-4">
          <SettingRow label={t("settings.theme_label")} hint={t("settings.theme_hint")}>
            <div className="flex rounded-md border border-border overflow-hidden">
              <button
                onClick={() => setTheme("light")}
                className={`px-3 py-1.5 text-xs min-h-[36px] transition-colors ${
                  theme === "light"
                    ? "bg-primary text-primary-foreground"
                    : "bg-background hover:bg-muted"
                }`}
              >
                {t("settings.theme_light")}
              </button>
              <button
                onClick={() => setTheme("dark")}
                className={`px-3 py-1.5 text-xs min-h-[36px] border-l border-border transition-colors ${
                  theme === "dark"
                    ? "bg-primary text-primary-foreground"
                    : "bg-background hover:bg-muted"
                }`}
              >
                {t("settings.theme_dark")}
              </button>
            </div>
          </SettingRow>
        </div>
      </section>

      {/* Privacy */}
      <section>
        <p className="text-xs uppercase tracking-wide text-muted-foreground mb-1">
          {t("settings.section_privacy")}
        </p>
        <div className="rounded-md border border-border px-4">
          <SettingRow label={t("settings.privacy_label")} hint={t("settings.privacy_hint")}>
            <div className="min-h-[44px] inline-flex items-center justify-center">
              <Switch checked={isPrivate} onCheckedChange={handlePrivacyToggle} />
            </div>
          </SettingRow>
          <SettingRow
            label={t("settings.terminology_label")}
            hint={t("settings.terminology_hint")}
          >
            <Select
              value={prefs?.terminology_mode ?? "simplified"}
              onValueChange={handleTerminologyChange}
              disabled={saveMutation.isPending}
            >
              <SelectTrigger className="w-44 min-h-[44px] text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="simplified" className="text-xs">
                  {t("terminology_settings.mode_simplified")}
                </SelectItem>
                <SelectItem value="expert" className="text-xs">
                  {t("terminology_settings.mode_expert")}
                </SelectItem>
              </SelectContent>
            </Select>
          </SettingRow>
        </div>
      </section>

      {/* Currency */}
      <section>
        <p className="text-xs uppercase tracking-wide text-muted-foreground mb-1">
          {t("settings.section_currency")}
        </p>
        <div className="rounded-md border border-border px-4">
          <SettingRow
            label={t("settings.default_currency_label")}
            hint={t("settings.default_currency_hint")}
          >
            <Select
              value={prefs?.default_display_currency ?? defaultDisplayCurrency}
              onValueChange={handleDisplayCurrencyChange}
              disabled={saveMutation.isPending}
            >
              <SelectTrigger className="w-32 min-h-[44px] text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {DISPLAY_CURRENCIES.map((c) => (
                  <SelectItem key={c} value={c} className="text-xs">
                    {c}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </SettingRow>
          <SettingRow
            label={t("settings.home_currency_label")}
            hint={t("settings.home_currency_hint")}
          >
            <Select
              value={profile?.home_currency ?? "TWD"}
              onValueChange={handleHomeCurrencyChange}
              disabled={updateProfileMutation.isPending || !profile}
            >
              <SelectTrigger className="w-32 min-h-[44px] text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {DISPLAY_CURRENCIES.map((c) => (
                  <SelectItem key={c} value={c} className="text-xs">
                    {c}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </SettingRow>
        </div>
      </section>
    </div>
  )
}
