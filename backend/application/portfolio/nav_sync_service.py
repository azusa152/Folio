"""Background sync for mutual fund NAV data from toushin-lib.

Follows the same daemon-thread pattern as ``eligible_sync_service``.  On each
cycle the service fetches the latest CSV from the Investment Trust Association
for every active ``Mutual_Fund`` stock on the radar, then upserts the results
into the ``MutualFundNav`` table.
"""

from __future__ import annotations

import threading
import time

from sqlmodel import Session

from config import settings
from domain.enums import StockCategory
from infrastructure import repositories as repo
from infrastructure.database import engine
from infrastructure.market_data.toushin_adapter import fetch_fund_nav_csv
from logging_config import get_logger

logger = get_logger(__name__)

_sync_started = False
_sync_lock = threading.Lock()


def _annotate_previous_nav(rows: list[dict]) -> list[dict]:
    """Add ``nav_previous`` to each row based on the next (older) row."""
    for i, row in enumerate(rows):
        row["nav_previous"] = rows[i + 1]["nav"] if i + 1 < len(rows) else None
    return rows


def sync_mutual_fund_navs() -> dict[str, int]:
    """One-shot sync: fetch NAV for all active Mutual_Fund stocks."""
    with Session(engine) as session:
        stocks = repo.find_active_stocks(session)
        mf_stocks = [s for s in stocks if s.category == StockCategory.MUTUAL_FUND]

        if not mf_stocks:
            logger.debug("NAV sync: no active Mutual_Fund stocks on radar.")
            return {"synced": 0, "failed": 0}

        synced = 0
        failed = 0

        for stock in mf_stocks:
            isin = repo.find_isin_for_ticker(session, stock.ticker)
            if not isin:
                logger.debug("NAV sync: no ISIN found for %s, skipping.", stock.ticker)
                failed += 1
                continue

            csv_rows = fetch_fund_nav_csv(stock.ticker, isin)
            if not csv_rows:
                failed += 1
                continue

            annotated = _annotate_previous_nav(csv_rows)
            count = repo.bulk_upsert_nav(
                session,
                stock.ticker,
                isin,
                annotated,
                autocommit=True,
            )
            synced += 1
            logger.info("NAV sync: %s — %d rows upserted.", stock.ticker, count)

    return {"synced": synced, "failed": failed}


def _nav_sync_loop() -> None:
    interval_hours = max(settings.NAV_SYNC_INTERVAL_HOURS, 0)
    if interval_hours <= 0:
        logger.info("NAV periodic sync disabled (interval=%d).", interval_hours)
        return
    interval_seconds = interval_hours * 3600
    logger.info("NAV periodic sync started (every %d hour(s)).", interval_hours)

    # Initial sync at startup
    try:
        result = sync_mutual_fund_navs()
        logger.info("NAV initial sync completed: %s", result)
    except Exception as exc:
        logger.warning("NAV initial sync failed: %s", exc)

    while True:
        time.sleep(interval_seconds)
        try:
            result = sync_mutual_fund_navs()
            logger.info("NAV periodic sync succeeded: %s", result)
        except Exception as exc:
            logger.warning("NAV periodic sync failed: %s", exc)


def start_nav_sync_loop() -> None:
    """Ensure only one background NAV sync loop is running."""
    global _sync_started
    with _sync_lock:
        if _sync_started:
            return
        _sync_started = True
    threading.Thread(target=_nav_sync_loop, daemon=True).start()
