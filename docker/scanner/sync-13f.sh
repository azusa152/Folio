#!/bin/sh
# 13F sync: daily in filing season (Feb/May/Aug/Nov), weekly on Mondays off-season.
# Only triggers /gurus/notify when sync actually produced new data.
BACKEND="http://backend:8000"
MONTH=$(date +%m)
DOW=$(date +%u)

_sync_and_notify() {
  echo "$(date) Starting 13F sync..."
  SYNC_RESULT=$(folio-curl.sh -X POST "$BACKEND/gurus/sync" 2>/dev/null)
  echo "$SYNC_RESULT"
  SYNCED=$(echo "$SYNC_RESULT" | jq -r '.synced // 0' 2>/dev/null)
  if [ "${SYNCED:-0}" -gt 0 ] 2>/dev/null; then
    echo "$(date) $SYNCED guru(s) newly synced — triggering notification..."
    folio-curl.sh -X POST "$BACKEND/gurus/notify" > /dev/null 2>&1
  else
    echo "$(date) No new guru data — skipping notification."
  fi
}

case "$MONTH" in
  02|05|08|11)
    echo "$(date) Filing season (month $MONTH) — triggering 13F sync for all gurus..."
    _sync_and_notify
    ;;
  *)
    if [ "$DOW" = "1" ]; then
      echo "$(date) Off-season Monday — triggering weekly 13F sync for amended filings..."
      _sync_and_notify
    else
      echo "$(date) Off-season (month $MONTH, day $DOW) — skipping 13F sync."
    fi
    ;;
esac
