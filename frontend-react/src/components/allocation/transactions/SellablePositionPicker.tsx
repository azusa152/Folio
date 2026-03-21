import { Check, ChevronsUpDown, Loader2 } from "lucide-react"
import { useTranslation } from "react-i18next"
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
import type { SellablePositionItem, TransactionType } from "@/hooks/useAddTransactionForm"

interface SellablePositionPickerProps {
  ticker: string
  transactionType: TransactionType
  sellPickerOpen: boolean
  sellPickerSearch: string
  filteredSellablePositions: SellablePositionItem[]
  selectedSellablePositionForDisplay: SellablePositionItem | null
  sellablePositionsQuery: { isLoading: boolean; isError: boolean }
  isMobile: boolean
  commandListScrollFix: Record<string, unknown>
  getSellValueSourceLabel: (valueSource?: SellablePositionItem["value_source"]) => string | null
  onSelect: (item: SellablePositionItem) => void
  setSellPickerOpen: (open: boolean) => void
  setSellPickerSearch: (search: string) => void
}

export function SellablePositionPicker({
  ticker,
  transactionType,
  sellPickerOpen,
  sellPickerSearch,
  filteredSellablePositions,
  selectedSellablePositionForDisplay,
  sellablePositionsQuery,
  isMobile,
  commandListScrollFix,
  getSellValueSourceLabel,
  onSelect,
  setSellPickerOpen,
  setSellPickerSearch,
}: SellablePositionPickerProps) {
  const { t } = useTranslation()

  return (
    <Popover
      open={sellPickerOpen}
      onOpenChange={(nextOpen) => {
        setSellPickerOpen(nextOpen)
        if (nextOpen) setSellPickerSearch("")
      }}
    >
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          role="combobox"
          aria-expanded={sellPickerOpen}
          className="h-auto min-h-9 w-full justify-between py-1.5 text-xs"
        >
          <span className="min-w-0 text-left">
            {selectedSellablePositionForDisplay ? (
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span className="min-w-0 flex flex-col leading-tight">
                      <span className="truncate font-medium text-xs">
                        {selectedSellablePositionForDisplay.fund_name ||
                          selectedSellablePositionForDisplay.ticker}
                      </span>
                      <span className="truncate text-[11px] text-muted-foreground">
                        {selectedSellablePositionForDisplay.ticker} ·{" "}
                        {selectedSellablePositionForDisplay.quantity.toLocaleString()}
                      </span>
                      {getSellValueSourceLabel(selectedSellablePositionForDisplay.value_source) ? (
                        <span
                          className={cn(
                            "truncate text-[10px] mt-0.5",
                            selectedSellablePositionForDisplay.value_source === "cost_basis"
                              ? "text-amber-500"
                              : "text-muted-foreground",
                          )}
                        >
                          {getSellValueSourceLabel(selectedSellablePositionForDisplay.value_source)}
                        </span>
                      ) : null}
                    </span>
                  </TooltipTrigger>
                  {selectedSellablePositionForDisplay.fund_name ? (
                    <TooltipContent side="bottom" className="max-w-xs text-xs">
                      {selectedSellablePositionForDisplay.fund_name}
                    </TooltipContent>
                  ) : null}
                </Tooltip>
              </TooltipProvider>
            ) : ticker.trim() ? (
              <span className="truncate">{ticker.trim().toUpperCase()}</span>
            ) : transactionType === "DIVIDEND" ? (
              t("transactions.sell_picker.placeholder_dividend")
            ) : (
              t("transactions.sell_picker.placeholder")
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
            value={sellPickerSearch}
            onValueChange={setSellPickerSearch}
            placeholder={t("transactions.sell_picker.search")}
          />
          <CommandList {...commandListScrollFix}>
            {sellablePositionsQuery.isLoading ? (
              <div className="flex items-center gap-2 px-3 py-4 text-xs text-muted-foreground">
                <Loader2 className="h-3.5 w-3.5 animate-spin shrink-0" />
                {t("transactions.sell_picker.loading")}
              </div>
            ) : sellablePositionsQuery.isError ? (
              <div className="px-3 py-4 text-xs text-destructive">
                {t("transactions.sell_picker.load_error")}
              </div>
            ) : (
              <>
                <CommandEmpty>{t("transactions.sell_picker.empty")}</CommandEmpty>
                <CommandGroup>
                  {filteredSellablePositions.map((item) => (
                    <CommandItem
                      key={item.ticker}
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
                              <p className="truncate text-[11px] text-muted-foreground">
                                {item.ticker} · {item.quantity.toLocaleString()} ·{" "}
                                {item.market_value != null
                                  ? `${item.currency} ${item.market_value.toLocaleString(undefined, { maximumFractionDigits: 2 })}`
                                  : t("transactions.sell_picker.price_unavailable")}
                              </p>
                              {getSellValueSourceLabel(item.value_source) ? (
                                <p
                                  className={cn(
                                    "text-[10px] mt-0.5",
                                    item.value_source === "cost_basis"
                                      ? "text-amber-500"
                                      : "text-muted-foreground",
                                  )}
                                >
                                  {getSellValueSourceLabel(item.value_source)}
                                </p>
                              ) : null}
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
        </Command>
      </PopoverContent>
    </Popover>
  )
}
