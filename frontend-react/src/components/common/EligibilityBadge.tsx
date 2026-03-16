import { CheckCircle2, Loader2, XCircle } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Badge } from "@/components/ui/badge"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import type { EligibilityCheckResponse } from "@/api/types/wrapper"

interface Props {
  result?: EligibilityCheckResponse
  loading?: boolean
}

export function EligibilityBadge({ result, loading = false }: Props) {
  const { t } = useTranslation()

  if (loading) {
    return (
      <Badge variant="outline" className="gap-1 text-[11px]">
        <Loader2 className="h-3 w-3 animate-spin" />
        {t("eligibility.checking")}
      </Badge>
    )
  }

  if (!result) return null

  if (result.eligible) {
    return (
      <Badge variant="outline" className="gap-1 border-emerald-500/40 text-emerald-700 dark:text-emerald-300 text-[11px]">
        <CheckCircle2 className="h-3 w-3" />
        {t("eligibility.eligible")}
      </Badge>
    )
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge
            variant="outline"
            className="gap-1 border-destructive/40 text-destructive text-[11px]"
          >
            <XCircle className="h-3 w-3" />
            {t("eligibility.not_eligible")}
          </Badge>
        </TooltipTrigger>
        <TooltipContent className="max-w-[280px]">
          <div className="space-y-1">
            {result.reasons.map((reason) => (
              <p key={reason}>{t(reason, { defaultValue: reason })}</p>
            ))}
            {result.suggested_wrapper ? (
              <p>
                {t("eligibility.try_instead", {
                  wrapper: t(`wrapper.${result.suggested_wrapper}`, {
                    defaultValue: result.suggested_wrapper,
                  }),
                })}
              </p>
            ) : null}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
