import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { usePreferences, useSavePreferences } from "@/api/hooks/useAllocation"
import { useIsPrivate } from "@/hooks/usePrivacyMode"
import { getErrorMessage } from "@/lib/utils"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

export function TerminologySettings() {
  const { t } = useTranslation()
  const { data: prefs } = usePreferences()
  const saveMutation = useSavePreferences()
  const isPrivate = useIsPrivate()

  const handleChange = (value: string) => {
    saveMutation.mutate(
      {
        privacy_mode: isPrivate,
        terminology_mode: value as "simplified" | "expert",
      },
      {
        onSuccess: () => toast.success(t("common.success")),
        onError: (err: unknown) => toast.error(getErrorMessage(err) || t("common.error")),
      },
    )
  }

  return (
    <div className="space-y-3">
      <Select
        value={prefs?.terminology_mode ?? "simplified"}
        onValueChange={handleChange}
        disabled={saveMutation.isPending}
      >
        <SelectTrigger className="w-full min-h-[44px] text-xs">
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
      <p className="text-xs text-muted-foreground">
        {t("terminology_settings.terminology_hint")}
      </p>
    </div>
  )
}
