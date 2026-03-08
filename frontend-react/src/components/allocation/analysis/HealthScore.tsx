import { useTranslation } from "react-i18next"
import { formatLocalTime } from "@/lib/utils"
import { FINANCE_TEXT } from "@/lib/colors"

interface Props {
  score: number
  level: string
  calculatedAt: string
}

function scoreColor(level: string): string {
  if (level === "healthy") return FINANCE_TEXT.gain
  if (level === "caution") return FINANCE_TEXT.warning
  return FINANCE_TEXT.loss
}

export function HealthScore({ score, level, calculatedAt }: Props) {
  const { t } = useTranslation()
  const ts = calculatedAt ? formatLocalTime(calculatedAt) : null

  return (
    <div className="flex items-center gap-4">
      <div>
        <p className="text-xs text-muted-foreground">{t("allocation.health.title")}</p>
        <div className="flex items-baseline gap-2">
          <span className={`text-3xl font-bold ${scoreColor(level)}`}>{score}</span>
          <span className={`text-sm font-medium ${scoreColor(level)}`}>{t(`allocation.health.level_${level}`, { defaultValue: level })}</span>
        </div>
      </div>
      {ts && (
        <p className="text-xs text-muted-foreground ml-auto">
          {t("allocation.health.calculated_at")} {ts}
        </p>
      )}
    </div>
  )
}
