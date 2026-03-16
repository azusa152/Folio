---
name: folio
description: Self-hosted investment tracking for stocks, portfolio, ledger-driven positions, FX monitoring, guru 13F analysis, and Japanese tax-advantaged accounts (NISA/iDeCo). Use when asked about portfolio status, stock analysis, market sentiment, alerts, FX timing, smart withdrawal, NISA quota, tax optimization, or superinvestor positions. Backend must be running at http://localhost:8000.
homepage: http://localhost:8000/docs
metadata: { "openclaw": { "requires": { "bins": ["docker", "curl"] }, "primaryEnv": "FOLIO_API_KEY", "emoji": "📊" } }
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
- `error_code: str | null` (present on structured failures)
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
- `transactions` - list recent transactions (optional `ticker`, `account_id`, `start`, `end`, `limit`)
- `add_transaction {ticker}` - record transactions (`type`: BUY/SELL/DIVIDEND/DEPOSIT/WITHDRAWAL/OPENING_BALANCE/ADJUSTMENT/TRANSFER_IN/TRANSFER_OUT, required `account_id`, `quantity`, `total_amount`, `date`)
- `accounts` - list accounts with holdings count
- `analytics` - risk metrics: Sharpe, Sortino, max drawdown (`start`, `end`)
- `insights` - natural language portfolio insights (`display_currency`)
- `quota` - NISA/iDeCo quota status (annual/lifetime remaining, restoration forecast)

## Recommended Workflows

- Quick check: `dashboard` -> `analyze {ticker}`
- Buy decision: `analyze {ticker}` -> `fear_greed`
- Need cash: `withdraw {amount, currency}`
- Asset review: `dashboard` -> `analytics` -> `insights` -> `transactions` with `ticker`
- Record trade: `add_transaction {ticker}` -> `transactions` with `ticker` to confirm (BUY/SELL auto-settle both cash and stock positions)
- NISA check: `quota` -> `dashboard` (review quota then allocation)
- Tax optimization: `quota` -> `insights` -> review DeTAX suggestions in dashboard

All position mutations now go through the transaction API; holdings are a derived position cache.

## Signal Cheatsheet

- `THESIS_BROKEN` (Business Declining): thesis deterioration, re-evaluate
- `DEEP_VALUE` (Priced Very Low): high-conviction discount zone
- `OVERSOLD` (Sharp Drop): deep discount, momentum not fully confirming
- `CONTRARIAN_BUY` (Possible Bounce): oversold momentum, potential reversal
- `APPROACHING_BUY` (Near Buy Zone): near buy zone
- `OVERHEATED` (Price Too Hot): elevated risk, avoid chasing
- `CAUTION_HIGH` (Be Cautious): one key indicator overheated
- `WEAKENING` (Losing Steam): early weakness, monitor closely
- `NORMAL`: no notable signal

If `is_rogue_wave=true`, warn about late-stage surge risk and avoid leveraged chasing.

## OpenClaw Integration

- Cron check-in: schedule a daily `dashboard` run, then follow with `analytics` and `insights` for portfolio health.
- Trade confirmation loop: `add_transaction {ticker}` then `transactions` with `ticker` to confirm the new entry.
- Trigger scans from automation: use `scan` and follow with `dashboard` to summarize results.
- Use concise mode for chat channels with tight context windows: add `"format":"concise"` to webhook payloads.
- Keep agent logic deterministic: call `help` first and branch on `success` + `error_code` in responses.

For health checks, restart, logs, and backup commands, see `docs/agents/TOOLS.md`.
For full endpoint fields, thresholds, and query parameters, load `reference.md`.
