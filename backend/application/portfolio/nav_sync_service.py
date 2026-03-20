"""Background sync for mutual fund NAV data from toushin-lib.

Follows the same daemon-thread pattern as ``eligible_sync_service``.  On each
cycle the service fetches the latest CSV from the Investment Trust Association
for every active ``Mutual_Fund`` stock on the radar, then upserts the results
into the ``MutualFundNav`` table.
"""

from __future__ import annotations

import re
import threading
import time

from sqlmodel import Session

from domain.enums import StockCategory
from infrastructure import repositories as repo
from infrastructure.common import config as settings
from infrastructure.database import engine
from infrastructure.market_data.toushin_adapter import fetch_fund_nav_csv
from infrastructure.market_data.toushin_lib_adapter import (
    lookup_isin,
    resolve_fund_code_from_name,
)
from logging_config import get_logger

logger = get_logger(__name__)

_sync_started = False
_sync_lock = threading.Lock()


_NAV_FAIL_MISSING_ISIN = "missing_isin"
_NAV_FAIL_DOWNLOAD_ERROR = "download_error"
_NAV_FAIL_EMPTY_CSV = "empty_csv"
_NAV_FAIL_UPSERT_ERROR = "upsert_error"


def _annotate_previous_nav(rows: list[dict]) -> list[dict]:
    """Add ``nav_previous`` to each row based on the next (older) row."""
    for i, row in enumerate(rows):
        row["nav_previous"] = rows[i + 1]["nav"] if i + 1 < len(rows) else None
    return rows


_FUND_CODE_RE = re.compile(r"^[0-9A-Z]{8}$", re.IGNORECASE)


def _is_fund_code(ticker: str) -> bool:
    return bool(_FUND_CODE_RE.match(ticker.strip()))


def _resolve_isin_fallback(session: Session, ticker: str) -> tuple[str, str] | None:
    """Try the toushin-lib search API when the local DB has no ISIN.

    Handles two cases:
    1. Normal fund code (e.g. ``01311143``) — look up ISIN directly.
    2. Legacy fund-name ticker (e.g. ``EMAXIS S&P500インデックス``) — first
       resolve the name to a fund code, then look up the ISIN.

    Returns ``(fund_code, isin)`` on success, ``None`` on failure.
    When resolved, the ISIN is back-filled into the EligibleAsset table.
    """
    fund_code = ticker
    if not _is_fund_code(ticker):
        try:
            resolved = resolve_fund_code_from_name(ticker)
        except Exception:
            resolved = None
        if not resolved:
            logger.warning(
                "ISIN fallback: ticker '%s' is not a fund code and "
                "could not be resolved from fund name.",
                ticker,
            )
            return None
        logger.info(
            "ISIN fallback: resolved legacy name '%s' → fund code %s.", ticker, resolved
        )
        fund_code = resolved

    try:
        isin = lookup_isin(fund_code)
    except Exception:
        return None
    if not isin:
        return None
    logger.info("ISIN fallback resolved %s → %s via toushin-lib.", fund_code, isin)
    try:
        # Quick migration: persist ISIN for both alias ticker and canonical fund code.
        repo.backfill_isin_for_ticker(session, ticker, isin)
        repo.backfill_isin_for_ticker(session, fund_code, isin)
    except Exception as exc:
        logger.debug("ISIN back-fill to DB failed for %s: %s", ticker, exc)
    return fund_code, isin


def _sync_single_fund_nav_with_reason(
    session: Session, ticker: str
) -> tuple[bool, str | None]:
    """Sync one fund and return structured outcome.

    Returns:
        (True, None) on success
        (False, reason_code) on failure
    """
    upper = ticker.upper()
    fund_code = upper
    isin = repo.find_isin_for_ticker(session, upper)

    # Legacy name ticker path: even when ISIN already exists locally, CSV download
    # still needs the 8-char fund code. Resolve DB-first by ISIN, then fallback API.
    if not _is_fund_code(upper):
        if isin:
            resolved_code = repo.find_fund_code_by_isin(session, isin)
            if resolved_code:
                fund_code = resolved_code
            else:
                fallback = _resolve_isin_fallback(session, upper)
                if fallback:
                    fund_code, fallback_isin = fallback
                    isin = isin or fallback_isin
        else:
            fallback = _resolve_isin_fallback(session, upper)
            if fallback:
                fund_code, isin = fallback
    elif not isin:
        fallback = _resolve_isin_fallback(session, upper)
        if fallback:
            fund_code, isin = fallback
    if not isin:
        logger.warning("NAV on-demand: no ISIN found for %s, skipping.", upper)
        return False, _NAV_FAIL_MISSING_ISIN

    try:
        csv_rows = fetch_fund_nav_csv(fund_code, isin)
    except Exception as exc:
        logger.warning("NAV on-demand fetch failed for %s: %s", upper, exc)
        return False, _NAV_FAIL_DOWNLOAD_ERROR

    if csv_rows is None:
        return False, _NAV_FAIL_DOWNLOAD_ERROR

    if not csv_rows:
        return False, _NAV_FAIL_EMPTY_CSV

    try:
        annotated = _annotate_previous_nav(csv_rows)
        repo.bulk_upsert_nav(session, fund_code, isin, annotated, autocommit=True)
    except Exception as exc:
        logger.warning("NAV on-demand upsert failed for %s: %s", fund_code, exc)
        return False, _NAV_FAIL_UPSERT_ERROR

    logger.info("NAV on-demand: %s — %d rows upserted.", fund_code, len(annotated))
    return True, None


def sync_single_fund_nav(session: Session, ticker: str) -> bool:
    """On-demand NAV sync for a single fund (called after stock creation).

    Returns True on success, False on failure.  Never raises — callers can
    safely fire-and-forget.
    """
    ok, _reason = _sync_single_fund_nav_with_reason(session, ticker)
    return ok


def sync_mutual_fund_navs() -> dict[str, int | list[str] | list[dict[str, str]]]:
    """One-shot sync: fetch NAV for all active Mutual_Fund stocks."""
    with Session(engine) as session:
        stocks = repo.find_active_stocks(session)
        mf_stocks = [s for s in stocks if s.category == StockCategory.MUTUAL_FUND]

        if not mf_stocks:
            logger.debug("NAV sync: no active Mutual_Fund stocks on radar.")
            return {
                "synced": 0,
                "failed": 0,
                "failed_tickers": [],
                "failed_details": [],
            }

        synced = 0
        failed = 0
        failed_tickers: list[str] = []
        failed_details: list[dict[str, str]] = []
        for stock in mf_stocks:
            ok, reason = _sync_single_fund_nav_with_reason(session, stock.ticker)
            if ok:
                synced += 1
            else:
                failed += 1
                failed_tickers.append(stock.ticker)
                failed_details.append(
                    {"ticker": stock.ticker, "reason": reason or _NAV_FAIL_UPSERT_ERROR}
                )

    return {
        "synced": synced,
        "failed": failed,
        "failed_tickers": failed_tickers,
        "failed_details": failed_details,
    }


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
