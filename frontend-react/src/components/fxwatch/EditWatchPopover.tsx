import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { useUpdateFxWatch } from "@/api/hooks/useFxWatch"
import type { FxWatch } from "@/api/types/fxWatch"
import { Button } from "@/components/ui/button"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { getErrorMessage } from "@/lib/utils"

interface Props {
  watch: FxWatch
}

export function EditWatchPopover({ watch }: Props) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const [recentHighDays, setRecentHighDays] = useState(watch.recent_high_days)
  const [consecutiveDays, setConsecutiveDays] = useState(watch.consecutive_increase_days)
  const [alertOnHigh, setAlertOnHigh] = useState(watch.alert_on_recent_high)
  const [alertOnConsecutive, setAlertOnConsecutive] = useState(watch.alert_on_consecutive_increase)
  const [reminderHours, setReminderHours] = useState(watch.reminder_interval_hours)
  const [targetRateInput, setTargetRateInput] = useState(
    watch.target_rate != null ? String(watch.target_rate) : "",
  )
  const [targetDirection, setTargetDirection] = useState<"above" | "below" | "">(
    watch.target_direction ?? "",
  )
  const [feedback, setFeedback] = useState<string | null>(null)

  const update = useUpdateFxWatch()

  useEffect(() => {
    if (!open) return
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setRecentHighDays(watch.recent_high_days)
    setConsecutiveDays(watch.consecutive_increase_days)
    setAlertOnHigh(watch.alert_on_recent_high)
    setAlertOnConsecutive(watch.alert_on_consecutive_increase)
    setReminderHours(watch.reminder_interval_hours)
    setTargetRateInput(watch.target_rate != null ? String(watch.target_rate) : "")
    setTargetDirection(watch.target_direction ?? "")
    setFeedback(null)
  }, [open, watch])

  const handleSave = () => {
    if (!alertOnHigh && !alertOnConsecutive) {
      setFeedback(t("fx_watch.form.error_no_alert"))
      return
    }
    const parsedTargetRate = targetRateInput.trim() ? Number(targetRateInput) : null
    if (
      parsedTargetRate !== null &&
      (!Number.isFinite(parsedTargetRate) || parsedTargetRate <= 0)
    ) {
      setFeedback(t("fx_watch.form.error_target_rate"))
      return
    }
    if (parsedTargetRate !== null && targetDirection === "") {
      setFeedback(t("fx_watch.form.error_target_direction"))
      return
    }
    const normalizedTargetDirection = parsedTargetRate === null ? null : targetDirection || null
    update.mutate(
      {
        id: watch.id,
        payload: {
          recent_high_days: recentHighDays,
          consecutive_increase_days: consecutiveDays,
          alert_on_recent_high: alertOnHigh,
          alert_on_consecutive_increase: alertOnConsecutive,
          target_rate: parsedTargetRate,
          target_direction: normalizedTargetDirection,
          reminder_interval_hours: reminderHours,
        },
      },
      {
        onSuccess: () => {
          setFeedback(t("common.success"))
          setOpen(false)
        },
        onError: (err: unknown) => {
          toast.error(getErrorMessage(err) || t("common.error"))
        },
      },
    )
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button size="sm" variant="outline" className="text-xs">
          {t("fx_watch.edit.button")}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-72 space-y-3 p-4" align="start">
        <p className="text-sm font-semibold">
          {t("fx_watch.edit.title", { pair: `${watch.base_currency}/${watch.quote_currency}` })}
        </p>

        <div>
          <label htmlFor={`edit-recent-high-${watch.id}`} className="text-xs text-muted-foreground">
            {t("fx_watch.form.recent_high_days")}: {recentHighDays}
          </label>
          <input
            id={`edit-recent-high-${watch.id}`}
            type="range"
            min={5}
            max={90}
            step={5}
            value={recentHighDays}
            onChange={(e) => setRecentHighDays(Number(e.target.value))}
            aria-valuemin={5}
            aria-valuemax={90}
            aria-valuenow={recentHighDays}
            className="w-full"
          />
        </div>

        <div>
          <label htmlFor={`edit-consecutive-${watch.id}`} className="text-xs text-muted-foreground">
            {t("fx_watch.form.consecutive_days")}: {consecutiveDays}
          </label>
          <input
            id={`edit-consecutive-${watch.id}`}
            type="range"
            min={2}
            max={10}
            step={1}
            value={consecutiveDays}
            onChange={(e) => setConsecutiveDays(Number(e.target.value))}
            aria-valuemin={2}
            aria-valuemax={10}
            aria-valuenow={consecutiveDays}
            className="w-full"
          />
        </div>

        <hr className="border-border" />

        <div className="space-y-2">
          <label className="flex items-center gap-2 text-xs">
            <input
              type="checkbox"
              checked={alertOnHigh}
              onChange={(e) => setAlertOnHigh(e.target.checked)}
            />
            {t("fx_watch.form.alert_on_high")}
          </label>
          <label className="flex items-center gap-2 text-xs">
            <input
              type="checkbox"
              checked={alertOnConsecutive}
              onChange={(e) => setAlertOnConsecutive(e.target.checked)}
            />
            {t("fx_watch.form.alert_on_consecutive")}
          </label>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div>
            <label
              htmlFor={`edit-target-rate-${watch.id}`}
              className="text-xs text-muted-foreground"
            >
              {t("fx_watch.form.target_rate")}
            </label>
            <input
              id={`edit-target-rate-${watch.id}`}
              type="number"
              step="0.0001"
              min={0}
              value={targetRateInput}
              onChange={(e) => setTargetRateInput(e.target.value)}
              className="mt-0.5 w-full rounded-md border border-input bg-background px-2 py-1 text-sm"
            />
          </div>
          <div>
            <label className="text-xs text-muted-foreground">
              {t("fx_watch.form.target_direction")}
            </label>
            <Select
              value={targetDirection || undefined}
              onValueChange={(v: "above" | "below") => setTargetDirection(v)}
            >
              <SelectTrigger className="h-8 mt-0.5 text-xs">
                <SelectValue placeholder={t("fx_watch.form.target_direction_placeholder")} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="above" className="text-xs">
                  {t("fx_watch.form.target_direction_above")}
                </SelectItem>
                <SelectItem value="below" className="text-xs">
                  {t("fx_watch.form.target_direction_below")}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <div>
          <label
            htmlFor={`edit-watch-reminder-hours-${watch.id}`}
            className="text-xs text-muted-foreground"
          >
            {t("fx_watch.form.reminder_hours")}
          </label>
          <input
            id={`edit-watch-reminder-hours-${watch.id}`}
            type="number"
            min={1}
            max={168}
            value={reminderHours}
            onChange={(e) => setReminderHours(Number(e.target.value))}
            className="mt-0.5 w-full rounded-md border border-input bg-background px-2 py-1 text-sm"
          />
        </div>

        <Button size="sm" className="w-full" onClick={handleSave} disabled={update.isPending}>
          {t("fx_watch.form.save")}
        </Button>
        {feedback && <p className="text-xs text-muted-foreground">{feedback}</p>}
      </PopoverContent>
    </Popover>
  )
}
