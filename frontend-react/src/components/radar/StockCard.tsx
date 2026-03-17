import { useCallback, useEffect, useMemo, useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import { MARKET_OPTIONS, SKIP_PRICE_CATEGORIES, SKIP_MOAT_CATEGORIES } from "@/lib/constants"
import { isMarketOpen } from "@/lib/format"
import { usePriceHistory, useMoatAnalysis } from "@/api/hooks/useRadar"
import type { RadarStock, RadarEnrichedStock, ResonanceMap } from "@/api/types/radar"
import { StockCardHeader } from "@/components/radar/StockCardHeader"
import { StockCardInsights } from "@/components/radar/StockCardInsights"
import { StockCardActions } from "@/components/radar/StockCardActions"

function infer_market_label(ticker: string): string {
  if (ticker.endsWith(".TW")) return "🇹🇼 TW"
  if (ticker.endsWith(".T")) return "🇯🇵 JP"
  if (ticker.endsWith(".HK")) return "🇭🇰 HK"
  return "🇺🇸 US"
}

function infer_currency(ticker: string): { symbol: string; code: string } {
  if (ticker.endsWith(".TW")) return { symbol: "NT$", code: "TWD" }
  if (ticker.endsWith(".T")) return { symbol: "¥", code: "JPY" }
  if (ticker.endsWith(".HK")) return { symbol: "HK$", code: "HKD" }
  return { symbol: "$", code: "USD" }
}

interface Props {
  stock: RadarStock
  enrichment?: RadarEnrichedStock
  resonance?: ResonanceMap[string]
  isHeld?: boolean
  index?: number
}

export function StockCard({ stock, enrichment, resonance, isHeld = false, index = 0 }: Props) {
  const [expanded, setExpanded] = useState(false)
  const [sparklineEnabled, setSparklineEnabled] = useState(index === 0)

  useEffect(() => {
    if (sparklineEnabled || expanded) return

    const timer = window.setTimeout(() => {
      setSparklineEnabled(true)
    }, index * 200)

    return () => window.clearTimeout(timer)
  }, [expanded, index, sparklineEnabled])

  const skipPrice = SKIP_PRICE_CATEGORIES.has(stock.category)
  const skipMoat = SKIP_MOAT_CATEGORIES.has(stock.category)
  const { data: priceHistory, isLoading: priceLoading } = usePriceHistory(stock.ticker, (expanded || sparklineEnabled) && !skipPrice)
  const { data: moatData, isLoading: moatLoading } = useMoatAnalysis(stock.ticker, expanded && !skipMoat)
  const isCrypto = stock.category === "Crypto"
  const showMoatChart = !isCrypto && moatData != null && moatData.moat !== "N/A" && moatData.moat !== "NOT_AVAILABLE"

  const isMutualFund = stock.category === "Mutual_Fund"
  const signal = enrichment?.computed_signal ?? stock.last_scan_signal ?? "NORMAL"
  const sig = enrichment?.signals
  const price = sig?.price ?? enrichment?.price
  const prevClose = sig?.previous_close
  const changePct = sig?.change_pct ?? enrichment?.change_pct
  const changeAbs = price != null && prevClose != null ? price - prevClose : null
  const marketCap = enrichment?.market_cap ?? enrichment?.fundamentals?.market_cap
  const navDate = enrichment?.nav_date

  const currency = useMemo(() => infer_currency(stock.ticker), [stock.ticker])
  const marketLabel = infer_market_label(stock.ticker)
  const handleToggle = useCallback(() => setExpanded((v) => !v), [])
  const marketKey = MARKET_OPTIONS.find((m) => m.suffix && stock.ticker.endsWith(m.suffix))?.key ?? "US"
  const marketOpen = isMarketOpen(marketKey)

  return (
    <Card className={cn("border-border/70", isHeld && "border-l-[3px] border-l-primary")}>
      <StockCardHeader
        ticker={stock.ticker}
        category={stock.category}
        signal={signal}
        price={price}
        changePct={changePct}
        changeAbs={changeAbs}
        currency={currency}
        marketOpen={marketOpen}
        isCrypto={isCrypto}
        isMutualFund={isMutualFund}
        navDate={navDate}
        expanded={expanded}
        priceHistory={priceHistory}
        onToggle={handleToggle}
      />

      {expanded && (
        <CardContent className="pt-0 pb-3 px-3 space-y-4">
          <StockCardInsights
            stock={stock}
            enrichment={enrichment}
            resonance={resonance}
            isHeld={isHeld}
            isCrypto={isCrypto}
            isMutualFund={isMutualFund}
            currency={currency}
            marketLabel={marketLabel}
            marketCap={marketCap}
            priceHistory={priceHistory}
            priceLoading={priceLoading}
            moatData={moatData}
            moatLoading={moatLoading}
            showMoatChart={showMoatChart}
          />
          <StockCardActions stock={stock} />
        </CardContent>
      )}
    </Card>
  )
}
