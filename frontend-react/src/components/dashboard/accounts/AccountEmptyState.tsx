import { useTranslation } from "react-i18next"
import { Link } from "react-router-dom"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"

interface Props {
  isLoading: boolean
  isError: boolean
  hasRows: boolean
}

export function AccountEmptyState({ isLoading, isError, hasRows }: Props) {
  const { t } = useTranslation()

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <Skeleton className="h-5 w-40" />
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-3 w-full" />
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
        </CardContent>
      </Card>
    )
  }

  if (isError && !hasRows) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">{t("dashboard.accounts_overview.title")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <p className="text-sm font-semibold">{t("dashboard.accounts_overview.error_title")}</p>
          <p className="text-sm text-muted-foreground">{t("dashboard.accounts_overview.error_description")}</p>
        </CardContent>
      </Card>
    )
  }

  if (!hasRows) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">{t("dashboard.accounts_overview.title")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm font-semibold">{t("dashboard.accounts_overview.empty_title")}</p>
          <p className="text-sm text-muted-foreground">{t("dashboard.accounts_overview.empty_description")}</p>
          <Button asChild size="sm" variant="outline" className="min-h-[36px]">
            <Link to="/allocation?tab=accounts">{t("dashboard.accounts_overview.empty_cta")}</Link>
          </Button>
        </CardContent>
      </Card>
    )
  }

  return null
}
