import { useState, useRef } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Button } from "@/components/ui/button"
import { MARKET_TAG_OPTIONS, MARKET_OPTIONS } from "@/lib/constants"
import { useAddStock, useTriggerScan, useImportStocks } from "@/api/hooks/useRadar"
import { useCryptoSearch } from "@/api/hooks/useCrypto"
import client from "@/api/client"
import type { AddStockRequest, StockCategory, StockImportItem } from "@/api/types/radar"
import { getErrorMessage } from "@/lib/utils"
import { AddStockForm } from "./AddStockForm"
import { AddBondForm } from "./AddBondForm"
import { AddCryptoForm } from "./AddCryptoForm"

interface Props {
  open: boolean
  onClose: () => void
  isScanning: boolean
}

type AssetType = "stock" | "bond" | "crypto"

export function AddStockDrawer({ open, onClose, isScanning }: Props) {
  const { t } = useTranslation()

  // Stock form state
  const [assetType, setAssetType] = useState<AssetType>("stock")
  const [market, setMarket] = useState("US")
  const [ticker, setTicker] = useState("")
  const [category, setCategory] = useState<StockCategory>("Growth")
  const [thesis, setThesis] = useState("")
  const [selectedTags, setSelectedTags] = useState<string[]>([])

  // Bond form state (reuses ticker + thesis from stock form)
  const [bondCurrency, setBondCurrency] = useState("USD")
  const [cryptoQuery, setCryptoQuery] = useState("")
  const [cryptoCoinId, setCryptoCoinId] = useState<string | null>(null)

  // Feedback
  const [addFeedback, setAddFeedback] = useState<string | null>(null)
  const [scanFeedback, setScanFeedback] = useState<string | null>(null)
  const [exportCount, setExportCount] = useState<number | null>(null)
  const [importFeedback, setImportFeedback] = useState<string | null>(null)
  const [exporting, setExporting] = useState(false)

  const fileInputRef = useRef<HTMLInputElement>(null)

  const addStock = useAddStock()
  const triggerScan = useTriggerScan()
  const importStocks = useImportStocks()
  const { data: cryptoSearchResults } = useCryptoSearch(cryptoQuery)

  const marketInfo = MARKET_OPTIONS.find((m) => m.key === market) ?? MARKET_OPTIONS[0]

  const tagOptions = MARKET_TAG_OPTIONS[market] ?? MARKET_TAG_OPTIONS.US

  const handleAddStock = () => {
    if (!ticker.trim()) {
      setAddFeedback(t("radar.form.error_no_ticker"))
      return
    }
    if (market === "JP" && !/^\d{4}$/.test(ticker.trim())) {
      setAddFeedback(t("radar.form.error_jp_ticker_format"))
      return
    }
    if (market === "TW" && !/^\d{4,6}$/.test(ticker.trim())) {
      setAddFeedback(t("radar.form.error_tw_ticker_format"))
      return
    }
    if (!thesis.trim()) {
      setAddFeedback(t("radar.form.error_no_thesis"))
      return
    }
    const fullTicker = ticker.trim().toUpperCase() + marketInfo.suffix
    const tags = [...selectedTags, t(marketInfo.labelKey), marketInfo.currency]
    addStock.mutate(
      { ticker: fullTicker, category, thesis: thesis.trim(), tags, is_etf: false },
      {
        onSuccess: () => {
          setAddFeedback(null)
          toast.success(t("radar.form.success_added", { ticker: fullTicker }))
          setTicker("")
          setThesis("")
          setSelectedTags([])
        },
        onError: (err: unknown) => {
          toast.error(getErrorMessage(err) || t("common.error"))
        },
      },
    )
  }

  const handleAddBond = () => {
    if (!ticker.trim()) {
      setAddFeedback(t("radar.form.error_no_bond_ticker"))
      return
    }
    if (!thesis.trim()) {
      setAddFeedback(t("radar.form.error_no_thesis"))
      return
    }
    const fullTicker = ticker.trim().toUpperCase()
    const tags = [...selectedTags, bondCurrency]
    addStock.mutate(
      { ticker: fullTicker, category: "Bond", thesis: thesis.trim(), tags },
      {
        onSuccess: () => {
          setAddFeedback(null)
          toast.success(t("radar.form.success_added", { ticker: fullTicker }))
          setTicker("")
          setThesis("")
          setSelectedTags([])
        },
        onError: (err: unknown) => {
          toast.error(getErrorMessage(err) || t("common.error"))
        },
      },
    )
  }

  const handleAddCrypto = () => {
    if (!ticker.trim()) {
      setAddFeedback(t("radar.form.crypto_select_required"))
      return
    }
    if (!thesis.trim()) {
      setAddFeedback(t("radar.form.error_no_thesis"))
      return
    }
    const fullTicker = ticker.trim().toUpperCase()
    const payload: AddStockRequest = {
      ticker: fullTicker,
      category: "Crypto",
      thesis: thesis.trim(),
      tags: ["Crypto", "USD"],
      coingecko_id: cryptoCoinId ?? undefined,
    }
    addStock.mutate(payload, {
      onSuccess: () => {
        setAddFeedback(null)
        toast.success(t("radar.form.success_added", { ticker: fullTicker }))
        setTicker("")
        setThesis("")
        setSelectedTags([])
        setCryptoQuery("")
        setCryptoCoinId(null)
      },
      onError: (err: unknown) => {
        toast.error(getErrorMessage(err) || t("common.error"))
      },
    })
  }

  const handleScan = () => {
    setScanFeedback(null)
    triggerScan.mutate(undefined, {
      onSuccess: (data) => {
        if ((data as Record<string, unknown> | undefined)?.error_code === "scan_in_progress") {
          setScanFeedback(null)
          toast.success(t("radar.scan.already_running"))
        } else {
          const msg = t("radar.scan.success", {
            message: data?.message ?? t("radar.scan.default_success"),
          })
          setScanFeedback(null)
          toast.success(msg)
        }
      },
      onError: (err: unknown) => {
        toast.error(getErrorMessage(err) || t("common.error"))
      },
    })
  }

  const handleExport = async () => {
    setExporting(true)
    try {
      const { data, error } = await client.GET("/stocks/export")
      if (error) throw error
      const json = JSON.stringify(data, null, 2)
      const blob = new Blob([json], { type: "application/json" })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = "folio_watchlist.json"
      a.click()
      URL.revokeObjectURL(url)
      setExportCount(Array.isArray(data) ? (data as unknown[]).length : null)
    } catch {
      setExportCount(null)
      toast.error(t("common.error"))
    } finally {
      setExporting(false)
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => {
      try {
        const parsed = JSON.parse(ev.target?.result as string)
        if (!Array.isArray(parsed)) {
          setImportFeedback(t("radar.import.error_not_array"))
          return
        }
        importStocks.mutate(parsed as StockImportItem[], {
          onSuccess: (data) => {
            const msg = data?.message ?? t("radar.import.success")
            setImportFeedback(null)
            toast.success(msg)
          },
          onError: (err: unknown) => {
            toast.error(getErrorMessage(err) || t("common.error"))
          },
        })
      } catch {
        setImportFeedback(t("radar.import.error_json"))
      }
    }
    reader.onerror = () => {
      toast.error(t("common.error"))
    }
    reader.readAsText(file)
    // Reset input so same file can be re-uploaded
    e.target.value = ""
  }

  const handleDownloadTemplate = () => {
    const template = [
      { ticker: "AAPL", category: "Growth", thesis: "iPhone ecosystem", tags: ["US", "USD"] },
    ]
    const blob = new Blob([JSON.stringify(template, null, 2)], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "stock_import_template.json"
    a.click()
    URL.revokeObjectURL(url)
  }

  const toggleTag = (tag: string) => {
    setSelectedTags((prev) => (prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]))
  }

  return (
    <Sheet
      open={open}
      onOpenChange={(v) => {
        if (!v) onClose()
      }}
    >
      <SheetContent side="right" className="w-80 overflow-y-auto">
        <SheetHeader>
          <SheetTitle className="text-base">{t("radar.panel_header")}</SheetTitle>
        </SheetHeader>

        <div className="mt-4 space-y-6">
          {/* Add Stock/Bond */}
          <section>
            <p className="text-sm font-semibold mb-2">{t("radar.panel.add_stock")}</p>

            {/* Asset type toggle */}
            <div className="flex gap-2 mb-3">
              <button
                onClick={() => {
                  setAssetType("stock")
                  setAddFeedback(null)
                }}
                className={`flex-1 rounded py-1 text-xs font-medium border transition-colors ${assetType === "stock" ? "bg-primary text-primary-foreground border-primary" : "border-border text-muted-foreground hover:text-foreground"}`}
              >
                {t("radar.form.asset_stock")}
              </button>
              <button
                onClick={() => {
                  setAssetType("bond")
                  setAddFeedback(null)
                }}
                className={`flex-1 rounded py-1 text-xs font-medium border transition-colors ${assetType === "bond" ? "bg-primary text-primary-foreground border-primary" : "border-border text-muted-foreground hover:text-foreground"}`}
              >
                {t("radar.form.asset_bond")}
              </button>
              <button
                onClick={() => {
                  setAssetType("crypto")
                  setAddFeedback(null)
                }}
                className={`flex-1 rounded py-1 text-xs font-medium border transition-colors ${assetType === "crypto" ? "bg-primary text-primary-foreground border-primary" : "border-border text-muted-foreground hover:text-foreground"}`}
              >
                {t("radar.form.asset_crypto")}
              </button>
            </div>

            {assetType === "stock" ? (
              <AddStockForm
                market={market}
                ticker={ticker}
                category={category}
                thesis={thesis}
                selectedTags={selectedTags}
                tagOptions={tagOptions}
                marketInfo={marketInfo}
                isPending={addStock.isPending}
                onMarketChange={(v) => {
                  setMarket(v)
                  setSelectedTags([])
                }}
                onTickerChange={setTicker}
                onCategoryChange={setCategory}
                onThesisChange={setThesis}
                onToggleTag={toggleTag}
                onSubmit={handleAddStock}
              />
            ) : assetType === "bond" ? (
              <AddBondForm
                ticker={ticker}
                bondCurrency={bondCurrency}
                thesis={thesis}
                selectedTags={selectedTags}
                market={market}
                isPending={addStock.isPending}
                onTickerChange={setTicker}
                onCurrencyChange={setBondCurrency}
                onThesisChange={setThesis}
                onToggleTag={toggleTag}
                onSubmit={handleAddBond}
              />
            ) : (
              <AddCryptoForm
                ticker={ticker}
                thesis={thesis}
                cryptoQuery={cryptoQuery}
                searchResults={cryptoSearchResults}
                isPending={addStock.isPending}
                onQueryChange={(q) => {
                  setCryptoQuery(q)
                  setTicker("")
                  setCryptoCoinId(null)
                }}
                onSelectCoin={(t, id, display) => {
                  setTicker(t)
                  setCryptoCoinId(id)
                  setCryptoQuery(display)
                }}
                onThesisChange={setThesis}
                onSubmit={handleAddCrypto}
              />
            )}

            {addFeedback && <p className="text-xs text-destructive mt-1">{addFeedback}</p>}
          </section>

          <hr className="border-border" />

          {/* Scan section */}
          <section>
            <p className="text-sm font-semibold mb-1">{t("radar.panel.scan")}</p>
            <p className="text-xs text-muted-foreground mb-2">{t("radar.scan.caption")}</p>
            {isScanning && (
              <div className="rounded bg-muted/50 p-2 text-xs mb-2">
                <p>{t("radar.scan.running")}</p>
                <p className="text-muted-foreground mt-0.5">
                  {t("radar.scan.running_description")}
                </p>
              </div>
            )}
            <Button
              size="sm"
              className="w-full"
              onClick={handleScan}
              disabled={isScanning || triggerScan.isPending}
            >
              {t("radar.scan.button")}
            </Button>
            {scanFeedback && <p className="text-xs text-destructive mt-1">{scanFeedback}</p>}
          </section>

          <hr className="border-border" />

          {/* Export */}
          <section>
            <p className="text-sm font-semibold mb-2">{t("radar.panel.export")}</p>
            <Button
              size="sm"
              variant="outline"
              className="w-full"
              onClick={handleExport}
              disabled={exporting}
            >
              {exporting ? t("common.loading") : t("radar.export.download_button")}
            </Button>
            {exportCount != null && (
              <p className="text-xs text-muted-foreground mt-1">
                {t("radar.export.count", { count: exportCount })}
              </p>
            )}
          </section>

          <hr className="border-border" />

          {/* Import */}
          <section>
            <p className="text-sm font-semibold mb-2">{t("radar.panel.import")}</p>
            <input
              ref={fileInputRef}
              type="file"
              accept=".json"
              className="hidden"
              onChange={handleFileChange}
            />
            <div className="space-y-2">
              <Button
                size="sm"
                variant="outline"
                className="w-full"
                onClick={() => fileInputRef.current?.click()}
                disabled={importStocks.isPending}
              >
                {t("radar.import.file_label")}
              </Button>
              <Button
                size="sm"
                variant="ghost"
                className="w-full text-xs"
                onClick={handleDownloadTemplate}
              >
                {t("radar.import.template_button")}
              </Button>
            </div>
            {importFeedback && <p className="text-xs text-destructive mt-1">{importFeedback}</p>}
          </section>
        </div>
      </SheetContent>
    </Sheet>
  )
}
