"""Backward-compatibility shim — re-exports domain.core.constants.

Consumers using ``from domain.constants import X`` continue to work unchanged.
``__all__`` is explicitly re-exported so static analysis tools know this module's
public API without needing to resolve the star import themselves.
"""

from domain.core.constants import *  # noqa: F403
from domain.core.constants import __all__ as __all__
