import { useTranslation } from "react-i18next"
import { Button } from "@/components/ui/button"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { EditWatchPopover } from "../EditWatchPopover"
import type { FxWatch } from "@/api/types/fxWatch"

interface Props {
  watch: FxWatch
  pair: string
  handleToggle: () => void
  handleDeleteConfirm: () => void
  togglePending: boolean
  deletePending: boolean
}

export function WatchCardActions({
  watch,
  pair,
  handleToggle,
  handleDeleteConfirm,
  togglePending,
  deletePending,
}: Props) {
  const { t } = useTranslation()

  return (
    <div className="flex gap-2 flex-wrap">
      <Button
        size="sm"
        variant="outline"
        className="text-xs"
        onClick={handleToggle}
        disabled={togglePending}
      >
        {togglePending
          ? t("common.loading")
          : watch.is_active
            ? t("fx_watch.card.disable")
            : t("fx_watch.card.enable")}
      </Button>
      <EditWatchPopover watch={watch} />
      <AlertDialog>
        <AlertDialogTrigger asChild>
          <Button size="sm" variant="destructive" className="text-xs">
            {t("fx_watch.card.delete")}
          </Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("fx_watch.delete.title")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("fx_watch.delete.description", { pair })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t("common.cancel")}</AlertDialogCancel>
            <AlertDialogAction onClick={handleDeleteConfirm} disabled={deletePending}>
              {t("common.confirm")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
