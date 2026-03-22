import { FINANCE_TEXT } from "@/lib/colors"

export { FINANCE_TEXT }

export const FEAR_GREED_BANDS = [
  {
    range: [0, 25] as [number, number],
    color: "#dc2626",
    labelKey: "config.fear_greed.extreme_fear",
    emoji: "😱",
  },
  {
    range: [25, 45] as [number, number],
    color: "#f97316",
    labelKey: "config.fear_greed.fear",
    emoji: "😨",
  },
  {
    range: [45, 55] as [number, number],
    color: "#eab308",
    labelKey: "config.fear_greed.neutral",
    emoji: "😐",
  },
  {
    range: [55, 75] as [number, number],
    color: "#86efac",
    labelKey: "config.fear_greed.greed",
    emoji: "🤑",
  },
  {
    range: [75, 100] as [number, number],
    color: "#16a34a",
    labelKey: "config.fear_greed.extreme_greed",
    emoji: "🤯",
  },
]

export function stripLeadingEmoji(label: string): string {
  return label.replace(/^(?:\p{Extended_Pictographic}|\uFE0F|\u200D)+\s*/u, "").trim()
}

export function scoreToColor(score: number): string {
  if (!Number.isFinite(score)) return FEAR_GREED_BANDS[FEAR_GREED_BANDS.length - 1].color
  const clamped = Math.max(0, Math.min(100, score))
  for (const band of FEAR_GREED_BANDS) {
    if (clamped >= band.range[0] && clamped <= band.range[1]) return band.color
  }
  return FEAR_GREED_BANDS[FEAR_GREED_BANDS.length - 1].color
}
