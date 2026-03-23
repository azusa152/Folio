import { useTranslation } from "react-i18next"
import { formatLocalTime } from "@/lib/utils"
import { GlossaryTerm } from "@/components/GlossaryTerm"
import type { FxWatch } from "@/api/types/fxWatch"

interface Props {
  watch: FxWatch
  targetDirectionLabel: string | null
}

export function WatchCardInsights({ watch, targetDirectionLabel }: Props) {
  const { t } = useTranslation()

  return (
    <div className="space-y-0.5 text-muted-foreground">
      <p className="font-medium text-foreground">{t("fx_watch.settings.title")}</p>
      <p>{t("fx_watch.settings.recent_high", { days: watch.recent_high_days })}</p>
      <p>{t("fx_watch.settings.consecutive", { days: watch.consecutive_increase_days })}</p>
      <p>
        <GlossaryTerm termKey="reminder_interval">
          {t("fx_watch.settings.interval", { hours: watch.reminder_interval_hours })}
        </GlossaryTerm>
      </p>
      <p>
        {watch.target_rate && watch.target_direction
          ? t("fx_watch.settings.target", {
              direction: targetDirectionLabel,
              rate: watch.target_rate.toFixed(4),
            })
          : t("fx_watch.settings.target_none")}
      </p>
      <p>{t("fx_watch.settings.high_alert", { icon: watch.alert_on_recent_high ? "✅" : "❌" })}</p>
      <p>
        {t("fx_watch.settings.consec_alert", {
          icon: watch.alert_on_consecutive_increase ? "✅" : "❌",
        })}
      </p>
      {watch.last_alerted_at ? (
        <p>
          {t("fx_watch.settings.last_alert_time", {
            time: formatLocalTime(watch.last_alerted_at),
          })}
        </p>
      ) : (
        <p>{t("fx_watch.settings.last_alert_none")}</p>
      )}
    </div>
  )
}
