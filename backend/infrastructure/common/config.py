"""Infrastructure configuration — environment-sourced path and size settings.

These values depend on the runtime environment and do not belong in the
domain layer.  All infrastructure modules that need disk paths import from
here, not from domain.constants.

External-service URLs and sync intervals (previously in config/settings.py)
are also centralised here.  Call init_settings() once at application startup
to apply any environment-variable overrides.
"""

import os

DATA_DIR: str = os.getenv("DATA_DIR", "/app/data")
DISK_CACHE_DIR: str = os.getenv("DISK_CACHE_DIR", f"{DATA_DIR}/yf_cache")
DISK_CACHE_SIZE_LIMIT: int = 100 * 1024 * 1024  # 100 MB

# External service URLs and sync intervals
ELIGIBLE_TSUMITATE_URL = "https://www.toushin.or.jp/static/NISA_growth_productsList/"
ELIGIBLE_GROWTH_URL = "https://www.toushin.or.jp/static/NISA_growth_productsList/"
ELIGIBLE_SYNC_INTERVAL_HOURS = 168
NAV_SYNC_INTERVAL_HOURS = 24
TOUSHIN_LIB_CSV_URL = (
    "https://toushin-lib.fwg.ne.jp/FdsWeb/FDST030000/csv-file-download"
)
TOUSHIN_LIB_SEARCH_URL = (
    "https://toushin-lib.fwg.ne.jp/FdsWeb/FDST999900/fundDataSearch"
)


def init_settings() -> None:
    """Override module-level settings from environment variables. Call once at startup."""
    global \
        ELIGIBLE_GROWTH_URL, \
        ELIGIBLE_SYNC_INTERVAL_HOURS, \
        ELIGIBLE_TSUMITATE_URL, \
        NAV_SYNC_INTERVAL_HOURS, \
        TOUSHIN_LIB_CSV_URL, \
        TOUSHIN_LIB_SEARCH_URL
    ELIGIBLE_TSUMITATE_URL = os.getenv(
        "ELIGIBLE_TSUMITATE_URL",
        ELIGIBLE_TSUMITATE_URL,
    )
    ELIGIBLE_GROWTH_URL = os.getenv(
        "ELIGIBLE_GROWTH_URL",
        ELIGIBLE_GROWTH_URL,
    )
    ELIGIBLE_SYNC_INTERVAL_HOURS = int(
        os.getenv("ELIGIBLE_SYNC_INTERVAL_HOURS", str(ELIGIBLE_SYNC_INTERVAL_HOURS))
    )
    NAV_SYNC_INTERVAL_HOURS = int(
        os.getenv("NAV_SYNC_INTERVAL_HOURS", str(NAV_SYNC_INTERVAL_HOURS))
    )
    TOUSHIN_LIB_CSV_URL = os.getenv(
        "TOUSHIN_LIB_CSV_URL",
        TOUSHIN_LIB_CSV_URL,
    )
    TOUSHIN_LIB_SEARCH_URL = os.getenv(
        "TOUSHIN_LIB_SEARCH_URL",
        TOUSHIN_LIB_SEARCH_URL,
    )
