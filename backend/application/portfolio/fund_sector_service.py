"""Application — Fund Sector Weight Service.

CRUD operations for FundSectorWeight overrides used in sector exposure calculation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlmodel import select

from domain.core.entities import FundSectorWeight
from infrastructure.persistence.repositories.fund_sector_repo import (
    delete_sector_weights as _delete,
)
from infrastructure.persistence.repositories.fund_sector_repo import (
    get_sector_weights_for_funds as _get,
)
from infrastructure.persistence.repositories.fund_sector_repo import (
    upsert_sector_weights as _upsert,
)
from logging_config import get_logger

if TYPE_CHECKING:
    from sqlmodel import Session

logger = get_logger(__name__)


def get_sector_weights(session: Session, fund_code: str) -> dict[str, float]:
    """Return stored sector weights for a single fund. Empty dict if none."""
    result = _get(session, [fund_code])
    return result.get(fund_code.upper().strip(), {})


def set_sector_weights(
    session: Session,
    fund_code: str,
    weights: dict[str, float],
    source: str = "manual",
) -> dict[str, float]:
    """Replace all sector weights for a fund. Returns the newly stored weights."""
    _upsert(session, fund_code, weights, source=source)
    return weights


def remove_sector_weights(session: Session, fund_code: str) -> int:
    """Remove all sector weights for a fund. Returns count of deleted rows."""
    return _delete(session, fund_code)


def get_fund_sector_source(session: Session, fund_code: str) -> str:
    """Return the source field for the first stored row, or 'manual' if none."""
    normalized = fund_code.upper().strip()
    row = session.exec(
        select(FundSectorWeight).where(FundSectorWeight.fund_code == normalized)
    ).first()
    return row.source if row else "manual"
