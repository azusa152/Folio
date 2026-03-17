"""Infrastructure — Toushin-lib NAV adapter for Japanese mutual funds.

Fetches NAV (基準価額) data from the Investment Trust Association library
(toushin-lib.fwg.ne.jp) via CSV download.  This is a pure fetcher — the DB
table ``MutualFundNav`` serves as the persistent cache, updated by a daily
background sync job in ``application.portfolio.nav_sync_service``.
"""

from __future__ import annotations

import csv
import io
from datetime import date, datetime

import httpx

from config import settings
from logging_config import get_logger

logger = get_logger(__name__)

_REQUEST_TIMEOUT = 30.0


def _parse_date(raw: str) -> date | None:
    """Parse YYYY/MM/DD or YYYY-MM-DD to a date object."""
    for fmt in ("%Y/%m/%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _parse_float(raw: str) -> float | None:
    cleaned = raw.strip().replace(",", "")
    if not cleaned or cleaned == "-":
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def fetch_fund_nav_csv(fund_code: str, isin_code: str) -> list[dict] | None:
    """Download and parse the NAV CSV from toushin-lib.

    Returns a list of dicts sorted newest-first:
        [{"date": date, "nav": float, "net_assets": float | None}, ...]
    Returns None on network/download error.
    Returns [] when downloaded but no parseable NAV rows are found.
    """
    params = {"isinCd": isin_code, "associFundCd": fund_code}
    try:
        with httpx.Client(timeout=_REQUEST_TIMEOUT, follow_redirects=True) as client:
            resp = client.get(settings.TOUSHIN_LIB_CSV_URL, params=params)
            resp.raise_for_status()
    except Exception as exc:
        logger.warning(
            "toushin-lib CSV download failed for %s/%s: %s",
            fund_code,
            isin_code,
            exc,
        )
        return None

    try:
        text = resp.content.decode("shift_jis", errors="replace")
    except Exception:
        text = resp.text

    rows: list[dict] = []
    reader = csv.reader(io.StringIO(text))
    header: list[str] | None = None

    for csv_row in reader:
        if header is None:
            header = [c.strip() for c in csv_row]
            continue
        if len(csv_row) < len(header):
            continue

        row_dict = dict(zip(header, csv_row, strict=False))
        nav_date = _parse_date(row_dict.get("年月日", ""))
        nav = _parse_float(row_dict.get("基準価額(円)", ""))
        if nav_date is None or nav is None:
            continue

        net_assets = _parse_float(row_dict.get("純資産総額(百万円)", ""))
        rows.append(
            {
                "date": nav_date,
                "nav": nav,
                "net_assets": net_assets,
            }
        )

    if not rows:
        logger.warning(
            "toushin-lib CSV returned 0 parseable NAV rows for %s/%s.",
            fund_code,
            isin_code,
        )
        return []

    rows.sort(key=lambda r: r["date"], reverse=True)
    return rows


def fetch_latest_nav(fund_code: str, isin_code: str) -> dict | None:
    """Convenience wrapper returning only the most recent NAV row."""
    rows = fetch_fund_nav_csv(fund_code, isin_code)
    if not rows:
        return None
    latest = rows[0]
    prev_nav = rows[1]["nav"] if len(rows) > 1 else None
    return {
        "date": latest["date"],
        "nav": latest["nav"],
        "nav_previous": prev_nav,
        "net_assets": latest.get("net_assets"),
    }
