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
from infrastructure.common import config as settings
from infrastructure.database import engine
from infrastructure.external.eligible_fund_parser import (
    parse_growth_xlsx,
    parse_tsumitate_from_growth_xlsx,
    parse_tsumitate_xlsx,
)
from infrastructure.market_data.toushin_lib_adapter import fetch_isin_mapping
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
    last_exc: Exception | None = None
    for attempt in range(_DOWNLOAD_MAX_RETRIES):
        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                index_resp = client.get(source_url)
                index_resp.raise_for_status()
                break
        except Exception as exc:
            last_exc = exc
            if not _is_ssl_error(exc) or attempt >= _DOWNLOAD_MAX_RETRIES - 1:
                raise
            logger.debug(
                "Index page fetch attempt %d failed for %s: %s",
                attempt + 1,
                source_url,
                exc,
            )
            time.sleep(1.5 * (attempt + 1))
    else:
        raise last_exc  # type: ignore[misc]
    return _extract_xlsx_urls(index_resp.text, source_url)


_DOWNLOAD_MAX_RETRIES = 3
_SSL_RETRY_ERRORS = (
    "UNEXPECTED_EOF_WHILE_READING",
    "EOF occurred in violation of protocol",
    "SSLError",
    "ConnectError",
)


def _is_ssl_error(exc: Exception) -> bool:
    return any(tok in str(exc) for tok in _SSL_RETRY_ERRORS)


def _download_to_temp(url: str) -> Path:
    last_exc: Exception | None = None
    for attempt in range(_DOWNLOAD_MAX_RETRIES):
        try:
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                response = client.get(url)
                response.raise_for_status()
                suffix = ".xlsx" if url.lower().endswith(".xlsx") else ".tmp"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(response.content)
                    return Path(tmp.name)
        except Exception as exc:
            last_exc = exc
            if not _is_ssl_error(exc) or attempt >= _DOWNLOAD_MAX_RETRIES - 1:
                raise
            logger.debug("Download attempt %d failed for %s: %s", attempt + 1, url, exc)
            time.sleep(1.5 * (attempt + 1))
    raise last_exc  # type: ignore[misc]


def _normalize_fund_name(value: str) -> str:
    return re.sub(r"\s+", "", value.strip()).lower()


def _load_tsumitate_rows() -> list[dict]:
    urls = _resolve_xlsx_urls(settings.ELIGIBLE_TSUMITATE_URL)
    if not urls:
        raise ValueError("No Tsumitate XLSX links found on configured source URL.")
    selected = [
        url
        for url in urls
        if "unlisted_fund_for_investor.xlsx" in url
        or "listed_fund_for_investor.xlsx" in url
    ] or urls
    rows: list[dict] = []
    fallback_rows: list[dict] = []
    growth_rows: list[dict] = []
    for url in selected:
        try:
            temp_path = _download_to_temp(url)
            try:
                rows.extend(parse_tsumitate_from_growth_xlsx(temp_path))
                growth_rows.extend(parse_growth_xlsx(temp_path))
                legacy_rows = parse_tsumitate_xlsx(temp_path)
                if len(legacy_rows) > len(fallback_rows):
                    fallback_rows = legacy_rows
            finally:
                temp_path.unlink(missing_ok=True)
        except Exception as exc:
            logger.warning("Skipping Tsumitate source candidate (%s): %s", url, exc)
            continue
    if rows:
        deduped: dict[str, dict] = {}
        for row in rows:
            deduped[row["ticker"]] = row
        return list(deduped.values())
    if fallback_rows:
        # Exact-match recovery path:
        # when legacy fallback rows only contain fund_name ticker surrogate,
        # recover ticker/ISIN from growth-parsed rows using normalized exact name.
        growth_by_name: dict[str, dict] = {}
        duplicate_growth_names: set[str] = set()
        for row in growth_rows:
            name = _normalize_fund_name(str(row.get("fund_name", "")))
            if not name:
                continue
            if name in growth_by_name:
                duplicate_growth_names.add(name)
            else:
                growth_by_name[name] = row

        resolved = 0
        unresolved = 0
        recovered_rows: list[dict] = []
        for row in fallback_rows:
            fund_name = str(row.get("fund_name", ""))
            key = _normalize_fund_name(fund_name)
            candidate = growth_by_name.get(key)
            if (
                candidate
                and key not in duplicate_growth_names
                and candidate.get("ticker")
                and candidate.get("isin_code")
            ):
                recovered_rows.append(
                    {
                        **row,
                        "ticker": str(candidate["ticker"]).strip().upper(),
                        "isin_code": str(candidate["isin_code"]).strip(),
                    }
                )
                resolved += 1
            else:
                recovered_rows.append(row)
                unresolved += 1

        logger.warning(
            "Tsumitate fallback recovery: resolved=%d unresolved=%d",
            resolved,
            unresolved,
        )
        logger.warning(
            "Tsumitate target flag not found; falling back to legacy FSA-style parser."
        )
        return recovered_rows
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


def _enrich_isin(rows: list[dict]) -> list[dict]:
    """Fill in missing ``isin_code`` using the toushin-lib fund search API."""
    missing = [r for r in rows if not r.get("isin_code") and r.get("ticker")]
    if not missing:
        return rows

    try:
        mapping = fetch_isin_mapping()
    except Exception as exc:
        logger.warning("ISIN enrichment lookup failed, skipping: %s", exc)
        return rows

    if not mapping:
        return rows

    enriched = 0
    for row in rows:
        if not row.get("isin_code") and row.get("ticker"):
            isin = mapping.get(row["ticker"].strip().upper())
            if isin:
                row["isin_code"] = isin
                enriched += 1

    if enriched:
        logger.info(
            "ISIN enrichment: filled %d of %d rows missing ISIN.",
            enriched,
            len(missing),
        )
    else:
        logger.warning(
            "ISIN enrichment: 0 of %d rows resolved — XLSX source may lack fund codes.",
            len(missing),
        )
    return rows


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
    rows = _enrich_isin(rows)
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


def refresh_official_wrappers_best_effort() -> dict[str, dict[str, int]]:
    """Best-effort one-shot refresh for NISA wrappers.

    Used by manual NAV sync to improve ISIN coverage before NAV fetch.
    Any wrapper-level refresh failure is logged and skipped.
    """
    result: dict[str, dict[str, int]] = {}
    with Session(engine) as session:
        for wrapper in ("nisa_tsumitate", "nisa_growth"):
            try:
                result[wrapper] = sync_wrapper_from_official_source(
                    session, wrapper, source="nav_sync_backfill"
                )
            except Exception as exc:
                logger.warning(
                    "NAV sync pre-refresh skipped for wrapper %s: %s", wrapper, exc
                )
        try:
            _reclassify_after_sync()
        except Exception as exc:
            logger.warning("NAV sync pre-refresh reclassification failed: %s", exc)
    return result


def _reclassify_after_sync() -> None:
    """Reclassify stocks and holdings after eligible-list refresh."""
    from application.portfolio.settlement_service import (
        reclassify_mutual_fund_holdings,
    )
    from application.stock.stock_service import reclassify_mutual_fund_stocks

    with Session(engine) as session:
        reclassify_mutual_fund_stocks(session)
        reclassify_mutual_fund_holdings(session)


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
        try:
            _reclassify_after_sync()
        except Exception as exc:
            logger.warning("Post-sync MF reclassification failed: %s", exc)


def start_eligible_sync_loop() -> None:
    """Ensure only one background eligible-list sync loop is running."""
    global _sync_started
    with _sync_lock:
        if _sync_started:
            return
        _sync_started = True
    threading.Thread(target=_eligible_sync_loop, daemon=True).start()
