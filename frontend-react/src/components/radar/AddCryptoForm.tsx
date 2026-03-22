import { useTranslation } from "react-i18next"
import { Button } from "@/components/ui/button"

interface CoinSearchResult {
  id: string
  symbol: string
  name: string
  ticker: string
}

interface Props {
  ticker: string
  thesis: string
  cryptoQuery: string
  searchResults: CoinSearchResult[] | undefined
  isPending: boolean
  onQueryChange: (query: string) => void
  onSelectCoin: (ticker: string, coinId: string, displayQuery: string) => void
  onThesisChange: (thesis: string) => void
  onSubmit: () => void
}

export function AddCryptoForm({
  ticker,
  thesis,
  cryptoQuery,
  searchResults,
  isPending,
  onQueryChange,
  onSelectCoin,
  onThesisChange,
  onSubmit,
}: Props) {
  const { t } = useTranslation()

  return (
    <div className="space-y-2">
      <div>
        <label htmlFor="add-crypto-search" className="text-xs text-muted-foreground">
          {t("radar.form.crypto_search")}
        </label>
        <input
          id="add-crypto-search"
          className="mt-0.5 w-full rounded-md border border-input bg-background px-2 py-1 text-sm"
          placeholder={t("radar.form.crypto_search_placeholder")}
          value={cryptoQuery}
          onChange={(e) => onQueryChange(e.target.value)}
        />
      </div>

      {searchResults && searchResults.length > 0 && (
        <div className="max-h-36 overflow-y-auto rounded border border-border p-1 space-y-1">
          {searchResults.map((coin) => (
            <button
              type="button"
              key={`${coin.id}-${coin.symbol}`}
              className="w-full text-left text-xs px-2 py-1 rounded hover:bg-muted/40"
              onClick={() => onSelectCoin(coin.ticker, coin.id, `${coin.name} (${coin.symbol})`)}
            >
              {coin.name} ({coin.symbol}) - {coin.ticker}
            </button>
          ))}
        </div>
      )}

      <div>
        <label htmlFor="add-crypto-ticker" className="text-xs text-muted-foreground">
          {t("radar.form.ticker")}
        </label>
        <input
          id="add-crypto-ticker"
          className="mt-0.5 w-full rounded-md border border-input bg-muted/40 px-2 py-1 text-sm"
          value={ticker}
          readOnly
        />
      </div>

      <div>
        <label htmlFor="add-crypto-thesis" className="text-xs text-muted-foreground">
          {t("radar.form.thesis")}
        </label>
        <textarea
          id="add-crypto-thesis"
          className="mt-0.5 w-full rounded-md border border-input bg-background p-2 text-sm resize-none"
          rows={3}
          placeholder={t("radar.form.thesis_placeholder")}
          value={thesis}
          onChange={(e) => onThesisChange(e.target.value)}
        />
      </div>

      <Button size="sm" className="w-full" onClick={onSubmit} disabled={isPending}>
        {t("radar.form.add_button")}
      </Button>
      <p className="text-[11px] text-muted-foreground">{t("allocation.crypto.market_24h")}</p>
    </div>
  )
}
