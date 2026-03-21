# Runbook: Scanner Troubleshooting

## Overview

The scanner (`scanner` Docker service) periodically calls the Folio backend
to refresh market signals for all tracked stocks. It runs as an Alpine container
executing `docker/scanner/entrypoint.sh` on a cron-like schedule.

---

## Check scanner status

```bash
# View live scanner logs
docker compose logs -f scanner

# Check prewarm status (authenticated endpoint)
curl -H "X-API-Key: $FOLIO_API_KEY" http://localhost:8000/prewarm-status

# Check backend health
curl http://localhost:8000/health
```

---

## Scanner not running / stale signals

**Symptom:** Stocks show stale scan timestamps; `docker compose ps` shows
`scanner` exited or restarting.

**Steps:**

1. Check logs for the error:
   ```bash
   docker compose logs scanner | tail -50
   ```

2. Confirm the backend is healthy:
   ```bash
   docker compose ps
   # backend should show "healthy"
   ```

3. If backend is unhealthy, restart it:
   ```bash
   make restart
   # Wait for healthy, then scanner will reconnect
   ```

4. If scanner exited cleanly but signals are stale, check the stale window
   settings in `.env`:
   ```
   SCAN_STALE_SECONDS_MARKET_HOURS=900   # 15 min during market hours
   SCAN_STALE_SECONDS_OFF_HOURS=3600     # 1 hour off-hours
   ```
   Signals are only considered stale after these windows, so "stale" is
   expected on weekends and public holidays.

5. Force a manual scan via the API:
   ```bash
   curl -X POST -H "X-API-Key: $FOLIO_API_KEY" http://localhost:8000/api/scan/run
   ```

---

## Prewarm failures

**Symptom:** `/prewarm-status` returns `{"status": "pending"}` for a long time
after startup.

**Steps:**

1. Check backend logs for yfinance errors:
   ```bash
   make logs | grep -i "prewarm\|yfinance\|error"
   ```

2. yfinance occasionally has rate-limit or network hiccups. The prewarm runs
   in a background daemon thread; wait 2–5 minutes and re-check.

3. If a specific ticker is consistently failing:
   - Check if the ticker is still valid on Yahoo Finance.
   - Consider removing or marking it inactive via the Folio UI.

---

## High API error rate from yfinance

**Symptom:** Scan logs show repeated `curl_cffi` SSL errors or `429 Too Many Requests`.

**Steps:**

1. Check `LOG_LEVEL=DEBUG` for detailed yfinance request logs.
2. Reduce the number of tracked stocks or increase scan stale windows.
3. The `curl_cffi` version is pinned at `<0.8` due to a BoringSSL TLS bug on
   Linux (see `backend/pyproject.toml`). Updating past `0.8` may resolve or
   introduce new network issues — see ADR for context.

---

## Telegram notifications not sending

**Symptom:** Scans complete but no Telegram messages arrive.

**Steps:**

1. Verify Telegram settings in the Folio UI (Settings → Telegram).
2. Check backend logs for `telegram` errors:
   ```bash
   make logs | grep -i telegram
   ```
3. Confirm `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are set in `.env`
   (or configured via the UI custom bot feature).
4. Test the bot directly:
   ```bash
   curl "https://api.telegram.org/bot<TOKEN>/sendMessage?chat_id=<CHAT_ID>&text=test"
   ```
