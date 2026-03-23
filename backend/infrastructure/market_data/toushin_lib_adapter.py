"""Infrastructure — Toushin-lib ISIN lookup adapter.

Resolves ``associFundCd`` (投信協会ファンドコード) → ``isinCd`` mappings
via the toushin-lib fund search API.  Results are cached in-process for up
to ``_CACHE_TTL_SECONDS`` to avoid repeated large HTTP payloads.
"""

from __future__ import annotations

import re
import threading
import time

import httpx

from infrastructure.common import config as settings
from logging_config import get_logger

logger = get_logger(__name__)

_REQUEST_TIMEOUT = 60.0
_CACHE_TTL_SECONDS = 24 * 3600
_MAX_PAGE_SIZE = 10_000
_FAIL_BACKOFF_BASE_SECONDS = 30.0
_FAIL_BACKOFF_MAX_SECONDS = 3600.0

_cache_lock = threading.Lock()
_cache_cond = threading.Condition(_cache_lock)
_isin_cache: dict[str, str] = {}
_name_to_code_cache: dict[str, str] = {}
_cache_ts: float = 0.0
_fetch_in_progress = False
_last_fetch_failed_ts: float = 0.0
_consecutive_failures = 0


def _normalize_name(value: str) -> str:
    """Normalize a fund name for fuzzy matching (strip whitespace, lowercase)."""
    return re.sub(r"\s+", "", value.strip()).lower()


def _fetch_raw_data() -> tuple[dict[str, str], dict[str, str], bool]:
    """POST to toushin-lib and return (code→isin, normalized_name→code)."""
    isin_map: dict[str, str] = {}
    name_map: dict[str, str] = {}
    data = {"pageSize": str(_MAX_PAGE_SIZE), "startNo": "0"}
    headers = {"X-Requested-With": "XMLHttpRequest"}

    last_exc: Exception | None = None
    for attempt in range(3):
        verify = attempt < 2
        try:
            with httpx.Client(
                timeout=_REQUEST_TIMEOUT, follow_redirects=True, verify=verify
            ) as client:
                resp = client.post(
                    settings.TOUSHIN_LIB_SEARCH_URL,
                    data=data,
                    headers=headers,
                )
                resp.raise_for_status()
                payload = resp.json()
                break
        except Exception as exc:
            last_exc = exc
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
                logger.debug(
                    "ISIN lookup attempt %d failed, retrying: %s", attempt + 1, exc
                )
                continue
            logger.warning("ISIN lookup failed after %d attempts: %s", attempt + 1, exc)
            return isin_map, name_map, False
    else:
        if last_exc:
            logger.warning("ISIN lookup exhausted retries: %s", last_exc)
        return isin_map, name_map, False

    results = (
        payload.get("searchResultInfo", {}).get("resultInfoMapList", [])
        if isinstance(payload, dict)
        else []
    )
    dup_names: set[str] = set()
    for item in results:
        fund_code = str(item.get("associFundCd", "")).strip().upper()
        isin = str(item.get("isinCd", "")).strip()
        fund_name = str(item.get("fundNm", "")).strip()
        if fund_code and isin:
            isin_map[fund_code] = isin
        if fund_code and fund_name:
            key = _normalize_name(fund_name)
            if key in name_map:
                dup_names.add(key)
            else:
                name_map[key] = fund_code
    for dup in dup_names:
        name_map.pop(dup, None)

    logger.info("ISIN lookup: resolved %d fund-code → ISIN mappings.", len(isin_map))
    return isin_map, name_map, True


def _ensure_cache(*, force_refresh: bool = False) -> None:
    global _cache_ts
    global _consecutive_failures
    global _fetch_in_progress
    global _isin_cache
    global _last_fetch_failed_ts
    global _name_to_code_cache

    # Avoid duplicate concurrent fetches: only one thread performs the network call,
    # other threads wait and reuse that result.
    while True:
        now = time.monotonic()
        with _cache_cond:
            if (
                not force_refresh
                and _isin_cache
                and (now - _cache_ts) < _CACHE_TTL_SECONDS
            ):
                return
            if (
                not force_refresh
                and _consecutive_failures > 0
                and _last_fetch_failed_ts > 0
            ):
                backoff_seconds = min(
                    _FAIL_BACKOFF_MAX_SECONDS,
                    _FAIL_BACKOFF_BASE_SECONDS * (2 ** (_consecutive_failures - 1)),
                )
                if (now - _last_fetch_failed_ts) < backoff_seconds:
                    # Serve stale cache (or empty cache on cold-start outage) and
                    # avoid hammering upstream while it is unhealthy.
                    return
            if not _fetch_in_progress:
                _fetch_in_progress = True
                break
            _cache_cond.wait(timeout=1.0)

    isin_map, name_map, ok = _fetch_raw_data()
    now = time.monotonic()
    with _cache_cond:
        if ok:
            _isin_cache = isin_map
            _name_to_code_cache = name_map
            _cache_ts = now
            _last_fetch_failed_ts = 0.0
            _consecutive_failures = 0
        else:
            _last_fetch_failed_ts = now
            _consecutive_failures += 1
        _fetch_in_progress = False
        _cache_cond.notify_all()


def fetch_isin_mapping(*, force_refresh: bool = False) -> dict[str, str]:
    """Return cached {fund_code: isin} mapping, refreshing if stale."""
    _ensure_cache(force_refresh=force_refresh)
    with _cache_lock:
        return dict(_isin_cache)


def lookup_isin(fund_code: str) -> str | None:
    """Look up ISIN for a single fund code (convenience wrapper)."""
    mapping = fetch_isin_mapping()
    return mapping.get(fund_code.strip().upper())


def resolve_fund_code_from_name(fund_name: str) -> str | None:
    """Resolve a fund name to its fund code via the toushin-lib cache.

    Used to handle legacy tickers that store fund names instead of codes.
    Returns None when the name is ambiguous (multiple matches) or not found.
    """
    _ensure_cache()
    key = _normalize_name(fund_name)
    with _cache_lock:
        return _name_to_code_cache.get(key)


def invalidate_isin_cache() -> None:
    """Force next call to ``fetch_isin_mapping`` to re-fetch."""
    global \
        _cache_ts, \
        _consecutive_failures, \
        _isin_cache, \
        _last_fetch_failed_ts, \
        _name_to_code_cache
    with _cache_lock:
        _isin_cache = {}
        _name_to_code_cache = {}
        _cache_ts = 0.0
        _last_fetch_failed_ts = 0.0
        _consecutive_failures = 0
