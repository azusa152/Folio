"""
Config — 從環境變數覆寫 domain 常數。
在應用程式啟動時呼叫一次 init_settings()。
"""

import os

ELIGIBLE_TSUMITATE_URL = "https://www.toushin.or.jp/static/NISA_growth_productsList/"
ELIGIBLE_GROWTH_URL = "https://www.toushin.or.jp/static/NISA_growth_productsList/"
ELIGIBLE_SYNC_INTERVAL_HOURS = 168


def init_settings() -> None:
    """Override domain constants from environment. Call once at startup."""
    global ELIGIBLE_GROWTH_URL, ELIGIBLE_SYNC_INTERVAL_HOURS, ELIGIBLE_TSUMITATE_URL
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
