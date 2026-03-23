import { useTranslation } from "react-i18next"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { CATEGORY_COLOR_FALLBACK, CATEGORY_COLOR_MAP, TAX_WRAPPER_COLOR_MAP } from "@/lib/constants"

interface WrapperAllocationItem {
  wrapper: string
  categories: Record<string, number>
  total: number
}

interface PlacementSuggestionItem {
  ticker: string
  category: string
  from_wrapper: string
  to_wrapper: string
  amount: number
  reason: string
}

interface TaxSavingsEstimateItem {
  annual_nisa_benefit: number
  annual_detax_benefit: number
  annual_ideco_deduction: number
  total_annual: number
  projected_10yr: number
  projected_20yr: number
}

interface AssetLocationVizProps {
  taxEfficiencyScore?: number | null
  wrapperAllocations?: WrapperAllocationItem[] | null
  placementSuggestions?: PlacementSuggestionItem[] | null
  taxSavingsEstimate?: TaxSavingsEstimateItem | null
  onExecuteSuggestion?: (ticker: string, targetWrapper: string) => void
}

function scoreVariant(score: number): "default" | "secondary" | "destructive" {
  if (score >= 80) return "default"
  if (score >= 50) return "secondary"
  return "destructive"
}

export function AssetLocationViz({
  taxEfficiencyScore,
  wrapperAllocations,
  placementSuggestions,
  taxSavingsEstimate,
  onExecuteSuggestion,
}: AssetLocationVizProps) {
  const { t } = useTranslation()
  const allocations = wrapperAllocations ?? []
  if (!allocations.length) return null

  const score = taxEfficiencyScore ?? 0
  const scoreMessage =
    score >= 80
      ? t("location.score_optimal")
      : score >= 50
        ? t("location.score_good")
        : t("location.score_needs_work")

  return (
    <section className="space-y-4">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">{t("location.title")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">{t("location.efficiency_score")}</span>
            <Badge variant={scoreVariant(score)}>{Math.round(score)}</Badge>
          </div>
          <p className="text-xs text-muted-foreground">{scoreMessage}</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">{t("location.title")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {allocations.map((allocation) => (
            <div key={allocation.wrapper} className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span>
                  {t(`wrapper.${allocation.wrapper}`, { defaultValue: allocation.wrapper })}
                </span>
                <span>{Math.round(allocation.total).toLocaleString()}</span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-muted flex">
                {Object.entries(allocation.categories).map(([category, amount]) => {
                  const widthPct = allocation.total > 0 ? (amount / allocation.total) * 100 : 0
                  const bgColor =
                    CATEGORY_COLOR_MAP[category] ??
                    TAX_WRAPPER_COLOR_MAP[allocation.wrapper] ??
                    CATEGORY_COLOR_FALLBACK
                  return (
                    <div
                      key={`${allocation.wrapper}-${category}`}
                      style={{ width: `${Math.max(widthPct, 0)}%`, backgroundColor: bgColor }}
                      title={`${category}: ${Math.round(amount).toLocaleString()}`}
                    />
                  )
                })}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {!!placementSuggestions?.length && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">{t("routing.suggest_title")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {placementSuggestions.map((suggestion) => (
              <div
                key={`${suggestion.ticker}-${suggestion.from_wrapper}-${suggestion.to_wrapper}`}
                className="rounded-md border border-border p-2 space-y-1"
              >
                <p className="text-xs font-medium">
                  {t(suggestion.reason, {
                    amount: Math.round(suggestion.amount).toLocaleString(),
                    category: suggestion.category,
                    from: t(`wrapper.${suggestion.from_wrapper}`, {
                      defaultValue: suggestion.from_wrapper,
                    }),
                    to: t(`wrapper.${suggestion.to_wrapper}`, {
                      defaultValue: suggestion.to_wrapper,
                    }),
                    defaultValue: `${suggestion.ticker}`,
                  })}
                </p>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-7 text-[11px]"
                  disabled={!onExecuteSuggestion}
                  onClick={() => onExecuteSuggestion?.(suggestion.ticker, suggestion.to_wrapper)}
                >
                  {t("smart_actions.review_button")}
                </Button>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {taxSavingsEstimate && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">{t("location.tax_savings")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-xs text-muted-foreground">
            <p>
              {t("location.tax_savings")}:{" "}
              {Math.round(taxSavingsEstimate.total_annual).toLocaleString()}
            </p>
            <p>
              {t("location.projected_10yr")}:{" "}
              {Math.round(taxSavingsEstimate.projected_10yr).toLocaleString()}
            </p>
            <p>
              {t("location.projected_20yr")}:{" "}
              {Math.round(taxSavingsEstimate.projected_20yr).toLocaleString()}
            </p>
          </CardContent>
        </Card>
      )}
    </section>
  )
}
