# Folio — API Reference

Folio's backend exposes a REST API at `http://localhost:8000`. Interactive documentation (Swagger UI) is always available at `http://localhost:8000/docs`.

All endpoints require the `X-API-Key` header when `FOLIO_API_KEY` is set in the environment. In development (unset), authentication is disabled.

---

## Table of Contents

- [Common endpoints](#common-endpoints)
- [Full endpoint reference](#full-endpoint-reference)
- [curl examples](#curl-examples)
- [AI agent integration (OpenClaw / Webhook)](#ai-agent-integration-openclaw--webhook)

---

## Common Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check (used by Docker healthcheck) |
| `POST` | `/ticker` | Add a stock to the watchlist |
| `GET` | `/stocks` | Get all tracked stocks (includes `last_scan_signal`) |
| `GET` | `/stocks/enriched` | Get stocks with technical + fundamentals + dividends |
| `GET` | `/ticker/{ticker}/fundamentals` | P/E, EPS, market cap, P/B, P/S, ROE, growth rates |
| `POST` | `/scan` | Trigger V2 three-layer funnel scan; pushes diff-only notifications |
| `GET` | `/summary` | Plain-text portfolio summary (AI agent friendly) |
| `POST` | `/webhook` | Unified AI agent entrypoint |
| `GET` | `/rebalance` | Rebalance analysis with ETF X-Ray |
| `GET` | `/backtest/summary` | Signal backtest hit-rate, avg return, false-positive rate |
| `GET` | `/snapshots` | Historical portfolio snapshots (`?days=30` or `?start=&end=`) |
| `GET` | `/snapshots/twr` | Time-weighted return (YTD or custom range) |
| `GET` | `/transactions` | Transaction ledger (`?ticker=`, `?limit=`) |
| `POST` | `/transactions` | Record a transaction |
| `GET` | `/accounts` | Account list |
| `GET` | `/wrappers/quota` | NISA/iDeCo quota status |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/openapi.json` | OpenAPI spec (JSON) |

---

## Full Endpoint Reference

<details>
<summary>Stocks and Watchlist</summary>

| Method | Path | Description |
|---|---|---|
| `POST` | `/ticker` | Add a tracked stock (with initial thesis and tags) |
| `GET` | `/stocks` | Get all tracked stocks (DB data, includes `last_scan_signal`) |
| `GET` | `/stocks/enriched` | Get enriched stock data (technical + earnings + dividends + fundamentals summary) |
| `PUT` | `/stocks/reorder` | Batch update display order |
| `GET` | `/stocks/export` | Export all stocks (JSON, includes thesis and tags) |
| `POST` | `/stocks/import` | Batch import stocks (JSON body, upsert logic) |
| `GET` | `/stocks/removed` | Get all removed stocks |
| `GET` | `/ticker/{ticker}/signals` | Technical signals for a stock (yfinance, cached) |
| `GET` | `/ticker/{ticker}/moat` | Moat health check (gross margin 5-quarter trend + YoY diagnosis) |
| `GET` | `/ticker/{ticker}/earnings` | Next earnings date (cached 24 hours) |
| `GET` | `/ticker/{ticker}/dividend` | Dividend yield and ex-dividend date |
| `GET` | `/ticker/{ticker}/fundamentals` | Fundamental metrics (P/E, EPS, market cap, P/B, P/S, ROE, growth rates) |
| `GET` | `/ticker/{ticker}/scan-history` | Per-stock scan history (signal + timestamp) |
| `GET` | `/ticker/{ticker}/price-history` | Price history (for frontend trend chart) |
| `POST` | `/ticker/{ticker}/thesis` | Add thesis (auto-increments version, includes tags) |
| `GET` | `/ticker/{ticker}/thesis` | Get thesis version history |
| `PATCH` | `/ticker/{ticker}/category` | Switch stock category |
| `POST` | `/ticker/{ticker}/deactivate` | Remove from watchlist (with removal reason) |
| `POST` | `/ticker/{ticker}/reactivate` | Reactivate a removed stock (can update category and thesis) |
| `GET` | `/ticker/{ticker}/removals` | Removal history for a stock |
| `POST` | `/ticker/{ticker}/alerts` | Create a price alert (metric / operator / threshold) |
| `GET` | `/ticker/{ticker}/alerts` | Get all price alerts for a stock |
| `DELETE` | `/alerts/{id}` | Delete a price alert |

</details>

<details>
<summary>Scanning and Backtesting</summary>

| Method | Path | Description |
|---|---|---|
| `POST` | `/scan` | V2 three-layer funnel scan (9-level signals, async, diff-only notifications) |
| `GET` | `/scan/last` | Last scan timestamp and market sentiment (used by smart-scan freshness check) |
| `GET` | `/scan/history` | Recent scan records (cross-stock) |
| `GET` | `/market/fear-greed` | Fear & Greed index (VIX + CNN composite, with per-source breakdown) |
| `POST` | `/digest` | Trigger weekly portfolio digest (async, result sent via Telegram) |
| `GET` | `/backtest/summary` | Signal backtest overview (hit rate, avg return, false-positive rate per signal) |
| `GET` | `/backtest/signal/{signal}` | Detailed backtest for a specific signal (event list + forward returns) |
| `GET` | `/backtest/backfill-status` | Cold-start backfill progress (`is_backfilling` / `total` / `completed`) |
| `GET` | `/backtest/export-csv` | Export all backtest events as CSV |

</details>

<details>
<summary>Portfolio and Holdings</summary>

| Method | Path | Description |
|---|---|---|
| `GET` | `/holdings` | All holdings (materialized from transactions) |
| `GET` | `/summary` | Plain-text portfolio summary (total value, day change, top movers, allocation drift, Smart Money) |
| `GET` | `/rebalance` | Rebalance analysis (target vs actual, suggestions, X-Ray); supports `?display_currency=TWD` |
| `POST` | `/rebalance/xray-alert` | Run X-Ray and send Telegram concentration warning |
| `POST` | `/withdraw` | Smart withdrawal suggestion (Liquidity Waterfall); supports `display_currency` and `notify` |
| `GET` | `/stress-test` | Stress test (`scenario_drop_pct`: -50 to 0, `display_currency`) |
| `GET` | `/snapshots` | Historical snapshots; supports `?days=30` (1–730) or `?start=YYYY-MM-DD&end=YYYY-MM-DD`; includes `benchmark_values` |
| `GET` | `/snapshots/twr` | Time-weighted return; supports `?start=&end=`, default YTD |
| `POST` | `/snapshots/take` | Manually trigger today's snapshot (background, upsert semantics) |
| `GET` | `/personas/templates` | Get system investor personality templates |
| `GET` | `/profiles` | Get active portfolio allocation profiles |
| `POST` | `/profiles` | Create a new allocation profile |
| `PUT` | `/profiles/{id}` | Update an allocation profile |
| `DELETE` | `/profiles/{id}` | Deactivate an allocation profile |

</details>

<details>
<summary>Transactions and Accounts</summary>

| Method | Path | Description |
|---|---|---|
| `GET` | `/transactions` | Transaction list (supports `?ticker=`, `?limit=`) |
| `POST` | `/transactions` | Add a transaction (BUY / SELL / DIVIDEND / DEPOSIT / WITHDRAWAL / OPENING_BALANCE / ADJUSTMENT / STOCK_SPLIT / TRANSFER_IN / TRANSFER_OUT) |
| `GET` | `/transactions/{id}` | Get a single transaction |
| `DELETE` | `/transactions/{id}` | Delete a transaction |
| `GET` | `/accounts` | Account list |
| `POST` | `/accounts` | Add an account |
| `PUT` | `/accounts/{id}` | Update an account |
| `DELETE` | `/accounts/{id}` | Deactivate an account |
| `GET` | `/accounts/summary` | Account summary (with per-account holdings count) |
| `GET` | `/accounts/{id}/positions` | Holdings for a specific account |
| `GET` | `/accounts/{id}/transactions` | Transactions for a specific account (paginated) |

</details>

<details>
<summary>Corporate Events (Splits and Dividends)</summary>

| Method | Path | Description |
|---|---|---|
| `POST` | `/stock-splits/check` | Check held stocks for split events (scheduled or manual) |
| `GET` | `/stock-splits/pending` | Get pending split events |
| `POST` | `/stock-splits/{event_id}/apply` | Apply a single split event |
| `POST` | `/stock-splits/{event_id}/dismiss` | Dismiss a single split event |
| `POST` | `/stock-splits/apply-all` | Apply all pending split events |
| `POST` | `/dividends/check` | Check held stocks for dividend events |
| `GET` | `/dividends/pending` | Get pending dividend events |
| `POST` | `/dividends/{event_id}/apply` | Apply a single dividend event |
| `POST` | `/dividends/{event_id}/dismiss` | Dismiss a single dividend event |
| `POST` | `/dividends/apply-all` | Apply all pending dividend events |

</details>

<details>
<summary>Crypto</summary>

| Method | Path | Description |
|---|---|---|
| `GET` | `/crypto/search?q=bitcoin` | Search for a cryptocurrency (returns `id/symbol/name/thumb/ticker`) |
| `GET` | `/crypto/price/{ticker}` | Get crypto price (CoinGecko primary, yfinance fallback); supports `?coingecko_id=` |

</details>

<details>
<summary>FX Watch</summary>

| Method | Path | Description |
|---|---|---|
| `GET` | `/fx-watch` | Get all FX monitoring configs; supports `?active_only=true` |
| `POST` | `/fx-watch` | Add FX monitoring config |
| `PATCH` | `/fx-watch/{id}` | Update FX monitoring config (partial update) |
| `DELETE` | `/fx-watch/{id}` | Delete FX monitoring config |
| `POST` | `/fx-watch/check` | Check all FX monitors (analyze, no Telegram) |
| `POST` | `/fx-watch/alert` | Check and send Telegram alerts (with cooldown) |

</details>

<details>
<summary>Tax Wrappers (NISA / iDeCo)</summary>

| Method | Path | Description |
|---|---|---|
| `GET` | `/wrappers/quota` | NISA/iDeCo quota status (annual / lifetime / growth sub-limit) |
| `GET` | `/wrappers/restoration-forecast` | NISA quota restoration forecast (pending restoration items) |
| `GET` | `/wrappers/contributions` | NISA contribution ledger (supports `?wrapper=nisa_tsumitate\|nisa_growth`, `?year=`, `?limit=`) |
| `GET` | `/wrappers/{wrapper}/check-eligibility` | Asset eligibility check (with alternative account suggestions) |
| `GET` | `/wrappers/{wrapper}/eligible-assets` | Eligible asset list (supports search/filter) |
| `POST` | `/wrappers/suggest-routing` | Smart purchase routing (NISA-first allocation) |
| `GET` | `/wrappers/detax` | DeTAX opportunities (losing positions in specific accounts) |

</details>

<details>
<summary>Analytics</summary>

| Method | Path | Description |
|---|---|---|
| `GET` | `/analytics/drawdown` | Drawdown time series |
| `GET` | `/analytics/risk-metrics` | Risk metrics (Sharpe, Sortino, max drawdown, annualized volatility) |
| `GET` | `/analytics/contribution-growth` | Cumulative contributions vs market appreciation |
| `GET` | `/analytics/insights` | Natural language portfolio insights |

</details>

<details>
<summary>Smart Money (Gurus / 13F)</summary>

| Method | Path | Description |
|---|---|---|
| `GET` | `/gurus` | All tracked gurus |
| `POST` | `/gurus` | Add a custom guru (name / cik / display_name) |
| `DELETE` | `/gurus/{guru_id}` | Deactivate a guru |
| `POST` | `/gurus/sync` | Sync all gurus' 13F filings (SEC EDGAR, with mutex) |
| `POST` | `/gurus/{guru_id}/sync` | Sync a single guru's 13F |
| `GET` | `/gurus/{guru_id}/filing` | Latest 13F filing summary (report date / filing date / total value / holdings count) |
| `GET` | `/gurus/{guru_id}/filings` | All 13F filing records for a guru |
| `GET` | `/gurus/{guru_id}/holdings` | All holdings with action labels (NEW / SOLD / INCREASED / DECREASED / UNCHANGED); add `?include_performance=true` for post-filing return |
| `GET` | `/gurus/{guru_id}/top` | Top-N holdings by weight (default N=10); supports `?include_performance=true` |
| `GET` | `/gurus/{guru_id}/qoq` | Cross-quarter holdings history (default 3 quarters); supports `?quarters=N`; includes trend column |
| `GET` | `/gurus/grand-portfolio` | Aggregated view across all tracked gurus — combined weight, avg weight, dominant action, sector breakdown |
| `GET` | `/gurus/heatmap` | 13F heatmap data (cross-guru aggregate; includes 45-day delay notice) |
| `GET` | `/gurus/{guru_id}/backtest` | Guru copy backtest (quarterly returns + cumulative + Alpha); supports `?quarters=2..12&benchmark=SPY\|VT` |
| `GET` | `/resonance` | Portfolio resonance overview (all gurus vs watchlist/holdings overlap) |
| `GET` | `/resonance/{ticker}` | Guru holdings for a specific ticker |

</details>

<details>
<summary>Settings and Admin</summary>

| Method | Path | Description |
|---|---|---|
| `GET` | `/settings/telegram` | Get Telegram notification settings (token masked) |
| `PUT` | `/settings/telegram` | Update Telegram notification settings (supports custom bot) |
| `POST` | `/settings/telegram/test` | Send a Telegram test message |
| `GET` | `/settings/preferences` | Get user preferences (privacy mode, etc.) |
| `PUT` | `/settings/preferences` | Update user preferences (upsert) |
| `POST` | `/admin/cache/clear` | Clear all backend caches (L1 memory + L2 disk) |

</details>

---

## curl Examples

<details>
<summary>Watchlist management</summary>

```bash
# Add a stock with tags
curl -X POST http://localhost:8000/ticker \
  -H "Content-Type: application/json" \
  -d '{"ticker": "NVDA", "category": "Moat", "thesis": "Shovel-seller for AI giants.", "tags": ["AI", "Semiconductor"]}'

# Update thesis with new tags
curl -X POST http://localhost:8000/ticker/NVDA/thesis \
  -H "Content-Type: application/json" \
  -d '{"content": "GB200 demand exceeding expectations — raised target.", "tags": ["AI", "Semiconductor", "Hardware"]}'

# Reactivate a removed stock
curl -X POST http://localhost:8000/ticker/ZM/reactivate \
  -H "Content-Type: application/json" \
  -d '{"category": "Growth", "thesis": "Re-evaluating streaming communication opportunity."}'

# Batch import stocks
curl -X POST http://localhost:8000/stocks/import \
  -H "Content-Type: application/json" \
  -d '[{"ticker":"AAPL","category":"Moat","thesis":"Brand moat","tags":["Hardware"]}]'

# Set a price alert (notify when NVDA RSI drops below 30)
curl -X POST http://localhost:8000/ticker/NVDA/alerts \
  -H "Content-Type: application/json" \
  -d '{"metric": "rsi", "operator": "lt", "threshold": 30}'

# Get fundamentals
curl -s http://localhost:8000/ticker/NVDA/fundamentals | python3 -m json.tool
```

</details>

<details>
<summary>Portfolio and rebalance</summary>

```bash
# Add a transaction (record a purchase)
curl -X POST http://localhost:8000/transactions \
  -H "Content-Type: application/json" \
  -d '{"account_id": 1, "ticker": "NVDA", "type": "BUY", "quantity": 10, "total_amount": 1200, "date": "2026-03-15"}'

# Set opening balance for a new account
curl -X POST http://localhost:8000/transactions \
  -H "Content-Type: application/json" \
  -d '{"account_id": 1, "ticker": "NVDA", "type": "OPENING_BALANCE", "quantity": 50, "total_amount": 6000, "date": "2026-03-12"}'

# Rebalance in USD (default)
curl -s http://localhost:8000/rebalance | python3 -m json.tool

# Rebalance in TWD
curl -s "http://localhost:8000/rebalance?display_currency=TWD" | python3 -m json.tool

# X-Ray: show ETF penetration (top 10 exposures)
curl -s http://localhost:8000/rebalance | python3 -c "
import json, sys
data = json.load(sys.stdin)
for e in data.get('xray', [])[:10]:
    print(f\"{e['symbol']:6s} direct:{e['direct_weight_pct']:5.1f}% indirect:{e['indirect_weight_pct']:5.1f}% total:{e['total_weight_pct']:5.1f}%\")
"

# Send X-Ray Telegram alert for positions exceeding 15% threshold
curl -s -X POST "http://localhost:8000/rebalance/xray-alert?display_currency=USD"

# Smart withdrawal: "I need 50,000 TWD — what should I sell?"
curl -s -X POST http://localhost:8000/withdraw \
  -H "Content-Type: application/json" \
  -d '{"target_amount": 50000, "display_currency": "TWD", "notify": true}' | python3 -m json.tool

# Create a portfolio profile from an investor personality template
curl -s http://localhost:8000/personas/templates | python3 -m json.tool
curl -X POST http://localhost:8000/profiles \
  -H "Content-Type: application/json" \
  -d '{"name": "Balanced", "source_template_id": "balanced", "config": {"Trend_Setter": 25, "Moat": 30, "Growth": 15, "Bond": 20, "Cash": 10}}'
```

</details>

<details>
<summary>Scan and signals</summary>

```bash
# Trigger a full scan
curl -X POST http://localhost:8000/scan

# Get plain-text summary (good for AI agent chat responses)
curl -s http://localhost:8000/summary

# Get backtest summary
curl -s http://localhost:8000/backtest/summary | python3 -m json.tool

# Check cold-start backfill progress
curl -s http://localhost:8000/backtest/backfill-status | python3 -m json.tool
```

</details>

<details>
<summary>Settings and admin</summary>

```bash
# Configure a custom Telegram bot
curl -X PUT http://localhost:8000/settings/telegram \
  -H "Content-Type: application/json" \
  -d '{"telegram_chat_id": "123456789", "custom_bot_token": "YOUR_BOT_TOKEN", "use_custom_bot": true}'

# Send a test Telegram message
curl -X POST http://localhost:8000/settings/telegram/test

# Clear all backend caches (L1 memory + L2 disk)
curl -X POST http://localhost:8000/admin/cache/clear
# => {"status":"ok","l1_cleared":10,"l2_cleared":true}
```

</details>

---

## AI Agent Integration (OpenClaw / Webhook)

Folio exposes a unified webhook entrypoint at `POST /webhook` designed for AI agents. Start with action discovery:

```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"action": "help"}'
```

### Webhook request format

```json
{
  "action": "analyze",
  "ticker": "NVDA",
  "params": {},
  "format": "detailed"
}
```

Set `"format": "concise"` to reduce token usage — most actions omit the `data` field in concise mode.

### Response format

```json
{
  "success": true,
  "message": "...",
  "interpretation": "...",
  "data": {}
}
```

Branch on `error_code` (machine-readable), not `detail` (localized text).

### Available webhook actions

| Action | Description | Requires `ticker` |
|---|---|:---:|
| `help` | List all actions, workflows, and model hints | No |
| `dashboard` | Portfolio summary + market sentiment (Fear & Greed) | No |
| `summary` | Portfolio health summary | No |
| `analyze` | Single stock integrated analysis (signals + moat + fundamentals) | Yes |
| `signals` | Single stock technical indicators | Yes |
| `scan` | Trigger a full global scan | No |
| `moat` | Moat health analysis for a stock | Yes |
| `alerts` | View price alerts for a stock | Yes |
| `add_stock` | Add a stock to the watchlist | Yes (in `params`) |
| `stock_splits` | Check held positions for split events; return summary | No |
| `dividends` | Check held positions for dividend events; return summary | No |
| `drift_alerts` | Check portfolio drift and return alert summary | No |
| `transactions` | View recent transactions (optional `ticker`, `limit` in `params`) | No |
| `add_transaction` | Record a transaction (BUY/SELL/DIVIDEND/DEPOSIT/WITHDRAWAL/OPENING_BALANCE/ADJUSTMENT/STOCK_SPLIT/TRANSFER_IN/TRANSFER_OUT) | Yes |
| `accounts` | List accounts and their holdings count | No |
| `analytics` | Risk metrics: Sharpe, Sortino, max drawdown | No |
| `insights` | Natural language portfolio insights | No |
| `quota` | NISA/iDeCo quota status | No |

### OpenClaw setup

[OpenClaw](https://docs.openclaw.ai/) is an open-source AI agent gateway that connects Folio to WhatsApp, Telegram, Discord, and other messaging platforms.

```bash
npm install -g openclaw@latest
openclaw onboard
```

**Option A — Skill file:**

```bash
cp -r docs/agents/folio/ ~/.openclaw/skills/folio/
```

**Option B — AGENTS.md:**

```bash
cp docs/agents/AGENTS.md ~/.openclaw/workspace/AGENTS.md
```

For compact action usage, refer to [`docs/agents/folio/SKILL.md`](agents/folio/SKILL.md). For detailed field-level specs and thresholds, refer to [`docs/agents/folio/reference.md`](agents/folio/reference.md).

### Example conversations

| You say... | Agent executes... |
|---|---|
| "How is my portfolio?" | `POST /webhook {"action":"dashboard"}` |
| "Quick analysis of NVDA (save tokens)" | `POST /webhook {"action":"analyze","ticker":"NVDA","format":"concise"}` |
| "Run a full scan" | `POST /webhook {"action":"scan"}` |
| "Add AMD to Moat category" | `POST /webhook {"action":"add_stock","params":{"ticker":"AMD","category":"Moat","thesis":"..."}}` |
| "What's my NISA quota?" | `POST /webhook {"action":"quota"}` |
| "I bought 10 shares of TSLA at $250" | `POST /webhook {"action":"add_transaction","ticker":"TSLA","params":{"type":"BUY","quantity":10,"total_amount":2500}}` |

### Smart withdrawal via webhook

```bash
curl -s -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"action": "withdraw", "params": {"amount": 50000, "currency": "TWD"}}'
```
