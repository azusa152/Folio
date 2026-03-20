import { Minus, TrendingDown, TrendingUp } from "lucide-react"
import type { FxAnalysis } from "@/api/types/fxWatch"

export function trendIcon(direction: FxAnalysis["trend_direction"]) {
  if (direction === "rising") return <TrendingUp className="h-3.5 w-3.5" />
  if (direction === "falling") return <TrendingDown className="h-3.5 w-3.5" />
  return <Minus className="h-3.5 w-3.5" />
}
