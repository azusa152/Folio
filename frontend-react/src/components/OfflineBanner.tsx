import { useTranslation } from "react-i18next"
import { useOnlineStatus } from "@/hooks/useOnlineStatus"

export function OfflineBanner() {
  const { t } = useTranslation()
  const isOnline = useOnlineStatus()
  if (isOnline) return null

  return (
    <div
      role="status"
      aria-live="polite"
      className="border-b border-amber-500/40 bg-amber-500/10 px-4 py-2 text-xs text-amber-700 dark:text-amber-300"
    >
      {t("common.offline_banner")}
    </div>
  )
}
