"""Backward-compat shim — SWRCache has moved to infrastructure.common.cache."""

from infrastructure.common.cache import CacheState, SWRCache  # noqa: F401
