import { useEffect, useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { useNavigate } from "react-router-dom"
import { toast } from "sonner"
import { useTriggerScan } from "@/api/hooks/useRadar"
import { useTriggerDigest, useSavePreferences } from "@/api/hooks/useAllocation"
import { useTheme } from "@/hooks/useTheme"
import { usePrivacyMode } from "@/hooks/usePrivacyMode"
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
  CommandShortcut,
} from "@/components/ui/command"
import { getErrorMessage } from "@/lib/utils"

export function CommandPalette() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const triggerScan = useTriggerScan()
  const triggerDigest = useTriggerDigest()
  const savePreferences = useSavePreferences()
  const { toggle: toggleTheme } = useTheme()
  const { isPrivate, toggle: togglePrivacy } = usePrivacyMode()

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key.toLowerCase() !== "k" || (!event.metaKey && !event.ctrlKey)) return
      event.preventDefault()
      setOpen((prev) => !prev)
    }
    document.addEventListener("keydown", onKeyDown)
    return () => document.removeEventListener("keydown", onKeyDown)
  }, [])

  const pages = useMemo(
    () => [
      { path: "/", label: t("nav.dashboard") },
      { path: "/radar", label: t("nav.radar") },
      { path: "/allocation", label: t("nav.allocation") },
      { path: "/nisa", label: t("nav.nisa") },
      { path: "/fx-watch", label: t("nav.fx_watch") },
      { path: "/smart-money", label: t("nav.smart_money") },
      { path: "/backtest", label: t("nav.backtest") },
    ],
    [t],
  )

  const onSelectPage = (path: string) => {
    navigate(path)
    setOpen(false)
  }

  const onTogglePrivacy = () => {
    togglePrivacy()
    const next = !isPrivate
    savePreferences.mutate(
      { privacy_mode: next },
      {
        onError: () => {
          /* fail silently — UI already updated optimistically */
        },
      },
    )
    setOpen(false)
  }

  const onToggleTheme = () => {
    toggleTheme()
    setOpen(false)
  }

  const onTriggerScan = () => {
    triggerScan.mutate(undefined, {
      onSuccess: () => {
        toast.success(t("radar.scan.default_success"))
      },
      onError: (err: unknown) => {
        toast.error(getErrorMessage(err) || t("common.error"))
      },
    })
    setOpen(false)
  }

  const onSendDigest = () => {
    triggerDigest.mutate(undefined, {
      onSuccess: () => {
        toast.success(t("api.digest_started"))
      },
      onError: (err: unknown) => {
        toast.error(getErrorMessage(err) || t("common.error"))
      },
    })
    setOpen(false)
  }

  return (
    <CommandDialog
      open={open}
      onOpenChange={setOpen}
      title={t("command_palette.title")}
      description={t("command_palette.description")}
      className="max-w-xl"
    >
      <CommandInput placeholder={t("command_palette.search_placeholder")} />
      <CommandList>
        <CommandEmpty>{t("command_palette.no_results")}</CommandEmpty>
        <CommandGroup heading={t("command_palette.group_pages")}>
          {pages.map((page) => (
            <CommandItem key={page.path} onSelect={() => onSelectPage(page.path)}>
              {page.label}
            </CommandItem>
          ))}
        </CommandGroup>
        <CommandSeparator />
        <CommandGroup heading={t("command_palette.group_actions")}>
          <CommandItem onSelect={onTogglePrivacy}>
            {isPrivate
              ? t("command_palette.action_privacy_off")
              : t("command_palette.action_privacy_on")}
          </CommandItem>
          <CommandItem onSelect={onToggleTheme}>
            {t("command_palette.action_toggle_theme")}
          </CommandItem>
          <CommandItem onSelect={onTriggerScan}>{t("command_palette.action_run_scan")}</CommandItem>
          <CommandItem onSelect={onSendDigest}>
            {t("command_palette.action_send_digest")}
          </CommandItem>
        </CommandGroup>
      </CommandList>
      <div className="border-t px-3 py-2 text-xs text-muted-foreground flex justify-end">
        <CommandShortcut>{t("command_palette.shortcut_hint")}</CommandShortcut>
      </div>
    </CommandDialog>
  )
}
