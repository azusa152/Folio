import { useTranslation } from "react-i18next"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { usePrivacyMode, maskMoney } from "@/hooks/usePrivacyMode"
import { useTerminology } from "@/hooks/useTerminology"
import { GlossaryTerm } from "@/components/GlossaryTerm"
import { InfoPopover } from "./InfoPopover"
import { getSignalLabel } from "@/lib/signal-label"
import { FINANCE_TEXT } from "@/lib/colors"
import { FearGreedGauge, FearGreedComponentBars, SparklineMini } from "./FearGreedIndicators"
import { FEAR_GREED_BANDS, stripLeadingEmoji } from "./fearGreedUtils"
import type {
  RebalanceResponse,
  FearGreedResponse,
  TwrResponse,
  Snapshot,
  LastScanResponse,
  Stock,
  EnrichedStock,
} from "@/api/types/dashboard"

const LEGACY_SENTIMENT_MAP: Record<string, string> = {
  positive: "bullish",
  caution: "bearish",
}

const GLOSSARY_KEYS = {
  twr: "twr",
  fearGreed: "fear_greed",
  marketSentiment: "market_sentiment",
  healthScore: "health_score",
} as const

function computeHealthScore(
  stocks: Stock[],
  enrichedSignalMap: Record<string, string>,
): { pct: number; normal: number; total: number } {
  const active = stocks.filter((s) => s.is_active)
  const total = active.length
  if (total === 0) return { pct: 0, normal: 0, total: 0 }
  const normal = active.filter((s) => {
    const signal = enrichedSignalMap[s.ticker] ?? s.last_scan_signal ?? "NORMAL"
    return signal === "NORMAL"
  }).length
  return { pct: (normal / total) * 100, normal, total }
}

function healthScoreColor(pct: number): string {
  if (pct >= 80) return FINANCE_TEXT.gain
  if (pct >= 50) return FINANCE_TEXT.warning
  return FINANCE_TEXT.loss
}

interface Props {
  rebalance?: RebalanceResponse | null
  fearGreed?: FearGreedResponse | null
  twr?: TwrResponse | null
  snapshots?: Snapshot[]
  lastScan?: LastScanResponse | null
  stocks?: Stock[]
  enrichedStocks?: EnrichedStock[]
  holdings?: { id: number }[]
  isLoading: boolean
  isRefreshing?: boolean
  /** True while the rebalance query has no data yet (initial load). */
  isRebalanceLoading?: boolean
  /** True while rebalance is background-refreshing — drives the "Updating…" badge on Total Market Value. */
  isValueRefreshing?: boolean
}

export function PortfolioPulse({
  rebalance,
  fearGreed,
  twr,
  snapshots = [],
  lastScan,
  stocks = [],
  enrichedStocks = [],
  holdings = [],
  isLoading,
  isRefreshing = false,
  isRebalanceLoading = false,
  isValueRefreshing = false,
}: Props) {
  const { t } = useTranslation()
  const isPrivate = usePrivacyMode((s) => s.isPrivate)
  const { term } = useTerminology()

  if (isLoading) {
    return (
      <Card>
        <CardContent className="grid grid-cols-1 gap-4 p-6 sm:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="space-y-3">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-8 w-40" />
              <Skeleton className="h-4 w-32" />
            </div>
          ))}
        </CardContent>
      </Card>
    )
  }

  const enrichedSignalMap: Record<string, string> = {}
  for (const es of enrichedStocks) {
    if (es.ticker) {
      enrichedSignalMap[es.ticker] = es.computed_signal ?? es.last_scan_signal ?? "NORMAL"
    }
  }

  const {
    pct: healthPct,
    normal: normalCnt,
    total: totalCnt,
  } = computeHealthScore(stocks, enrichedSignalMap)

  const stockCount = stocks.filter((s) => s.is_active).length
  const holdingCount = holdings.length

  const marketStatus = lastScan?.market_status
  const rawKey = marketStatus?.toLowerCase() ?? ""
  const sentimentKey = LEGACY_SENTIMENT_MAP[rawKey] ?? rawKey
  const sentimentLabel = !marketStatus
    ? t("config.sentiment.not_scanned")
    : t(`config.sentiment.${sentimentKey}`, { defaultValue: marketStatus })

  const displayCurrency = rebalance?.display_currency ?? "USD"
  const totalVal = rebalance?.total_value
  const changePct = rebalance?.total_value_change_pct
  const changeAmt = rebalance?.total_value_change
  const ytdTwr = twr?.twr_pct

  // Staleness: true when showing last-known data while fresh data computes in the background.
  const isValueStale = rebalance?.source === "snapshot"
  // When there is no data yet and the query is still in flight, show a skeleton.
  const isLoadingValue = totalVal == null && isRebalanceLoading

  // "As of" label: prefer snapshot_at (daily date) when available, else calculated_at.
  const asOfDisplay = (() => {
    const raw = rebalance?.snapshot_at ?? rebalance?.calculated_at
    if (!raw) return null
    try {
      const d = new Date(raw)
      // snapshot_at is a date string ("YYYY-MM-DD"); calculated_at is a full ISO datetime.
      const isDateOnly = /^\d{4}-\d{2}-\d{2}$/.test(raw)
      return isDateOnly
        ? d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })
        : d.toLocaleString(undefined, {
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
          })
    } catch {
      return null
    }
  })()

  const fgScore = fearGreed?.composite_score ?? lastScan?.fear_greed_score ?? null
  const fgLevel = fearGreed?.composite_level ?? lastScan?.fear_greed_level ?? null
  const hasFearGreed = fgScore != null && fgLevel != null
  const vixVal = fearGreed?.vix?.value
  const vixChange = fearGreed?.vix?.change_1d
  const cnnScore = fearGreed?.cnn?.score

  const allNonNormalStocks = stocks
    .filter((s) => s.is_active)
    .flatMap((s) => {
      const signal = enrichedSignalMap[s.ticker] ?? s.last_scan_signal ?? "NORMAL"
      return signal !== "NORMAL" ? [{ ticker: s.ticker, signal }] : []
    })
  const NON_NORMAL_CAP = 10
  const nonNormalStocks = allNonNormalStocks.slice(0, NON_NORMAL_CAP)
  const nonNormalOverflow = allNonNormalStocks.length - nonNormalStocks.length

  const fearGreedTopBottom = (() => {
    const components = fearGreed?.components
    if (!components || components.length === 0) return null
    const scored = components.filter((c) => c.score != null) as Array<{
      name: string
      score: number
      weight: number
    }>
    if (scored.length === 0) return null
    const sorted = [...scored].sort((a, b) => b.score - a.score)
    const topName = sorted[0].name
    const bottomName = sorted[sorted.length - 1].name
    return {
      top: {
        label: t(`config.fear_greed.components.${topName}`, { defaultValue: topName }),
        score: sorted[0].score,
      },
      bottom: {
        label: t(`config.fear_greed.components.${bottomName}`, { defaultValue: bottomName }),
        score: sorted[sorted.length - 1].score,
      },
    }
  })()

  return (
    <Card>
      {isRefreshing && (
        <p className="px-6 pt-4 text-xs text-muted-foreground text-right">{t("common.loading")}</p>
      )}
      <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4 p-6">
        {/* Left: Total Portfolio Value — primary KPI, visually dominant */}
        <div className="space-y-1 md:col-span-1">
          <div className="flex items-center gap-2">
            <p className="text-xs text-muted-foreground">{t("dashboard.total_market_value")}</p>
            {(isValueStale || isValueRefreshing) && !isLoadingValue && (
              <span className="text-xs text-muted-foreground animate-pulse">
                {t("dashboard.updating")}
              </span>
            )}
          </div>
          {isLoadingValue ? (
            /* Skeleton while rebalance data is in flight (no value yet) */
            <div className="space-y-2 pt-1">
              <Skeleton className="h-10 w-44" />
              <Skeleton className="h-4 w-28" />
            </div>
          ) : totalVal != null ? (
            <>
              <p
                className={`text-4xl font-extrabold tabular-nums leading-tight${isValueStale ? " opacity-70" : ""}`}
              >
                {maskMoney(totalVal, displayCurrency)}
              </p>
              {isValueStale && asOfDisplay && (
                <p className="text-xs text-muted-foreground">
                  {t("dashboard.as_of", { datetime: asOfDisplay })}
                </p>
              )}
              <div className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
                {changePct != null && changeAmt != null && (
                  <span
                    className={`text-sm ${changePct >= 0 ? FINANCE_TEXT.gain : FINANCE_TEXT.loss}`}
                  >
                    {changePct >= 0 ? "▲" : "▼"}
                    {Math.abs(changePct).toFixed(2)}%
                    {!isPrivate && ` (${maskMoney(Math.abs(changeAmt), displayCurrency)})`}
                  </span>
                )}
                {ytdTwr != null && (
                  <span
                    className={`text-xs ${ytdTwr >= 0 ? FINANCE_TEXT.gain : FINANCE_TEXT.loss}`}
                  >
                    <GlossaryTerm termKey={GLOSSARY_KEYS.twr}>
                      {term("twr", t("dashboard.ytd_return"))}
                    </GlossaryTerm>{" "}
                    {ytdTwr >= 0 ? "▲" : "▼"}
                    {Math.abs(ytdTwr).toFixed(2)}%
                  </span>
                )}
              </div>
              {snapshots.length >= 2 && !isPrivate && <SparklineMini snapshots={snapshots} />}
            </>
          ) : (
            /* No value and not loading: rebalance failed or portfolio is empty */
            <p className="text-2xl font-bold text-muted-foreground">N/A</p>
          )}
        </div>

        {/* Center: Fear & Greed Gauge */}
        <div className="space-y-1">
          <div className="flex items-center justify-center gap-1">
            <p className="text-xs text-muted-foreground">
              <GlossaryTerm termKey={GLOSSARY_KEYS.fearGreed}>
                {t("dashboard.fear_greed_title")}
              </GlossaryTerm>
            </p>
            {fearGreed && (
              <InfoPopover align="center">
                <p className="text-xs font-medium">
                  {fearGreed.cnn?.score != null
                    ? t("dashboard.info.fear_greed_source_cnn")
                    : fearGreed.self_calculated_score != null
                      ? t("dashboard.info.fear_greed_source_self")
                      : t("dashboard.info.fear_greed_source_vix")}
                </p>
                {fearGreedTopBottom && (
                  <>
                    <p className="text-xs text-muted-foreground">
                      {t("dashboard.info.fear_greed_top", {
                        name: fearGreedTopBottom.top.label,
                        score: fearGreedTopBottom.top.score,
                      })}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {t("dashboard.info.fear_greed_bottom", {
                        name: fearGreedTopBottom.bottom.label,
                        score: fearGreedTopBottom.bottom.score,
                      })}
                    </p>
                  </>
                )}
              </InfoPopover>
            )}
          </div>
          {hasFearGreed ? (
            <>
              <p className="sr-only" aria-live="polite">
                {t("dashboard.fear_greed_title")}: {fgScore!}/100, {fgLevel!}
              </p>
              <FearGreedGauge score={fgScore!} level={fgLevel!} />
              <div className="mt-1.5 flex flex-wrap justify-center gap-x-3 gap-y-1">
                {FEAR_GREED_BANDS.map((band) => (
                  <span
                    key={band.labelKey}
                    className="inline-flex items-center gap-1.5 text-xs text-muted-foreground"
                  >
                    <span className="text-sm leading-none">{band.emoji}</span>
                    <span>{stripLeadingEmoji(t(band.labelKey))}</span>
                    <span
                      className="h-1 w-4 rounded-full"
                      style={{ backgroundColor: band.color }}
                    />
                  </span>
                ))}
              </div>
              <p className="text-xs text-muted-foreground text-center">
                {vixVal != null && (
                  <>
                    VIX={vixVal.toFixed(1)}
                    {vixChange != null &&
                      ` (${vixChange > 0 ? "▲" : "▼"}${Math.abs(vixChange).toFixed(1)})`}
                  </>
                )}
                {vixVal != null && " ｜ "}
                {cnnScore != null ? `CNN=${cnnScore}` : t("config.fear_greed.cnn_unavailable")}
              </p>
              {fearGreed?.components && fearGreed.components.length > 0 && (
                <FearGreedComponentBars components={fearGreed.components} />
              )}
            </>
          ) : (
            <p className="text-center text-muted-foreground text-sm">N/A</p>
          )}
        </div>

        {/* Right: Market Sentiment + Health Score + Tracking */}
        <div className="space-y-4">
          <div>
            <div className="flex items-center gap-1">
              <p className="text-xs text-muted-foreground">
                <GlossaryTerm termKey={GLOSSARY_KEYS.marketSentiment}>
                  {t("dashboard.market_sentiment")}
                </GlossaryTerm>
              </p>
              <InfoPopover align="end">
                {lastScan?.market_status_details ? (
                  <p className="text-xs">{lastScan.market_status_details}</p>
                ) : (
                  <p className="text-xs text-muted-foreground">
                    {t("dashboard.info.sentiment_no_details")}
                  </p>
                )}
                <p className="text-xs text-muted-foreground whitespace-pre-line">
                  {t("dashboard.info.sentiment_thresholds")}
                </p>
              </InfoPopover>
            </div>
            <p className="text-base font-semibold">{sentimentLabel}</p>
          </div>
          <div>
            <div className="flex items-center gap-1">
              <p className="text-xs text-muted-foreground">
                <GlossaryTerm termKey={GLOSSARY_KEYS.healthScore}>
                  {t("dashboard.health_score")}
                </GlossaryTerm>
              </p>
              <InfoPopover align="end">
                {nonNormalStocks.length > 0 ? (
                  <>
                    <p className="text-xs font-medium">{t("dashboard.info.health_non_normal")}</p>
                    <ul className="space-y-0.5">
                      {nonNormalStocks.map(({ ticker, signal }) => (
                        <li key={ticker} className="text-xs flex gap-1.5">
                          <span className="font-medium">{ticker}</span>
                          <span className="text-muted-foreground">{getSignalLabel(t, signal)}</span>
                        </li>
                      ))}
                    </ul>
                    {nonNormalOverflow > 0 && (
                      <p className="text-xs text-muted-foreground">
                        {t("dashboard.info.health_overflow", { count: nonNormalOverflow })}
                      </p>
                    )}
                  </>
                ) : (
                  <p className="text-xs">{t("dashboard.info.health_all_normal")}</p>
                )}
              </InfoPopover>
            </div>
            {totalCnt > 0 ? (
              <>
                <p className={`text-base font-semibold ${healthScoreColor(healthPct)}`}>
                  {healthPct.toFixed(0)}%
                </p>
                <p className="text-xs text-muted-foreground">
                  {t("dashboard.health_delta", { normal: normalCnt, total: totalCnt })}
                </p>
              </>
            ) : (
              <p className="text-base font-semibold text-muted-foreground">N/A</p>
            )}
          </div>
          <div>
            <p className="text-xs text-muted-foreground">{t("dashboard.kpi.tracking_holdings")}</p>
            <p className="text-sm font-medium">
              {t("dashboard.kpi.tracking_holdings_value", {
                stocks: stockCount,
                holdings: holdingCount,
              })}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
