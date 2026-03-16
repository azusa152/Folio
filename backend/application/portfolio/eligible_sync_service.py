"""Background sync for official NISA eligible-asset lists."""

from __future__ import annotations

import re
import tempfile
import threading
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from sqlmodel import Session

from application.portfolio.eligibility_service import refresh_eligible_assets_from_rows
from config import settings
from infrastructure.database import engine
from infrastructure.external.eligible_fund_parser import (
    is_tsumitate_asset_class_xlsx,
    parse_growth_xlsx,
    parse_tsumitate_xlsx,
)
from logging_config import get_logger

logger = get_logger(__name__)

_sync_started = False
_sync_lock = threading.Lock()


def _extract_xlsx_urls(page_html: str, base_url: str) -> list[str]:
    matches = re.findall(r'href="([^"]+\.xlsx)"', page_html, flags=re.IGNORECASE)
    urls = [urljoin(base_url, href.strip()) for href in matches if href.strip()]
    # Keep order while removing duplicates
    seen: set[str] = set()
    ordered: list[str] = []
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        ordered.append(url)
    return ordered


def _resolve_xlsx_urls(source_url: str) -> list[str]:
    if urlparse(source_url).path.lower().endswith(".xlsx"):
        return [source_url]
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        index_resp = client.get(source_url)
        index_resp.raise_for_status()
    return _extract_xlsx_urls(index_resp.text, source_url)


def _download_to_temp(url: str) -> Path:
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        suffix = ".xlsx" if url.lower().endswith(".xlsx") else ".tmp"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(response.content)
            return Path(tmp.name)


def _load_tsumitate_rows() -> list[dict]:
    urls = _resolve_xlsx_urls(settings.ELIGIBLE_TSUMITATE_URL)
    if not urls:
        raise ValueError("No Tsumitate XLSX links found on configured source URL.")
    fallback_rows: list[dict] = []
    for url in urls:
        try:
            temp_path = _download_to_temp(url)
            try:
                if is_tsumitate_asset_class_xlsx(temp_path):
                    rows = parse_tsumitate_xlsx(temp_path)
                    if rows:
                        return rows
                rows = parse_tsumitate_xlsx(temp_path)
                if len(rows) > len(fallback_rows):
                    fallback_rows = rows
            finally:
                temp_path.unlink(missing_ok=True)
        except Exception as exc:
            logger.warning("Skipping Tsumitate source candidate (%s): %s", url, exc)
            continue
    if fallback_rows:
        logger.warning(
            "Tsumitate asset-class signature not found; falling back to largest parsed sheet."
        )
        return fallback_rows
    raise ValueError("No parseable rows found in Tsumitate source XLSX links.")


def _load_growth_rows() -> list[dict]:
    urls = _resolve_xlsx_urls(settings.ELIGIBLE_GROWTH_URL)
    if not urls:
        raise ValueError("No Growth XLSX links found on configured source URL.")
    selected = [
        url
        for url in urls
        if "unlisted_fund_for_investor.xlsx" in url
        or "listed_fund_for_investor.xlsx" in url
    ] or urls
    rows: list[dict] = []
    for url in selected:
        try:
            temp_path = _download_to_temp(url)
            try:
                rows.extend(parse_growth_xlsx(temp_path))
            finally:
                temp_path.unlink(missing_ok=True)
        except Exception as exc:
            logger.warning("Skipping Growth source candidate (%s): %s", url, exc)
            continue
    if not rows:
        raise ValueError("No parseable rows found in Growth source XLSX links.")
    deduped: dict[str, dict] = {}
    for row in rows:
        deduped[row["ticker"]] = row
    return list(deduped.values())


def sync_wrapper_from_official_source(
    session: Session,
    wrapper: str,
    *,
    source: str = "official_sync",
) -> dict[str, int]:
    normalized_wrapper = wrapper.strip().lower()
    if normalized_wrapper == "nisa_tsumitate":
        rows = _load_tsumitate_rows()
    elif normalized_wrapper == "nisa_growth":
        rows = _load_growth_rows()
    else:
        raise ValueError(f"Unsupported wrapper for official sync: {wrapper}")
    return refresh_eligible_assets_from_rows(
        session=session,
        wrapper=normalized_wrapper,
        rows=rows,
        source=source,
        autocommit=True,
    )


def refresh_official_wrappers() -> dict[str, dict[str, int]]:
    """Run one-shot refresh for NISA wrappers from official URLs."""
    result: dict[str, dict[str, int]] = {}
    with Session(engine) as session:
        for wrapper in ("nisa_tsumitate", "nisa_growth"):
            result[wrapper] = sync_wrapper_from_official_source(session, wrapper)
    return result


def _eligible_sync_loop() -> None:
    interval_hours = max(settings.ELIGIBLE_SYNC_INTERVAL_HOURS, 0)
    if interval_hours <= 0:
        logger.info(
            "NISA eligible-list periodic sync disabled (interval=%d).", interval_hours
        )
        return
    interval_seconds = interval_hours * 3600
    logger.info(
        "NISA eligible-list periodic sync started (every %d hour(s)).",
        interval_hours,
    )
    while True:
        time.sleep(interval_seconds)
        try:
            stats = refresh_official_wrappers()
            logger.info("NISA eligible-list periodic sync succeeded: %s", stats)
        except Exception as exc:
            logger.warning("NISA eligible-list periodic sync failed: %s", exc)


def start_eligible_sync_loop() -> None:
    """Ensure only one background eligible-list sync loop is running."""
    global _sync_started
    with _sync_lock:
        if _sync_started:
            return
        _sync_started = True
    threading.Thread(target=_eligible_sync_loop, daemon=True).start()
