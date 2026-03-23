import { useTranslation } from "react-i18next"
import { formatValue } from "./formatters"
import { FINANCE_TEXT } from "@/lib/colors"
import type { ActivityFeed, ActivityFeedItem } from "@/api/types/smartMoney"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"

type ActivityKind = "bought" | "sold"

function GuruActivityPopover({
  ticker,
  gurus,
  activity,
}: {
  ticker: string
  gurus: string[]
  activity: ActivityKind
}) {
  const { t } = useTranslation()
  if (gurus.length === 0) return null

  const viewKey =
    activity === "sold" ? "smart_money.activity.view_sellers" : "smart_money.activity.view_buyers"
  const ariaKey =
    activity === "sold"
      ? "smart_money.activity.view_sellers_aria"
      : "smart_money.activity.view_buyers_aria"
  const titleKey =
    activity === "sold" ? "smart_money.activity.sellers_title" : "smart_money.activity.buyers_title"

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          className="inline-flex items-center rounded-sm px-2 py-1 text-xs text-muted-foreground underline underline-offset-2 transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring min-h-11"
          aria-label={t(ariaKey, { ticker })}
        >
          {t(viewKey)}
        </button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-60 max-w-[calc(100vw-2rem)] p-3 text-xs space-y-2">
        <p className="font-medium">{t(titleKey, { ticker })}</p>
        <ul
          className="max-h-52 space-y-1 overflow-y-auto pr-1 text-muted-foreground"
          data-testid="guru-holders-list"
        >
          {gurus.map((guru) => (
            <li key={guru}>{guru}</li>
          ))}
        </ul>
      </PopoverContent>
    </Popover>
  )
}

function FeedList({
  items,
  emptyKey,
  activity,
}: {
  items: ActivityFeedItem[]
  emptyKey: string
  activity: ActivityKind
}) {
  const { t } = useTranslation()
  if (items.length === 0) {
    return <p className="text-xs text-muted-foreground">{t(emptyKey)}</p>
  }
  return (
    <div className="space-y-1">
      {items.map((item) => (
        <div key={item.ticker} className="flex items-start justify-between gap-2 text-xs">
          <div className="min-w-0">
            <span className="font-medium">{item.ticker}</span>
            <div>
              <GuruActivityPopover ticker={item.ticker} gurus={item.gurus} activity={activity} />
            </div>
          </div>
          <div className="shrink-0 text-right">
            <span className="font-medium">
              {item.guru_count} {t("smart_money.activity.guru_count_label")}
            </span>
            <span className="text-muted-foreground ml-1">{formatValue(item.total_value)}</span>
          </div>
        </div>
      ))}
    </div>
  )
}

export function ActivityFeed({ data }: { data: ActivityFeed }) {
  const { t } = useTranslation()
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <div className="space-y-2">
        <p className={`text-xs font-semibold ${FINANCE_TEXT.gain}`}>
          {t("smart_money.activity.most_bought")}
        </p>
        <FeedList
          items={data.most_bought}
          emptyKey="smart_money.activity.empty_bought"
          activity="bought"
        />
      </div>
      <div className="space-y-2">
        <p className={`text-xs font-semibold ${FINANCE_TEXT.loss}`}>
          {t("smart_money.activity.most_sold")}
        </p>
        <FeedList
          items={data.most_sold}
          emptyKey="smart_money.activity.empty_sold"
          activity="sold"
        />
      </div>
    </div>
  )
}
