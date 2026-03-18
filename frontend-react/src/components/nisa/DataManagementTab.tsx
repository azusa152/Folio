import { useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import {
  useEligibleAssetsMetadata,
  useRefreshEligibleAssets,
  useUploadEligibleAssets,
} from "@/api/hooks/useWrappers"

export function DataManagementTab() {
  const { t } = useTranslation()
  const [uploadWrapper, setUploadWrapper] = useState<"nisa_tsumitate" | "nisa_growth">(
    "nisa_tsumitate",
  )
  const [uploadFile, setUploadFile] = useState<File | null>(null)

  const tsumitateMetaQuery = useEligibleAssetsMetadata("nisa_tsumitate")
  const growthMetaQuery = useEligibleAssetsMetadata("nisa_growth")
  const refreshEligibleMutation = useRefreshEligibleAssets()
  const uploadEligibleMutation = useUploadEligibleAssets()

  const handleRefreshEligibleData = (wrapper: "nisa_tsumitate" | "nisa_growth") => {
    refreshEligibleMutation.mutate(wrapper, {
      onSuccess: () => {
        toast.success(t("eligibility.refresh_success"))
      },
      onError: () => {
        toast.error(t("eligibility.refresh_failed"))
      },
    })
  }

  const handleUploadEligibleData = () => {
    if (!uploadFile) return
    uploadEligibleMutation.mutate(
      { wrapper: uploadWrapper, file: uploadFile },
      {
        onSuccess: () => {
          toast.success(t("eligibility.upload_success"))
          setUploadFile(null)
        },
        onError: () => {
          toast.error(t("eligibility.upload_failed"))
        },
      },
    )
  }

  return (
    <div className="space-y-4">
      <div className="space-y-1">
        <h2 className="text-base font-semibold">{t("eligibility.data_management_title")}</h2>
        <p className="text-sm text-muted-foreground">{t("eligibility.data_management_hint")}</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
        <div className="rounded border border-border p-3">
          <p className="font-medium">{t("wrapper.nisa_tsumitate")}</p>
          <p className="text-muted-foreground">
            {t("eligibility.data_count_label", {
              count: tsumitateMetaQuery.data?.count ?? 0,
            })}
          </p>
          <p className="text-muted-foreground">
            {t("eligibility.data_last_updated_label", {
              date: tsumitateMetaQuery.data?.last_refreshed_at
                ? new Date(tsumitateMetaQuery.data.last_refreshed_at).toLocaleString()
                : "—",
            })}
          </p>
          <Button
            size="sm"
            variant="outline"
            className="mt-2 text-xs"
            disabled={refreshEligibleMutation.isPending}
            onClick={() => handleRefreshEligibleData("nisa_tsumitate")}
          >
            {t("eligibility.refresh_now")}
          </Button>
          <p className="mt-1 text-[11px] text-muted-foreground">{t("eligibility.refresh_hint")}</p>
        </div>

        <div className="rounded border border-border p-3">
          <p className="font-medium">{t("wrapper.nisa_growth")}</p>
          <p className="text-muted-foreground">
            {t("eligibility.data_count_label", {
              count: growthMetaQuery.data?.count ?? 0,
            })}
          </p>
          <p className="text-muted-foreground">
            {t("eligibility.data_last_updated_label", {
              date: growthMetaQuery.data?.last_refreshed_at
                ? new Date(growthMetaQuery.data.last_refreshed_at).toLocaleString()
                : "—",
            })}
          </p>
          <Button
            size="sm"
            variant="outline"
            className="mt-2 text-xs"
            disabled={refreshEligibleMutation.isPending}
            onClick={() => handleRefreshEligibleData("nisa_growth")}
          >
            {t("eligibility.refresh_now")}
          </Button>
          <p className="mt-1 text-[11px] text-muted-foreground">{t("eligibility.refresh_hint")}</p>
        </div>
      </div>

      <div className="space-y-2 border-t border-border pt-3">
        <p className="text-sm font-medium">{t("eligibility.upload_title")}</p>
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={uploadWrapper}
            onChange={(event) =>
              setUploadWrapper(event.target.value as "nisa_tsumitate" | "nisa_growth")
            }
            className="text-xs border border-border rounded px-2 py-2 min-h-[36px] bg-background"
          >
            <option value="nisa_tsumitate">{t("wrapper.nisa_tsumitate")}</option>
            <option value="nisa_growth">{t("wrapper.nisa_growth")}</option>
          </select>
          <input
            type="file"
            accept=".csv,.xlsx"
            onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)}
            className="text-xs"
          />
          <Button
            size="sm"
            variant="outline"
            className="text-xs"
            disabled={!uploadFile || uploadEligibleMutation.isPending}
            onClick={handleUploadEligibleData}
          >
            {t("eligibility.upload_button")}
          </Button>
        </div>
        <p className="text-[11px] text-muted-foreground">{t("eligibility.upload_hint")}</p>
      </div>
    </div>
  )
}
