"""API-layer mapping from application errors to HTTP errors."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import HTTPException

from i18n import t

if TYPE_CHECKING:
    from application.errors import ApplicationError

_HINT_TO_STATUS: dict[str | None, int] = {
    "validation": 422,
    "not_found": 404,
    "external": 502,
    "internal": 500,
    None: 500,
}


def to_http_exception(error: ApplicationError, *, lang: str) -> HTTPException:
    """Convert an application error into a transport-safe HTTPException."""
    status_code = error.status_code or _HINT_TO_STATUS.get(error.status_hint, 500)
    return HTTPException(
        status_code=status_code,
        detail={
            "error_code": error.error_code,
            "detail": t(error.message_key, lang=lang, **error.params),
        },
    )
