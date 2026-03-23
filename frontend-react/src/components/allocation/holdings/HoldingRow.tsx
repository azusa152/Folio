import { useTranslation } from "react-i18next"
import { FINANCE_TEXT } from "@/lib/colors"
import { formatQuantity, formatSignedMoneyWithPrivacy, getQuantityUnitKey } from "@/lib/format"
import { maskMoney } from "@/hooks/usePrivacyMode"
import { getDisplayName } from "@/lib/stock-display"
import type { GroupedHolding } from "./HoldingsTableUtils"
import { computeFxReturn, fmtPct, formatAccountList, getValueClass } from "./HoldingsTableUtils"

interface HoldingRowProps {
  holding: GroupedHolding
  privacyMode: boolean
  displayCurrency?: string
}

export function HoldingRow({ holding: h, privacyMode, displayCurrency }: HoldingRowProps) {
  const { t } = useTranslation()

  const isCrypto = h.category === "Crypto"
  const isCash = h.category === "Cash"
  const targetCurrency = displayCurrency ?? h.currency
  const currentFxRate = h.current_fx_rate
  const fxReturn = computeFxReturn(h.purchase_fx_rate, h.current_fx_rate)
  const showFxBreakdown =
    !isCash && h.purchase_fx_rate != null && fxReturn != null && h.currency !== targetCurrency

  const showCashFxInfo =
    isCash &&
    currentFxRate != null &&
    Number.isFinite(currentFxRate) &&
    h.currency !== targetCurrency

  // Home return = local price return + FX impact (approximate additive)
  const homeReturn = showFxBreakdown && h.change_pct != null ? h.change_pct + fxReturn : null
  const quantityUnit = getQuantityUnitKey(h.category, h.ticker)
  const quantityText = t(quantityUnit.key, {
    quantity: formatQuantity(h.quantity, { category: h.category, ticker: h.ticker }),
    ...quantityUnit.params,
  })
  const accountDisplay = formatAccountList(h.accounts)
  const displayName = getDisplayName(h.name)

  return (
    <tr key={h.row_key} className="border-b border-border/50">
      <td className="py-0.5 pr-2">
        {displayName ? (
          <div className="flex flex-col leading-tight">
            <span className="font-medium truncate max-w-[160px]" title={displayName}>
              {displayName}
            </span>
            <span className="text-[10px] text-muted-foreground">{h.ticker}</span>
          </div>
        ) : (
          <span className="font-medium">{h.ticker}</span>
        )}
      </td>
      <td className="py-0.5 pr-2 text-muted-foreground">
        {h.accounts.length > 1 ? (
          <span className="text-[10px] leading-tight" title={accountDisplay.fullLabel}>
            {accountDisplay.shortLabel}
          </span>
        ) : (
          (h.account_name ?? "—")
        )}
      </td>
      <td className="py-0.5 pr-2 text-muted-foreground">
        {t(`config.category.${h.category.toLowerCase()}`)}
      </td>
      <td className="py-0.5 pr-2 text-right">{privacyMode ? "***" : quantityText}</td>
      <td className="py-0.5 pr-2 text-right">
        {h.market_value == null ? "—" : maskMoney(h.market_value, displayCurrency ?? h.currency)}
      </td>
      <td className="py-0.5 pr-2 text-right">
        {h.weight_pct != null ? `${h.weight_pct.toFixed(1)}%` : "—"}
      </td>
      <td className="py-0.5 pr-2 text-right">
        {h.cost_total == null ? "—" : maskMoney(h.cost_total, displayCurrency ?? h.currency)}
      </td>
      <td className="py-0.5 pr-2 text-right">
        {!isCash && (h.change_value != null || h.change_pct != null) ? (
          <>
            <div className={`font-medium ${getValueClass(h.change_value ?? h.change_pct)}`}>
              {formatSignedMoneyWithPrivacy(
                h.change_value,
                displayCurrency ?? h.currency,
                privacyMode,
              )}
            </div>
            <div className={getValueClass(h.change_pct)}>
              {h.change_pct != null
                ? `${fmtPct(h.change_pct)}${isCrypto ? ` (${t("allocation.crypto.change_24h_short")})` : ""}`
                : "—"}
            </div>
          </>
        ) : (
          <div className={FINANCE_TEXT.neutral}>—</div>
        )}
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
      <td className="py-0.5 text-right">
        {h.total_gain_value != null || h.total_gain_pct != null ? (
          <>
            <div className={`font-medium ${getValueClass(h.total_gain_value)}`}>
              {formatSignedMoneyWithPrivacy(
                h.total_gain_value,
                displayCurrency ?? h.currency,
                privacyMode,
              )}
            </div>
            <div className={getValueClass(h.total_gain_pct)}>
              {h.total_gain_pct != null ? fmtPct(h.total_gain_pct) : "—"}
            </div>
          </>
        ) : (
          "—"
        )}
      </td>
    </tr>
  )
}
