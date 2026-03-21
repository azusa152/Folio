import { useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { Lightbulb, ShieldCheck, Sparkles } from "lucide-react"
import { useTranslation } from "react-i18next"
import { useAccounts } from "@/api/hooks/useAccounts"
import { useDeTaxSuggestions, useSuggestRouting } from "@/api/hooks/useWrappers"
import { getPreferredWrapperAccountMap } from "@/lib/wrapperAccounts"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"

interface SmartActionCardsProps {
  enabled?: boolean
  onApplyRouting?: (ticker: string, accountId: number, currency: string) => void
  onReviewDetax?: (accountId: number, currency: string) => void
  forceHideActions?: boolean
  emptyHintKey?: string
}

export function SmartActionCards({
  enabled = true,
  onApplyRouting,
  onReviewDetax,
  forceHideActions = false,
  emptyHintKey,
}: SmartActionCardsProps) {
  const { t } = useTranslation()
  const queryEnabled = enabled && !forceHideActions
  const { data: accounts } = useAccounts(queryEnabled)
  const [ticker, setTicker] = useState("")
  const [amount, setAmount] = useState("")
  const [whyOpen, setWhyOpen] = useState(false)
  const amountNumber = Number(amount)

  const routingQuery = useSuggestRouting(
    ticker,
    Number.isFinite(amountNumber) ? amountNumber : null,
    queryEnabled,
  )
  const detaxQuery = useDeTaxSuggestions(queryEnabled)

  const accountByWrapper = useMemo(() => getPreferredWrapperAccountMap(accounts), [accounts])
  const accountById = useMemo(() => {
    const map = new Map<number, string>()
    for (const account of accounts ?? []) {
      if (account.id == null) continue
      map.set(account.id, (account.currency || "USD").toUpperCase())
    }
    return map
  }, [accounts])

  const totalDetaxSavings = detaxQuery.data?.total_estimated_savings ?? 0
  const hasDetax = totalDetaxSavings > 0
  const routingSuggestions = routingQuery.data?.suggestions ?? []
  const routingTotal = routingSuggestions.reduce((sum, item) => sum + item.amount, 0)
  const segmentClassByWrapper: Record<string, string> = {
    nisa_growth: "bg-emerald-500",
    nisa_tsumitate: "bg-green-500",
    ideco: "bg-blue-500",
    tokutei: "bg-slate-500",
    ippan: "bg-zinc-500",
  }

  if (forceHideActions) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col items-center justify-center gap-3 px-4 py-3 text-center">
            <div className="rounded-full bg-muted p-3">
              <ShieldCheck className="h-5 w-5 text-muted-foreground" />
            </div>
            <div className="space-y-1">
              <p className="text-sm font-semibold">{t("nisa.actions.empty_title")}</p>
              <p className="text-xs text-muted-foreground">
                {t(emptyHintKey ?? "nisa.actions.empty")}
              </p>
            </div>
            <Button asChild size="sm">
              <Link to="/allocation?tab=accounts">{t("nisa.actions.empty_cta")}</Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base flex items-center gap-2">
            <Lightbulb className="h-4 w-4" />
            {t("routing.suggest_title")}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 gap-2">
            <Input
              value={ticker}
              onChange={(event) => setTicker(event.target.value.toUpperCase())}
              className="text-xs"
              placeholder={t("smart_actions.ticker_placeholder")}
              aria-label={t("transactions.form.ticker")}
            />
            <Input
              value={amount}
              type="number"
              min={0}
              onChange={(event) => setAmount(event.target.value)}
              className="text-xs"
              placeholder={t("smart_actions.amount_placeholder")}
              aria-label={t("transactions.form.total_amount")}
            />
          </div>
          {routingSuggestions.length ? (
            <div className="space-y-2">
              <div className="h-2 w-full overflow-hidden rounded-full bg-muted flex">
                {routingSuggestions.map((item, index) => {
                  const widthPct = routingTotal > 0 ? (item.amount / routingTotal) * 100 : 0
                  return (
                    <div
                      key={`${item.wrapper}-segment-${index}`}
                      className={segmentClassByWrapper[item.wrapper] ?? "bg-primary"}
                      style={{ width: `${Math.max(widthPct, 0)}%` }}
                    />
                  )
                })}
              </div>
              <button
                type="button"
                className="text-[11px] text-primary hover:underline"
                onClick={() => setWhyOpen((value) => !value)}
              >
                {t("smart_actions.why_toggle")}
              </button>
              {routingSuggestions.map((item, index) => {
                const suggestionAccount =
                  item.account_id != null
                    ? {
                        id: item.account_id,
                        currency: accountById.get(item.account_id) ?? "JPY",
                      }
                    : accountByWrapper.get(item.wrapper)
                return (
                  <div
                    key={`${item.wrapper}-${index}`}
                    className="rounded-md border border-border bg-muted/20 p-2 space-y-1"
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-medium">
                        {t(`wrapper.${item.wrapper}`, { defaultValue: item.wrapper })}
                      </span>
                      <span>{Math.round(item.amount).toLocaleString()}</span>
                    </div>
                    {whyOpen ? (
                      <p className="text-[11px] text-muted-foreground">
                        {t(item.reason, { defaultValue: item.reason })}
                      </p>
                    ) : null}
                    {suggestionAccount && onApplyRouting ? (
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-7 text-[11px]"
                        onClick={() =>
                          onApplyRouting(
                            ticker.trim().toUpperCase(),
                            suggestionAccount.id,
                            suggestionAccount.currency,
                          )
                        }
                      >
                        {t("smart_actions.apply_suggestion")}
                      </Button>
                    ) : null}
                  </div>
                )
              })}
            </div>
          ) : null}
        </CardContent>
      </Card>

      {hasDetax ? (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <Sparkles className="h-4 w-4" />
              {t("detax.title")}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-xs text-muted-foreground">
              {t("detax.estimated_saving", {
                amount: Math.round(totalDetaxSavings).toLocaleString(),
              })}
            </p>
            {detaxQuery.data?.opportunities.map((item) => (
              <div
                key={`${item.account_id}-${item.ticker}`}
                className="rounded-md border border-border p-2"
              >
                <p className="text-xs font-medium">{item.ticker}</p>
                <p className="text-[11px] text-muted-foreground">
                  {t(item.reason, { defaultValue: item.reason })}
                </p>
                {onReviewDetax ? (
                  <Button
                    size="sm"
                    variant="outline"
                    className="mt-1 h-7 text-[11px]"
                    onClick={() =>
                      onReviewDetax(item.account_id, accountById.get(item.account_id) ?? "USD")
                    }
                  >
                    {t("smart_actions.review_button")}
                  </Button>
                ) : null}
              </div>
            ))}
            <p className="text-[11px] text-muted-foreground">{t("detax.disclaimer")}</p>
          </CardContent>
        </Card>
      ) : null}
    </div>
  )
}
