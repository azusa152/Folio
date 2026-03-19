import { useSearchParams } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { useIsPrivate } from "@/hooks/usePrivacyMode"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { GeneralSettings } from "@/components/settings/GeneralSettings"
import { TelegramSettings } from "@/components/settings/TelegramSettings"
import { NotificationPreferences } from "@/components/settings/NotificationPreferences"
import { TargetAllocation } from "@/components/allocation/tools/TargetAllocation"
import { HoldingsManager } from "@/components/allocation/holdings/HoldingsManager"

type SettingsTab = "general" | "portfolio" | "notifications"

export default function Settings() {
  const { t } = useTranslation()
  const [searchParams, setSearchParams] = useSearchParams()
  const privacyMode = useIsPrivate()

  const activeTab = (searchParams.get("tab") as SettingsTab) ?? "general"

  const handleTabChange = (value: string) => {
    setSearchParams({ tab: value }, { replace: true })
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-6 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{t("settings.page_title")}</h1>
        <p className="text-sm text-muted-foreground mt-1">
          {t("app.page_title")}
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={handleTabChange}>
        <TabsList className="w-full grid grid-cols-3">
          <TabsTrigger value="general" className="text-xs">
            {t("settings.tab_general")}
          </TabsTrigger>
          <TabsTrigger value="portfolio" className="text-xs">
            {t("settings.tab_portfolio")}
          </TabsTrigger>
          <TabsTrigger value="notifications" className="text-xs">
            {t("settings.tab_notifications")}
          </TabsTrigger>
        </TabsList>

        {/* General Tab */}
        <TabsContent value="general" className="mt-6">
          <GeneralSettings />
        </TabsContent>

        {/* Portfolio Tab */}
        <TabsContent value="portfolio" className="mt-6 space-y-6">
          <section className="space-y-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">
              {t("allocation.tab.portfolio")}
            </p>
            <div className="rounded-md border border-border p-4">
              <TargetAllocation />
            </div>
            <div className="rounded-md border border-border p-4">
              <HoldingsManager privacyMode={privacyMode} />
            </div>
          </section>
        </TabsContent>

        {/* Notifications Tab */}
        <TabsContent value="notifications" className="mt-6 space-y-6">
          <section className="space-y-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">
              {t("settings.telegram_section_title")}
            </p>
            <div className="rounded-md border border-border p-4">
              <TelegramSettings privacyMode={privacyMode} />
            </div>
          </section>

          <section className="space-y-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">
              {t("settings.alerts_section_title")}
            </p>
            <div className="rounded-md border border-border p-4">
              <NotificationPreferences />
            </div>
          </section>
        </TabsContent>
      </Tabs>
    </div>
  )
}
