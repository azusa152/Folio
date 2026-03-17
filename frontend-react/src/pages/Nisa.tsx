import { useTranslation } from "react-i18next"
import { useSearchParams } from "react-router-dom"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { QuotaDashboard } from "@/components/allocation/wrappers/QuotaDashboard"
import { EligibleAssetsTab } from "@/components/nisa/EligibleAssetsTab"
import { DataManagementTab } from "@/components/nisa/DataManagementTab"
import { ContributionsTab } from "@/components/nisa/ContributionsTab"
import { NisaEducationCard } from "@/components/nisa/NisaEducationCard"
import { useEligibleAssetsMetadata } from "@/api/hooks/useWrappers"

type NisaTab = "eligible" | "quota" | "contributions" | "data"

export default function Nisa() {
  const { t } = useTranslation()
  const [searchParams, setSearchParams] = useSearchParams()
  const tabParam = searchParams.get("tab")
  const activeTab: NisaTab =
    tabParam === "quota" || tabParam === "contributions" || tabParam === "data"
      ? tabParam
      : "eligible"

  const tsumitateMetaQuery = useEligibleAssetsMetadata("nisa_tsumitate")
  const growthMetaQuery = useEligibleAssetsMetadata("nisa_growth")

  const setActiveTab = (tab: string) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      if (tab === "eligible") next.delete("tab")
      else next.set("tab", tab)
      return next
    })
  }

  return (
    <div className="p-3 sm:p-6 space-y-4">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold">{t("nisa.title")}</h1>
        <p className="text-sm text-muted-foreground">{t("nisa.caption")}</p>
        <p className="text-xs text-muted-foreground mt-1">
          {t("eligibility.last_updated_compact", {
            tsumitate: tsumitateMetaQuery.data?.last_refreshed_at
              ? new Date(tsumitateMetaQuery.data.last_refreshed_at).toLocaleDateString()
              : "—",
            growth: growthMetaQuery.data?.last_refreshed_at
              ? new Date(growthMetaQuery.data.last_refreshed_at).toLocaleDateString()
              : "—",
          })}
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="flex-wrap h-auto min-h-[44px] gap-1">
          <TabsTrigger value="eligible" className="min-h-[44px]">
            {t("nisa.tabs.eligible")}
          </TabsTrigger>
          <TabsTrigger value="quota" className="min-h-[44px]">
            {t("nisa.tabs.quota")}
          </TabsTrigger>
          <TabsTrigger value="contributions" className="min-h-[44px]">
            {t("nisa.tabs.contributions")}
          </TabsTrigger>
          <TabsTrigger value="data" className="min-h-[44px]">
            {t("nisa.tabs.data")}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="eligible" className="mt-4">
          <EligibleAssetsTab />
        </TabsContent>

        <TabsContent value="quota" className="mt-4 space-y-4">
          <div className="space-y-4">
            <QuotaDashboard enabled={activeTab === "quota"} />
            <NisaEducationCard />
          </div>
        </TabsContent>

        <TabsContent value="contributions" className="mt-4">
          <ContributionsTab />
        </TabsContent>

        <TabsContent value="data" className="mt-4">
          <DataManagementTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}
