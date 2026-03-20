"""Backward-compat shim for legacy imports from ``config.settings``.

Canonical location is ``infrastructure.common.config``.
Use module-attribute delegation so callers importing this module as
``from config import settings`` always see the latest values after
``init_settings()`` mutates runtime configuration.
"""

from infrastructure.common import config as _config

__all__ = [name for name in dir(_config) if name == "init_settings" or name.isupper()]


def init_settings() -> None:
    _config.init_settings()


def __getattr__(name: str):
    return getattr(_config, name)


def __dir__():
    return sorted(set(globals()) | set(dir(_config)))
