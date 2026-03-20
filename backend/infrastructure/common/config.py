"""Infrastructure configuration — environment-sourced path and size settings.

These values depend on the runtime environment and do not belong in the
domain layer.  All infrastructure modules that need disk paths import from
here, not from domain.constants.
"""

import os

DATA_DIR: str = os.getenv("DATA_DIR", "/app/data")
DISK_CACHE_DIR: str = os.getenv("DISK_CACHE_DIR", f"{DATA_DIR}/yf_cache")
DISK_CACHE_SIZE_LIMIT: int = 100 * 1024 * 1024  # 100 MB
