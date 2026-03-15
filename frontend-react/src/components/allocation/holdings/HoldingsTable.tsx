import { useTranslation } from "react-i18next"
import { Info } from "lucide-react"
import { useTerminology } from "@/hooks/useTerminology"
import type { HoldingDetail } from "@/api/types/allocation"
import { FINANCE_TEXT } from "@/lib/colors"
import { formatQuantity, getQuantityUnitKey } from "@/lib/format"
import { maskMoney } from "@/hooks/usePrivacyMode"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

interface Props {
  holdings: HoldingDetail[]
  privacyMode: boolean
  displayCurrency?: string
}

function fmtPct(v: number, showSign = true): string {
  const sign = showSign && v >= 0 ? "+" : ""
  return `${sign}${v.toFixed(2)}%`
}

/** Compute FX return % given purchase and current FX rate */
function computeFxReturn(purchaseFx: number | null | undefined, currentFx: number | null | undefined): number | null {
  if (purchaseFx == null || currentFx == null || purchaseFx === 0) return null
  return (currentFx / purchaseFx - 1) * 100
}

export function HoldingsTable({ holdings, privacyMode, displayCurrency }: Props) {
  const { t } = useTranslation()
  const { term } = useTerminology()

  if (!holdings || holdings.length === 0) {
    return <p className="text-sm text-muted-foreground">{t("allocation.holdings.empty")}</p>
  }

  return (
    <div className="space-y-1">
      <p className="text-sm font-semibold">{t("allocation.holdings.title")}</p>
      <div className="text-xs text-muted-foreground bg-muted/50 rounded px-3 py-2 mb-2">
        {t("allocation.holdings_read_only_hint")}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-muted-foreground border-b border-border">
              <th className="text-left py-0.5 pr-2">{t("allocation.col.ticker")}</th>
              <th className="text-left py-0.5 pr-2">{t("allocation.col.account")}</th>
              <th className="text-left py-0.5 pr-2">{t("allocation.col.category")}</th>
              <th className="text-right py-0.5 pr-2">{t("allocation.col.qty")}</th>
              <th className="text-right py-0.5 pr-2">{t("allocation.col.value")}</th>
              <th className="text-right py-0.5 pr-2">{t("allocation.col.weight_pct")}</th>
              <th className="text-right py-0.5 pr-2">
                <div className="inline-flex items-center justify-end gap-1">
                  <span>{term("cost_basis", t("allocation.col.cost"))}</span>
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Info
                          className="h-3 w-3 cursor-help text-muted-foreground"
                          aria-label={t("allocation.col.cost_tooltip")}
                        />
                      </TooltipTrigger>
                      <TooltipContent>
                        <p className="max-w-[220px]">{t("allocation.col.cost_tooltip")}</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>
              </th>
              <th className="text-right py-0.5">{t("allocation.col.change_pct")}</th>
            </tr>
          </thead>
          <tbody>
            {holdings.map((h, i) => {
              const isCrypto = h.category === "Crypto"
              const isCash = h.category === "Cash"
              const targetCurrency = displayCurrency ?? h.currency
              const currentFxRate = h.current_fx_rate
              const fxReturn = computeFxReturn(h.purchase_fx_rate, h.current_fx_rate)
              const showFxBreakdown =
                !isCash &&
                h.purchase_fx_rate != null &&
                fxReturn != null &&
                h.currency !== targetCurrency

              const showCashFxInfo =
                isCash &&
                currentFxRate != null &&
                Number.isFinite(currentFxRate) &&
                h.currency !== targetCurrency

              // Home return = local price return + FX impact (approximate additive)
              const homeReturn =
                showFxBreakdown && h.change_pct != null
                  ? h.change_pct + fxReturn
                  : null
              const quantityUnit = getQuantityUnitKey(h.category, h.ticker)
              const quantityText = t(quantityUnit.key, {
                quantity: formatQuantity(h.quantity, { category: h.category, ticker: h.ticker }),
                ...quantityUnit.params,
              })

              return (
                <tr key={`${h.ticker}-${i}`} className="border-b border-border/50">
                  <td className="py-0.5 pr-2 font-medium">{h.ticker}</td>
                  <td className="py-0.5 pr-2 text-muted-foreground">{h.account_name ?? "—"}</td>
                  <td className="py-0.5 pr-2 text-muted-foreground">
                    {t(`config.category.${h.category.toLowerCase()}`)}
                  </td>
                  <td className="py-0.5 pr-2 text-right">
                    {privacyMode
                      ? "***"
                      : quantityText}
                  </td>
                  <td className="py-0.5 pr-2 text-right">
                    {h.market_value == null ? "—" : maskMoney(h.market_value, displayCurrency ?? h.currency)}
                  </td>
                  <td className="py-0.5 pr-2 text-right">
                    {h.weight_pct != null ? `${h.weight_pct.toFixed(1)}%` : "—"}
                  </td>
                  <td className="py-0.5 pr-2 text-right">
                    {h.cost_total == null ? "—" : maskMoney(h.cost_total, displayCurrency ?? h.currency)}
                  </td>
                  <td className="py-0.5 text-right">
                    <div
                      className={
                        !isCash && h.change_pct != null
                          ? (h.change_pct >= 0 ? FINANCE_TEXT.gain : FINANCE_TEXT.loss)
                          : undefined
                      }
                    >
                      {!isCash && h.change_pct != null
                        ? `${fmtPct(h.change_pct)}${isCrypto ? ` (${t("allocation.crypto.change_24h_short")})` : ""}`
                        : "—"}
                    </div>
                    {isCrypto && h.change_pct != null && Math.abs(h.change_pct) >= 5 && (
                      <div className={`text-[10px] leading-tight mt-0.5 ${FINANCE_TEXT.warning}`}>
                        {t("allocation.crypto.volatility_warning")}
                      </div>
                    )}
                    {showCashFxInfo && (
                      <div className="text-muted-foreground text-[10px] leading-tight mt-0.5">
                        {t("allocation.col.fx_rate_info", {
                          from: h.currency,
                          rate: currentFxRate.toLocaleString(undefined, {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 6,
                          }),
                          to: targetCurrency,
                        })}
                      </div>
                    )}
                    {showFxBreakdown && (
                      <div className="text-muted-foreground text-[10px] leading-tight mt-0.5">
                        {homeReturn != null && (
                          <div className={homeReturn >= 0 ? FINANCE_TEXT.gain : FINANCE_TEXT.loss}>
                            {t("allocation.col.home_return", { pct: fmtPct(homeReturn) })}
                          </div>
                        )}
                        <div className={fxReturn >= 0 ? FINANCE_TEXT.gain : FINANCE_TEXT.loss}>
                          {t("allocation.col.fx_return", { pct: fmtPct(fxReturn) })}
                        </div>
                      </div>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
