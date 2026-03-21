# Folio — Self-Hosted Investment Tracker

[![CI](https://github.com/azusa152/azusa-stock/actions/workflows/ci.yml/badge.svg)](https://github.com/azusa152/azusa-stock/actions/workflows/ci.yml)
![Coverage](https://raw.githubusercontent.com/azusa152/azusa-stock/python-coverage-comment-action-data/badge.svg)

> Not a stock picker — a discipline machine. Record your thesis, track signals, get alerted, and stop making decisions on gut feel.

Folio is a self-hosted, Dockerized investment analysis system for disciplined investors. Manage a categorized watchlist, run a multi-layer signal scanner, monitor portfolio allocation, and receive Telegram notifications — all from a single lightweight Docker Compose stack.

---

## Highlights

**Watchlist & Signals**
- Categorize stocks across five buckets (Trend Setter / Moat / Growth / Bond / Cash)
- V2 three-layer funnel scanner: market sentiment → moat health → 9-level technical signal
- Persistent scan history, backtest hit-rate dashboard, and cold-start backfill
- Rogue Wave detection (deviation ≥ P95 + volume × 1.5x)

**Portfolio (War Room)**
- Ledger-driven positions — all holdings derived from transaction records
- Rebalance drift analysis, stress test (CAPM Beta), smart withdrawal (Liquidity Waterfall)
- ETF X-Ray: penetrate ETF holdings to compute true exposure
- FX exposure monitoring with Telegram alerts
- Japan tax accounts: NISA (Tsumitate / Growth) and iDeCo quota tracking, DeTAX optimizer

**Smart Money**
- SEC 13F tracker — sync any institutional investor by CIK
- Guru consensus, QoQ holdings diff, grand portfolio heatmap, and backtest vs SPY/VT
- "Great Minds Think Alike" — auto-match your watchlist against all tracked gurus

**Notifications**
- Telegram alerts: price alerts, weekly digest, drift reminders, FX alerts, stock splits, dividends
- Dual-mode: system `.env` bot or per-user custom bot token

**Interface**
- 8-page SPA: Dashboard, Radar, Backtest, War Room, NISA Center, FX Watch, Smart Money, Settings
- Multi-language: Traditional Chinese, English, 日本語, Simplified Chinese
- PWA — installable on desktop, Android, and iOS
- Privacy mode, drag-and-drop ordering, dark/light theme

---

## Quick Start

**Prerequisite:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.

### 1. Configure environment

Copy `.env.example` to `.env` and fill in your Telegram credentials (optional — skip to disable notifications):

```bash
cp .env.example .env
```

```env
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-telegram-chat-id
```

Set an API key to protect the API in production (leave unset to disable auth in dev):

```env
FOLIO_API_KEY=your-api-key   # generate one with: make generate-key
```

### 2. Start

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend Dashboard | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |

### 3. Import your watchlist (optional)

Upload a JSON file via the Dashboard sidebar, or use the CLI:

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install requests
python scripts/import_stocks.py            # load the default sample watchlist
python scripts/import_stocks.py my.json   # load your own
```

That's it — the scanner runs automatically and will push Telegram notifications on signal changes.

---

## Configuration

### Key environment variables

| Variable | Default | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | — | Telegram bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | — | Your Telegram chat/group ID |
| `FOLIO_API_KEY` | _(unset = dev mode)_ | API key for `X-API-Key` header auth |
| `FERNET_KEY` | _(unset = plaintext)_ | Fernet key for encrypting stored bot tokens |
| `COINGECKO_API_KEY` | — | CoinGecko Pro key (optional, higher rate limits) |
| `SCAN_STALE_SECONDS_MARKET_HOURS` | `900` | Scanner freshness threshold during market hours |
| `SCAN_STALE_SECONDS_OFF_HOURS` | `3600` | Scanner freshness threshold off-hours |
| `NAV_SYNC_INTERVAL_HOURS` | `24` | Mutual fund NAV sync interval |
| `LOG_LEVEL` | `INFO` | Log verbosity (`DEBUG` / `INFO` / `WARNING`) |
| `LOG_FORMAT` | `text` | `text` (human-readable) or `json` (for ELK/Loki) |

See `.env.example` for the full list.

### Language (i18n)

| Language | Code |
|---|---|
| Traditional Chinese | `zh-TW` (default) |
| English | `en` |
| 日本語 | `ja` |
| Simplified Chinese | `zh-CN` |

Switch at any time from the sidebar — the setting persists across devices.

---

## Documentation

| Document | Audience | Contents |
|---|---|---|
| [docs/USER_GUIDE.md](docs/USER_GUIDE.md) | End users | Features, scanning logic, import guides, Telegram setup, PWA, data management |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Contributors | Setup, CI, testing, architecture, logging, security |
| [docs/API.md](docs/API.md) | Developers / AI agents | Full API reference, curl examples, OpenClaw integration |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contributors | Branch/commit conventions, PR workflow |
| [docs/agents/folio/SKILL.md](docs/agents/folio/SKILL.md) | AI agents | Compact webhook action reference |
| [docs/agents/folio/reference.md](docs/agents/folio/reference.md) | AI agents | Detailed field specs and thresholds |

---

## For Developers

```bash
# First-time setup (install deps, codegen, pre-commit hooks)
make setup

# Start everything locally
docker compose up -d

# Full CI check — mirrors all GitHub Actions jobs
make ci

# Faster iteration loop
make ci-quick          # lint + tests only
make backend-test-quick
```

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for the complete guide covering Python version pinning, dependency management (uv), API type codegen, architecture boundaries, test coverage ratchet, and logging configuration.

See [CONTRIBUTING.md](CONTRIBUTING.md) for branch naming, commit format, and PR workflow.

---

## Stack

- **Backend** — FastAPI + SQLModel (Clean Architecture: domain → application → infrastructure → api)
- **Frontend** — React 18 + Vite + TypeScript + shadcn/ui + Tailwind CSS
- **Database** — SQLite (persisted via Docker volume)
- **Market data** — yfinance with multi-layer caching, rate limiting, and auto-retry
- **Notifications** — Telegram Bot API (dual-mode)
- **Deployment** — Docker Compose (Backend + Frontend + Alpine cron scanner)

---

## License

MIT
