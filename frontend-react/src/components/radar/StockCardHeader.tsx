import { memo } from "react"
import { ChevronDown } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { Skeleton } from "@/components/ui/skeleton"
import { SparklineHeader } from "@/components/radar/SparklineHeader"
import { cn } from "@/lib/utils"
import {
  SCAN_SIGNAL_ICONS,
  CATEGORY_ICON_SHORT,
  BUY_OPPORTUNITY_SIGNALS,
  RISK_WARNING_SIGNALS,
} from "@/lib/constants"
import { formatPrice } from "@/lib/format"
import { getSignalDescription, getSignalLabel } from "@/lib/signal-label"
import { FINANCE_BADGE, FINANCE_TEXT } from "@/lib/colors"
import type { PricePoint } from "@/api/hooks/useRadar"
import type { StockCategory } from "@/api/types/radar"

interface Props {
  ticker: string
  category: StockCategory
  signal: string
  price?: number | null
  changePct?: number | null
  changeAbs: number | null
  currency: { symbol: string; code: string }
  marketOpen: boolean
  isCrypto: boolean
  expanded: boolean
  priceHistory?: PricePoint[]
  onToggle: () => void
}

export const StockCardHeader = memo(function StockCardHeader({
  ticker,
  category,
  signal,
  price,
  changePct,
  changeAbs,
  currency,
  marketOpen,
  isCrypto,
  expanded,
  priceHistory,
  onToggle,
}: Props) {
  const { t } = useTranslation()

  const signalIcon = SCAN_SIGNAL_ICONS[signal] ?? "➖"
  const catIcon = CATEGORY_ICON_SHORT[category] ?? ""
  const signalLabel = signal !== "NORMAL" ? getSignalLabel(t, signal) : ""
  const signalDescription = signal !== "NORMAL" ? getSignalDescription(t, signal) : ""
  const signalBadgeClass = BUY_OPPORTUNITY_SIGNALS.has(signal)
    ? `shrink-0 text-[10px] rounded px-1.5 py-0.5 ${FINANCE_BADGE.gain}`
    : RISK_WARNING_SIGNALS.has(signal)
      ? `shrink-0 text-[10px] rounded px-1.5 py-0.5 ${FINANCE_BADGE.loss}`
      : "shrink-0 text-[10px] bg-muted text-muted-foreground rounded px-1.5 py-0.5"

  const isUp = changePct != null ? changePct >= 0 : null
  const changeColor = isUp === null ? "" : isUp ? FINANCE_TEXT.gain : FINANCE_TEXT.loss

  return (
    <button
      className="w-full text-left p-3 font-medium text-sm hover:bg-muted/30 transition-colors rounded-t-lg"
      onClick={onToggle}
      aria-expanded={expanded}
    >
      <span className="flex items-center justify-between gap-2">
        {/* Left: ticker + category icon + signal badge */}
        <span className="flex-1 min-w-0 flex items-center gap-1.5 text-sm">
          <span className="truncate">{signalIcon} {ticker}</span>
          <span className="shrink-0 text-muted-foreground">{catIcon}</span>
          {signalLabel && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <span
                    className={signalBadgeClass}
                    aria-label={signalDescription}
                    role="status"
                  >
                    {signalLabel}
                  </span>
                </TooltipTrigger>
                <TooltipContent sideOffset={6}>{signalDescription}</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </span>

        {/* Right: price + sparkline + market dot + chevron */}
        <span className="flex items-center gap-2 shrink-0">
          {price != null && (
            <span className="flex flex-col items-end leading-tight">
              <span className="text-sm font-semibold tabular-nums">
                {currency.symbol}{formatPrice(price, currency.code)}
              </span>
              {changePct != null && (
                <span className={`text-xs tabular-nums font-medium ${changeColor}`}>
                  {isUp ? "▲" : "▼"}{" "}
                  {changeAbs != null ? `${currency.symbol}${formatPrice(Math.abs(changeAbs), currency.code)} ` : ""}
                  ({Math.abs(changePct).toFixed(2)}%{isCrypto ? ` ${t("allocation.crypto.change_24h_short")}` : ""})
                </span>
              )}
            </span>
          )}
          {!expanded && (
            priceHistory && priceHistory.length >= 5
              ? <SparklineHeader data={priceHistory} />
              : <Skeleton className="h-8 w-20 shrink-0" />
          )}
          <span className={`text-[10px] ${marketOpen ? FINANCE_TEXT.gain : "text-muted-foreground"}`}>
            {marketOpen ? "●" : "○"}
          </span>
          <ChevronDown className={cn("h-3.5 w-3.5 text-muted-foreground transition-transform duration-200", expanded && "rotate-180")} />
        </span>
      </span>
    </button>
  )
})
