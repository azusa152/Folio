---
name: folio
description: Self-hosted investment tracking for stocks, portfolio, holdings, FX monitoring, and guru 13F analysis. Use when asked about portfolio status, stock analysis, market sentiment, alerts, FX timing, smart withdrawal, or superinvestor positions. Backend must be running at http://localhost:8000.
homepage: http://localhost:8000/docs
metadata: { "openclaw": { "requires": { "bins": ["docker", "curl"] }, "emoji": "📊" } }
---

# Folio Skill

Use `exec` + `curl` against `http://localhost:8000`.

## Quick Start

```bash
# Discover actions first (recommended)
curl -s -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $FOLIO_API_KEY" \
  -d '{"action":"help"}'

# Portfolio + market overview (recommended starting point)
curl -s -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $FOLIO_API_KEY" \
  -d '{"action":"dashboard"}'

# Token-efficient response (omit most data payloads)
curl -s -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $FOLIO_API_KEY" \
  -d '{"action":"dashboard","format":"concise"}'
```

## Auth + i18n

- If `FOLIO_API_KEY` is set, include `X-API-Key`.
- If unset, dev mode auth is disabled.
- Language keys: `zh-TW` (default), `en`, `ja`, `zh-CN`.
- Errors are localized: always branch on `error_code`, not `detail`.

## Webhook Contract

Endpoint: `POST /webhook`

Request body:
- `action` (required)
- `ticker` (optional, required by some actions)
- `params` (optional object)

Response envelope:
- `success: bool`
- `message: str`
- `interpretation: str` (always present)
- `data: dict` (included by default)

Verbosity (top-level `format` field in request body):
- `"format":"detailed"` (default): includes `data` payload
- `"format":"concise"`: omits `data`, returns only `message` + `interpretation`

## Actions

- `help` - list actions, workflows, and model hints
- `dashboard` - portfolio + market overview (start here)
- `summary` - portfolio health overview
- `analyze {ticker}` - full deep-dive (signals + moat + fundamentals)
- `signals {ticker}` - RSI/MA/Bias analysis
- `moat {ticker}` - gross margin YoY moat analysis
- `alerts {ticker}` - list price alerts
- `add_stock` - add to watchlist (`ticker`, `category`, `thesis`, `tags`)
- `fear_greed` - fear & greed index
- `withdraw` - smart withdrawal (`amount`, `currency`)
- `fx_watch` - FX timing checks + Telegram alerts
- `scan` - trigger background scan
- `guru_sync` - sync all tracked gurus (13F)
- `guru_summary` - send latest guru digest
- `transactions` - list recent transactions (optional `ticker`, `limit`)
- `add_transaction {ticker}` - record buy/sell/dividend/deposit/withdrawal (`type`, `quantity`, `total_amount`, `date`)
- `accounts` - list accounts with holdings count
- `analytics` - risk metrics: Sharpe, Sortino, max drawdown (`start`, `end`)
- `insights` - natural language portfolio insights (`display_currency`)

## Recommended Workflows

- Quick check: `dashboard` -> `analyze {ticker}`
- Buy decision: `analyze {ticker}` -> `fear_greed`
- Need cash: `withdraw {amount, currency}`
- Asset review: `dashboard` -> `analytics` -> `insights` -> `transactions` with `ticker`
- Record trade: `add_transaction {ticker}` -> `transactions` with `ticker` to confirm

## Signal Cheatsheet

- `THESIS_BROKEN`: thesis deterioration, re-evaluate
- `DEEP_VALUE`: high-conviction discount zone
- `OVERSOLD`: deep discount, momentum not fully confirming
- `CONTRARIAN_BUY`: oversold momentum, potential reversal
- `APPROACHING_BUY`: near buy zone
- `OVERHEATED`: elevated risk, avoid chasing
- `CAUTION_HIGH`: one key indicator overheated
- `WEAKENING`: early weakness, monitor closely
- `NORMAL`: no notable signal

If `is_rogue_wave=true`, warn about late-stage surge risk and avoid leveraged chasing.

For health checks, restart, logs, and backup commands, see `docs/agents/TOOLS.md`.
For full endpoint fields, thresholds, and query parameters, load `reference.md`.
