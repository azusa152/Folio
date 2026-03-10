export type AnalyticsTimeframe = 30 | 90 | 180 | 365 | 0

export const ANALYTICS_TIMEFRAMES: Array<{ value: AnalyticsTimeframe; key: string }> = [
  { value: 30, key: "1m" },
  { value: 90, key: "3m" },
  { value: 180, key: "6m" },
  { value: 365, key: "1y" },
  { value: 0, key: "max" },
]
