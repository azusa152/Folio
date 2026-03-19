import { useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useWrapperContributions } from "@/api/hooks/useWrappers"

type WrapperFilter = "all" | "nisa_tsumitate" | "nisa_growth"

function entryTypeLabel(type: string, t: (key: string) => string): string {
  if (type === "CONTRIBUTION") return t("nisa.contributions.entry_type.contribution")
  if (type === "RESTORATION") return t("nisa.contributions.entry_type.restoration")
  if (type === "ADJUSTMENT") return t("nisa.contributions.entry_type.adjustment")
  return type
}

export function ContributionsTab() {
  const { t, i18n } = useTranslation()
  const [wrapper, setWrapper] = useState<WrapperFilter>("all")
  const [year, setYear] = useState<number>(new Date().getFullYear())

  const query = useWrapperContributions({
    wrapper: wrapper === "all" ? undefined : wrapper,
    year,
    limit: 500,
  })

  const summary = useMemo(() => {
    const items = query.data?.items ?? []
    const byWrapper: Record<
      string,
      { netLedgerAmount: number; contributionAmount: number }
    > = {
      nisa_tsumitate: { netLedgerAmount: 0, contributionAmount: 0 },
      nisa_growth: { netLedgerAmount: 0, contributionAmount: 0 },
    }
    for (const item of items) {
      const current = byWrapper[item.tax_wrapper] ?? {
        netLedgerAmount: 0,
        contributionAmount: 0,
      }
      current.netLedgerAmount += item.amount
      if (item.entry_type === "CONTRIBUTION") {
        current.contributionAmount += item.amount
      }
      byWrapper[item.tax_wrapper] = current
    }
    return byWrapper
  }, [query.data?.items])

  const formatDateOnly = (dateOnly: string): string => {
    const [yearPart, monthPart, dayPart] = dateOnly.split("-")
    const year = Number(yearPart)
    const month = Number(monthPart)
    const day = Number(dayPart)
    if (!Number.isFinite(year) || !Number.isFinite(month) || !Number.isFinite(day)) {
      return dateOnly
    }
    return new Date(year, month - 1, day).toLocaleDateString(i18n.language)
  }

  return (
    <div className="space-y-4">
      <div className="space-y-1">
        <h2 className="text-base font-semibold">{t("nisa.contributions.title")}</h2>
        <p className="text-sm text-muted-foreground">{t("nisa.contributions.hint")}</p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <label htmlFor="nisa-wrapper-filter" className="text-xs text-muted-foreground">
          {t("nisa.contributions.filter_wrapper")}
        </label>
        <select
          id="nisa-wrapper-filter"
          value={wrapper}
          onChange={(event) => setWrapper(event.target.value as WrapperFilter)}
          className="text-xs border border-border rounded px-2 py-2 min-h-[36px] bg-background"
        >
          <option value="all">{t("nisa.contributions.filter_all_wrappers")}</option>
          <option value="nisa_tsumitate">{t("wrapper.nisa_tsumitate")}</option>
          <option value="nisa_growth">{t("wrapper.nisa_growth")}</option>
        </select>

        <label htmlFor="nisa-year-filter" className="text-xs text-muted-foreground ml-2">
          {t("nisa.contributions.filter_year")}
        </label>
        <input
          id="nisa-year-filter"
          type="number"
          min={2000}
          max={2100}
          value={year}
          onChange={(event) => setYear(Number(event.target.value) || new Date().getFullYear())}
          className="text-xs border border-border rounded px-2 py-2 min-h-[36px] w-24 bg-background"
        />
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">{t("wrapper.nisa_tsumitate")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            <p className="text-xs text-muted-foreground">
              {t("nisa.contributions.summary_net_ledger_label")}
            </p>
            <p className="text-xl font-semibold">
              {Math.round(summary.nisa_tsumitate?.netLedgerAmount ?? 0).toLocaleString()}
            </p>
            <p className="text-xs text-muted-foreground">
              {t("nisa.contributions.summary_contribution_only_label", {
                amount: Math.round(
                  summary.nisa_tsumitate?.contributionAmount ?? 0,
                ).toLocaleString(),
              })}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">{t("wrapper.nisa_growth")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1">
            <p className="text-xs text-muted-foreground">
              {t("nisa.contributions.summary_net_ledger_label")}
            </p>
            <p className="text-xl font-semibold">
              {Math.round(summary.nisa_growth?.netLedgerAmount ?? 0).toLocaleString()}
            </p>
            <p className="text-xs text-muted-foreground">
              {t("nisa.contributions.summary_contribution_only_label", {
                amount: Math.round(
                  summary.nisa_growth?.contributionAmount ?? 0,
                ).toLocaleString(),
              })}
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="rounded-md border border-border overflow-x-auto">
        <table className="w-full min-w-[760px] text-sm">
          <thead className="bg-muted/40">
            <tr className="text-left">
              <th className="px-3 py-2 font-medium">{t("nisa.contributions.table_date")}</th>
              <th className="px-3 py-2 font-medium">{t("nisa.contributions.table_wrapper")}</th>
              <th className="px-3 py-2 font-medium">{t("nisa.contributions.table_type")}</th>
              <th className="px-3 py-2 font-medium">{t("nisa.contributions.table_amount")}</th>
              <th className="px-3 py-2 font-medium">{t("nisa.contributions.table_note")}</th>
            </tr>
          </thead>
          <tbody>
            {query.isLoading ? (
              Array.from({ length: 8 }).map((_, index) => (
                <tr key={`contrib-skeleton-${index}`} className="border-t border-border">
                  <td className="px-3 py-2" colSpan={5}>
                    <Skeleton className="h-4 w-full" />
                  </td>
                </tr>
              ))
            ) : query.isError ? (
              <tr className="border-t border-border">
                <td className="px-3 py-6" colSpan={5}>
                  <div className="space-y-2">
                    <p className="text-sm font-medium">{t("nisa.contributions.error_title")}</p>
                    <p className="text-sm text-muted-foreground">
                      {t("nisa.contributions.error_hint")}
                    </p>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        void query.refetch()
                      }}
                    >
                      {t("nisa.contributions.retry")}
                    </Button>
                  </div>
                </td>
              </tr>
            ) : query.data?.items.length ? (
              query.data.items.map((item) => (
                <tr key={item.id} className="border-t border-border">
                  <td className="px-3 py-2">
                    {formatDateOnly(item.effective_date)}
                  </td>
                  <td className="px-3 py-2">
                    <Badge variant="outline">{t(`wrapper.${item.tax_wrapper}`)}</Badge>
                  </td>
                  <td className="px-3 py-2">{entryTypeLabel(item.entry_type, t)}</td>
                  <td className="px-3 py-2">
                    {Math.round(item.amount).toLocaleString()}
                  </td>
                  <td className="px-3 py-2 text-muted-foreground">{item.note || "—"}</td>
                </tr>
              ))
            ) : (
              <tr className="border-t border-border">
                <td className="px-3 py-6 text-sm text-muted-foreground" colSpan={5}>
                  {t("nisa.contributions.empty")}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
