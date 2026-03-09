import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Info, TrendingUp, AlertTriangle, Zap } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"
import type { InsightItem } from "@/api/hooks/useAnalytics"

interface Props {
  insights: InsightItem[]
  maxVisible?: number
  isLoading?: boolean
}

const SEVERITY_CONFIG: Record<string, {
  icon: typeof Info
  color: string
  bg: string
}> = {
  info: {
    icon: Info,
    color: "text-blue-500",
    bg: "bg-blue-50 dark:bg-blue-950/30",
  },
  positive: {
    icon: TrendingUp,
    color: "text-green-500",
    bg: "bg-green-50 dark:bg-green-950/30",
  },
  warning: {
    icon: AlertTriangle,
    color: "text-amber-500",
    bg: "bg-amber-50 dark:bg-amber-950/30",
  },
  action: {
    icon: Zap,
    color: "text-red-500",
    bg: "bg-red-50 dark:bg-red-950/30",
  },
}

export function InsightCard({ insights, maxVisible = 3, isLoading }: Props) {
  const { t } = useTranslation()
  const [expanded, setExpanded] = useState(false)

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-4 sm:p-6 space-y-3">
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </CardContent>
      </Card>
    )
  }

  if (!insights.length) return null

  const visible = expanded ? insights : insights.slice(0, maxVisible)
  const hasMore = insights.length > maxVisible

  return (
    <Card>
      <CardContent className="p-4 sm:p-6 space-y-3">
        <h3 className="text-sm font-semibold text-muted-foreground">
          {t("insight.title")}
        </h3>
        <div className="space-y-2">
          {visible.map((item, idx) => {
            const config = SEVERITY_CONFIG[item.severity] ?? SEVERITY_CONFIG.info
            const Icon = config.icon
            return (
              <div
                key={`${item.key}-${item.vars.category ?? item.category}-${idx}`}
                className={cn(
                  "flex items-start gap-2.5 rounded-md px-3 py-2 text-sm",
                  config.bg,
                )}
              >
                <Icon className={cn("mt-0.5 h-4 w-4 shrink-0", config.color)} />
                <span>{t(item.key, item.vars)}</span>
              </div>
            )
          })}
        </div>
        {hasMore && (
          <Button
            variant="ghost"
            size="sm"
            className="text-xs px-0 h-auto"
            onClick={() => setExpanded((prev) => !prev)}
          >
            {expanded ? t("insight.show_less") : t("insight.show_more")}
          </Button>
        )}
      </CardContent>
    </Card>
  )
}
