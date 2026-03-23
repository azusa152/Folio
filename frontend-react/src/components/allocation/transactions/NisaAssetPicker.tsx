import { Check, ChevronsUpDown, Loader2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"
import type { NisaEligibleAssetItem } from "@/hooks/useAddTransactionForm"

interface NisaAssetPickerProps {
  ticker: string
  selectedWrapper: string
  nisaPickerOpen: boolean
  nisaPickerSearch: string
  nisaEligibleAssetsQuery: {
    isLoading: boolean
    data?: { items?: NisaEligibleAssetItem[] }
  }
  selectedNisaAssetForDisplay: NisaEligibleAssetItem | null
  isMobile: boolean
  commandListScrollFix: Record<string, unknown>
  onSelect: (item: NisaEligibleAssetItem) => void
  setNisaPickerOpen: (open: boolean) => void
  setNisaPickerSearch: (search: string) => void
}

export function NisaAssetPicker({
  ticker,
  selectedWrapper,
  nisaPickerOpen,
  nisaPickerSearch,
  nisaEligibleAssetsQuery,
  selectedNisaAssetForDisplay,
  isMobile,
  commandListScrollFix,
  onSelect,
  setNisaPickerOpen,
  setNisaPickerSearch,
}: NisaAssetPickerProps) {
  const { t } = useTranslation()
  const items = nisaEligibleAssetsQuery.data?.items ?? []

  return (
    <Popover
      open={nisaPickerOpen}
      onOpenChange={(nextOpen) => {
        setNisaPickerOpen(nextOpen)
        if (nextOpen) setNisaPickerSearch("")
      }}
    >
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          role="combobox"
          aria-expanded={nisaPickerOpen}
          className="h-auto min-h-9 w-full justify-between py-1.5 text-xs"
        >
          <span className="min-w-0 text-left">
            {selectedNisaAssetForDisplay ? (
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span className="min-w-0 flex flex-col leading-tight">
                      <span className="truncate font-medium text-xs">
                        {selectedNisaAssetForDisplay.fund_name ||
                          selectedNisaAssetForDisplay.ticker}
                      </span>
                      <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
                        <span>
                          {selectedNisaAssetForDisplay.ticker}
                          {selectedNisaAssetForDisplay.trust_fee_pct != null
                            ? ` · ${t("eligibility.nisa_trust_fee_label")}: ${selectedNisaAssetForDisplay.trust_fee_pct.toFixed(3)}%`
                            : ""}
                        </span>
                        {selectedWrapper === "nisa_growth" &&
                        selectedNisaAssetForDisplay.asset_type ? (
                          <Badge variant="outline" className="h-4 px-1 text-[10px] font-normal">
                            {t(
                              `nisa.eligible.asset_type.${selectedNisaAssetForDisplay.asset_type}`,
                            )}
                          </Badge>
                        ) : null}
                      </span>
                    </span>
                  </TooltipTrigger>
                  {selectedNisaAssetForDisplay.fund_name ? (
                    <TooltipContent side="bottom" className="max-w-xs text-xs">
                      {selectedNisaAssetForDisplay.fund_name}
                    </TooltipContent>
                  ) : null}
                </Tooltip>
              </TooltipProvider>
            ) : ticker.trim() ? (
              <span className="truncate">{ticker.trim().toUpperCase()}</span>
            ) : (
              t("eligibility.nisa_picker_placeholder")
            )}
          </span>
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent
        className="w-[360px] max-w-[calc(100vw-2rem)] p-0"
        align="start"
        onOpenAutoFocus={(event) => {
          if (isMobile) event.preventDefault()
        }}
      >
        <Command shouldFilter={false}>
          <CommandInput
            value={nisaPickerSearch}
            onValueChange={setNisaPickerSearch}
            placeholder={t("eligibility.nisa_picker_search")}
          />
          <CommandList {...commandListScrollFix}>
            {nisaEligibleAssetsQuery.isLoading ? (
              <div className="flex items-center gap-2 px-3 py-4 text-xs text-muted-foreground">
                <Loader2 className="h-3.5 w-3.5 animate-spin shrink-0" />
                {t("eligibility.nisa_picker_loading")}
              </div>
            ) : (
              <>
                <CommandEmpty>{t("eligibility.nisa_picker_empty")}</CommandEmpty>
                <CommandGroup>
                  {items.map((item) => (
                    <CommandItem
                      key={`${item.ticker}-${item.fund_name}`}
                      value={`${item.ticker} ${item.fund_name}`}
                      onSelect={() => {
                        onSelect(item)
                      }}
                    >
                      <Check
                        className={cn(
                          "h-4 w-4",
                          ticker.trim().toUpperCase() === item.ticker.toUpperCase()
                            ? "opacity-100"
                            : "opacity-0",
                        )}
                      />
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <div className="min-w-0 flex-1">
                              <p className="truncate text-xs font-medium">
                                {item.fund_name || item.ticker}
                              </p>
                              <div className="flex items-center gap-1 text-[11px] text-muted-foreground">
                                <span>
                                  {item.ticker}
                                  {item.trust_fee_pct != null
                                    ? ` · ${t("eligibility.nisa_trust_fee_label")}: ${item.trust_fee_pct.toFixed(3)}%`
                                    : ""}
                                </span>
                                {selectedWrapper === "nisa_growth" && item.asset_type ? (
                                  <Badge
                                    variant="outline"
                                    className="h-4 px-1 text-[10px] font-normal"
                                  >
                                    {t(`nisa.eligible.asset_type.${item.asset_type}`)}
                                  </Badge>
                                ) : null}
                              </div>
                            </div>
                          </TooltipTrigger>
                          {item.fund_name ? (
                            <TooltipContent side="right" className="max-w-xs text-xs">
                              {item.fund_name}
                            </TooltipContent>
                          ) : null}
                        </Tooltip>
                      </TooltipProvider>
                    </CommandItem>
                  ))}
                </CommandGroup>
              </>
            )}
          </CommandList>
          {!nisaEligibleAssetsQuery.isLoading && items.length > 0 ? (
            <p className="border-t px-3 py-2 text-[11px] text-muted-foreground">
              {t("eligibility.nisa_picker_limit_hint")}
            </p>
          ) : null}
        </Command>
      </PopoverContent>
    </Popover>
  )
}
