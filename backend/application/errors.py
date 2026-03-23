"""Application-layer error primitives.

These exceptions represent use-case/domain failures and must be mapped to
transport-layer errors (e.g. FastAPI HTTPException) in API routes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

StatusHint = Literal["validation", "not_found", "external", "internal"]


@dataclass(slots=True)
class ApplicationError(Exception):
    """Typed error raised by application services."""

    error_code: str
    message_key: str
    status_hint: StatusHint | None = None
    # Deprecated: prefer status_hint. status_code is a transport concept and
    # breaks the application/transport boundary.
    status_code: int | None = None
    params: dict[str, object] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"{self.error_code}: {self.message_key}"
