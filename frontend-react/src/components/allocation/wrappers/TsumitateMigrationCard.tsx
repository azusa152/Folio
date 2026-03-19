import { useTranslation } from "react-i18next"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface TsumitateMigration {
  monthly_amount: number
  source_wrapper: string
  eligible_tickers: string[]
  reason: string
}

interface TsumitateMigrationCardProps {
  migration?: TsumitateMigration | null
  onSetup?: (tickers: string[]) => void
}

export function TsumitateMigrationCard({ migration, onSetup }: TsumitateMigrationCardProps) {
  const { t } = useTranslation()
  if (!migration) return null

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">{t("location.tsumitate_migration")}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <p className="text-xs font-medium">
          {t(migration.reason, {
            amount: Math.round(migration.monthly_amount).toLocaleString(),
            source: t(`wrapper.${migration.source_wrapper}`, { defaultValue: migration.source_wrapper }),
            defaultValue: t("location.tsumitate_migration"),
          })}
        </p>
        <p className="text-xs text-muted-foreground">
          {migration.eligible_tickers.join(", ")}
        </p>
        <Button
          size="sm"
          variant="outline"
          className="h-7 text-[11px]"
          disabled={!onSetup}
          onClick={() => onSetup?.(migration.eligible_tickers)}
        >
          {t("location.setup_monthly_migration")}
        </Button>
      </CardContent>
    </Card>
  )
}
