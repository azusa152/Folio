import { useTranslation } from "react-i18next"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export function NisaEducationCard() {
  const { t } = useTranslation()

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">{t("nisa.education.title")}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-sm text-muted-foreground">
        <p>{t("nisa.education.summary")}</p>
        <ul className="list-disc pl-5 space-y-1">
          <li>{t("nisa.education.tsumitate_limit")}</li>
          <li>{t("nisa.education.growth_limit")}</li>
          <li>{t("nisa.education.combined_annual_limit")}</li>
          <li>{t("nisa.education.combined_lifetime_limit")}</li>
        </ul>
      </CardContent>
    </Card>
  )
}
