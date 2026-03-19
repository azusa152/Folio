import { useMemo, useState } from "react"
import { CircleAlert, CircleCheck, Info, Target } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { FINANCE_TEXT } from "@/lib/colors"

export interface InsightItem {
  key: string
  severity: string
  vars?: Record<string, unknown>
  category: string
}

interface Props {
  insights: InsightItem[]
  maxVisible?: number
  isLoading?: boolean
}

function iconForSeverity(severity: string) {
  if (severity === "positive") return CircleCheck
  if (severity === "warning") return CircleAlert
  if (severity === "action") return Target
  return Info
}

function classForSeverity(severity: string) {
  if (severity === "positive") return FINANCE_TEXT.gain
  if (severity === "warning") return FINANCE_TEXT.warning
  if (severity === "action") return FINANCE_TEXT.loss
  return "text-sky-600 dark:text-sky-400"
}

export function InsightCard({ insights, maxVisible = 3, isLoading = false }: Props) {
  const { t } = useTranslation()
  const [expanded, setExpanded] = useState(false)

  const visibleInsights = useMemo(
    () => (expanded ? insights : insights.slice(0, maxVisible)),
    [expanded, insights, maxVisible],
  )

  if (isLoading && !insights.length) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">{t("insight.title")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-11/12" />
          <Skeleton className="h-4 w-10/12" />
        </CardContent>
      </Card>
    )
  }

  if (!insights.length) return null

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">{t("insight.title")}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {visibleInsights.map((insight, idx) => {
          const Icon = iconForSeverity(insight.severity)
          return (
            <div key={`${insight.key}-${idx}`} className="flex items-start gap-2 text-xs">
              <Icon
                aria-hidden="true"
                className={`h-4 w-4 mt-[1px] shrink-0 ${classForSeverity(insight.severity)}`}
              />
              <p className="text-muted-foreground">
                {t(insight.key, (insight.vars ?? {}) as Record<string, string | number>)}
              </p>
            </div>
          )
        })}
        {insights.length > maxVisible ? (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-7 px-1 text-[11px]"
            onClick={() => setExpanded((v) => !v)}
          >
            {expanded ? t("insight.show_less") : t("insight.show_more")}
          </Button>
        ) : null}
      </CardContent>
    </Card>
  )
}
