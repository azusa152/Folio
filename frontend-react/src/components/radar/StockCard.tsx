import { useCallback, useEffect, useMemo, useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import { SKIP_PRICE_CATEGORIES, SKIP_MOAT_CATEGORIES } from "@/lib/constants"
import { isMarketOpen } from "@/lib/format"
import { inferMarket, inferMarketLabel, inferCurrency } from "@/lib/market"
import { usePriceHistory, useMoatAnalysis } from "@/api/hooks/useRadar"
import type { RadarStock, RadarEnrichedStock, ResonanceMap } from "@/api/types/radar"
import { StockCardHeader } from "@/components/radar/StockCardHeader"
import { StockCardInsights } from "@/components/radar/StockCardInsights"
import { StockCardActions } from "@/components/radar/StockCardActions"

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
  const fundName = enrichment?.fund_name

  const currency = useMemo(() => inferCurrency(stock.ticker, stock.category), [stock.ticker, stock.category])
  const marketLabel = inferMarketLabel(stock.ticker, stock.category)
  const handleToggle = useCallback(() => setExpanded((v) => !v), [])
  const marketKey = inferMarket(stock.ticker, stock.category)
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
        fundName={fundName}
        expanded={expanded}
        priceHistory={priceHistory}
        onToggle={handleToggle}
      />

      {expanded && (
        <CardContent className="pt-0 pb-3 px-3 space-y-4">
          <StockCardInsights
            stock={stock}
            enrichment={enrichment}
            signal={signal}
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
