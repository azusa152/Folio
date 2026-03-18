#!/bin/sh
# Market-hours aware scanner: triggers scan only when stale.
# During extended US market hours we scan every 15 minutes.
# During off-hours/weekends we keep scanning with a relaxed cadence.
# Source environment for cron context (Alpine crond doesn't inherit env).
[ -f /etc/folio.env ] && . /etc/folio.env

BACKEND="http://backend:8000"
MARKET_HOURS_STALE_SECONDS="${SCAN_STALE_SECONDS_MARKET_HOURS:-900}"
OFF_HOURS_STALE_SECONDS="${SCAN_STALE_SECONDS_OFF_HOURS:-3600}"

# Two-tier staleness threshold:
# - Market hours (Mon-Fri 13:00-22:00 UTC): 15 minutes
# - Off-hours/weekends: 60 minutes
DOW=$(date +%u)   # 1=Mon ... 7=Sun
HOUR=$(date -u +%H)  # UTC hour (0-23)
if [ "$DOW" -lt 6 ] && [ "$HOUR" -ge 13 ] && [ "$HOUR" -lt 22 ]; then
  STALE_SECONDS="$MARKET_HOURS_STALE_SECONDS"
else
  STALE_SECONDS="$OFF_HOURS_STALE_SECONDS"
fi

last_epoch=$(folio-curl.sh "$BACKEND/scan/last" | jq -r '.epoch // empty')
if [ -z "$last_epoch" ]; then
  echo "$(date) No previous scan found, triggering scan..."
  folio-curl.sh -X POST "$BACKEND/scan" > /dev/null 2>&1
  exit 0
fi

now_epoch=$(date +%s)
age=$(( now_epoch - last_epoch ))

if [ "$age" -ge "$STALE_SECONDS" ]; then
  echo "$(date) Last scan was ${age}s ago (>= ${STALE_SECONDS}s), triggering scan..."
  folio-curl.sh -X POST "$BACKEND/scan" > /dev/null 2>&1
else
  echo "$(date) Last scan was ${age}s ago (< ${STALE_SECONDS}s), skipping."
fi
