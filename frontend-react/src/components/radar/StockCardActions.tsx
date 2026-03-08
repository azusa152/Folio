import { memo, useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { STOCK_CATEGORIES, CATEGORY_ICON_SHORT } from "@/lib/constants"
import { FINANCE_TEXT } from "@/lib/colors"
import { useAddThesis, useUpdateCategory, useDeactivateStock } from "@/api/hooks/useRadar"
import type { RadarStock, StockCategory } from "@/api/types/radar"
import { getErrorMessage } from "@/lib/utils"

function ThesisForm({ ticker, stock }: { ticker: string; stock: RadarStock }) {
  const { t } = useTranslation()
  const [thesisText, setThesisText] = useState("")
  const [tags, setTagsText] = useState("")
  const [feedback, setFeedback] = useState<string | null>(null)
  const addThesis = useAddThesis()

  const handleSubmit = () => {
    if (!thesisText.trim()) {
      setFeedback(t("radar.stock_card.error_no_thesis"))
      return
    }
    const tagList = tags
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean)
    addThesis.mutate(
      { ticker, payload: { content: thesisText.trim(), tags: tagList.length ? tagList : stock.current_tags } },
      {
        onSuccess: () => {
          setFeedback(t("common.success"))
          setThesisText("")
          setTagsText("")
        },
        onError: (err: unknown) => {
          toast.error(getErrorMessage(err) || t("common.error"))
        },
      },
    )
  }

  return (
    <div className="space-y-2">
      <textarea
        className="w-full rounded-md border border-input bg-background p-2 text-sm resize-none"
        rows={3}
        placeholder={t("radar.stock_card.update_thesis_placeholder")}
        value={thesisText}
        onChange={(e) => setThesisText(e.target.value)}
      />
      <input
        className="w-full rounded-md border border-input bg-background px-2 py-1 text-xs"
        placeholder={t("radar.stock_card.tags_placeholder")}
        value={tags}
        onChange={(e) => setTagsText(e.target.value)}
      />
      <Button size="sm" onClick={handleSubmit} disabled={addThesis.isPending}>
        {t("radar.stock_card.update_button")}
      </Button>
      {feedback && <p className="text-xs text-muted-foreground">{feedback}</p>}
    </div>
  )
}

function ChangeCategoryForm({ ticker, currentCategory }: { ticker: string; currentCategory: StockCategory }) {
  const { t } = useTranslation()
  const [selected, setSelected] = useState<StockCategory>(
    STOCK_CATEGORIES.find((c) => c !== currentCategory) ?? "Growth",
  )
  const [feedback, setFeedback] = useState<string | null>(null)
  const updateCategory = useUpdateCategory()

  const others = STOCK_CATEGORIES.filter((c) => c !== currentCategory)

  const handleConfirm = () => {
    updateCategory.mutate(
      { ticker, payload: { category: selected } },
      {
        onSuccess: (data) => {
          const msg = data?.message ?? t("common.success")
          setFeedback(msg)
        },
        onError: (err: unknown) => {
          toast.error(getErrorMessage(err) || t("common.error"))
        },
      },
    )
  }

  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">
        {t("radar.stock_card.current_category_label", { cat: currentCategory })}
      </p>
      <Select value={selected} onValueChange={(v) => setSelected(v as StockCategory)}>
        <SelectTrigger className="text-xs h-8">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {others.map((c) => (
            <SelectItem key={c} value={c} className="text-xs">
              {CATEGORY_ICON_SHORT[c] ?? ""} {c.replace("_", " ")}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Button size="sm" variant="outline" onClick={handleConfirm} disabled={updateCategory.isPending}>
        {t("radar.stock_card.confirm_switch")}
      </Button>
      {feedback && <p className="text-xs text-muted-foreground">{feedback}</p>}
    </div>
  )
}

function RemoveForm({ ticker }: { ticker: string }) {
  const { t } = useTranslation()
  const [reason, setReason] = useState("")
  const [feedback, setFeedback] = useState<string | null>(null)
  const deactivate = useDeactivateStock()

  const handleRemove = () => {
    if (!reason.trim()) {
      setFeedback(t("radar.stock_card.remove_reason_required"))
      return
    }
    deactivate.mutate(
      { ticker, payload: { reason: reason.trim() } },
      {
        onSuccess: (data) => {
          const msg = data?.message ?? t("common.success")
          setFeedback(msg)
        },
        onError: (err: unknown) => {
          toast.error(getErrorMessage(err) || t("common.error"))
        },
      },
    )
  }

  return (
    <div className="space-y-2">
      <p className={`text-xs ${FINANCE_TEXT.warning}`}>{t("radar.stock_card.remove_warning")}</p>
      <textarea
        className="w-full rounded-md border border-input bg-background p-2 text-sm resize-none"
        rows={2}
        placeholder={t("radar.stock_card.remove_reason_placeholder")}
        value={reason}
        onChange={(e) => setReason(e.target.value)}
      />
      <Button size="sm" variant="destructive" onClick={handleRemove} disabled={deactivate.isPending}>
        {t("radar.stock_card.confirm_remove")}
      </Button>
      {feedback && <p className="text-xs text-muted-foreground">{feedback}</p>}
    </div>
  )
}

interface Props {
  stock: RadarStock
}

export const StockCardActions = memo(function StockCardActions({ stock }: Props) {
  const ticker = stock.ticker
  const { t } = useTranslation()

  return (
    <div className="border-t border-border/50 pt-3 space-y-4">
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
        {t("radar.stock_card.section_actions")}
      </p>

      <div className="space-y-1.5">
        <p className="text-xs font-medium">{t("radar.stock_card.update_thesis")}</p>
        <ThesisForm ticker={ticker} stock={stock} />
      </div>

      <div className="space-y-1.5">
        <p className="text-xs font-medium">{t("radar.stock_card.change_category")}</p>
        <ChangeCategoryForm ticker={ticker} currentCategory={stock.category} />
      </div>

      <div className="space-y-1.5">
        <p className="text-xs font-medium">{t("radar.stock_card.remove")}</p>
        <RemoveForm ticker={ticker} />
      </div>
    </div>
  )
})
