import { useQuery } from "@tanstack/react-query"
import { useTranslation } from "react-i18next"
import type { components } from "@/api/types/generated"

type HealthResponse = components["schemas"]["HealthResponse"]

function useDemoMode(): boolean {
  const { data } = useQuery<HealthResponse>({
    queryKey: ["health"],
    queryFn: async () => {
      const res = await fetch("/api/health")
      if (!res.ok) return { status: "error", service: "unknown", demo_mode: false }
      return res.json() as Promise<HealthResponse>
    },
    staleTime: Infinity,
    retry: false,
  })
  return data?.demo_mode === true
}

export function DemoBanner() {
  const { t } = useTranslation()
  const isDemoMode = useDemoMode()
  if (!isDemoMode) return null

  return (
    <div
      role="status"
      aria-live="polite"
      className="border-b border-blue-500/40 bg-blue-500/10 px-4 py-2 text-xs text-blue-700 dark:text-blue-300 flex items-center gap-2"
    >
      <span className="font-semibold">🎭</span>
      <span>{t("common.demo_banner")}</span>
    </div>
  )
}
