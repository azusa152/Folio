"""Infrastructure — FundSectorWeight Repository."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Session, delete, select

from domain.core.entities import FundSectorWeight


def get_sector_weights_for_funds(
    session: Session,
    fund_codes: list[str],
) -> dict[str, dict[str, float]]:
    """Batch-load sector weights for a list of fund codes.

    Returns {fund_code: {sector: weight, ...}, ...}.
    Fund codes not in the DB are absent from the result.
    """
    if not fund_codes:
        return {}
    normalized = [c.upper().strip() for c in fund_codes]
    stmt = select(FundSectorWeight).where(
        FundSectorWeight.fund_code.in_(normalized)  # pyright: ignore[reportAttributeAccessIssue]
    )
    rows = session.exec(stmt).all()
    result: dict[str, dict[str, float]] = {}
    for row in rows:
        result.setdefault(row.fund_code, {})[row.sector] = row.weight
    return result


def upsert_sector_weights(
    session: Session,
    fund_code: str,
    weights: dict[str, float],
    source: str = "manual",
    *,
    autocommit: bool = True,
) -> list[FundSectorWeight]:
    """Replace all sector weights for a fund (delete-then-insert).

    ``weights`` maps sector name to weight (0.0–1.0).
    Returns the newly upserted rows.
    """
    normalized = fund_code.upper().strip()
    now = datetime.now(UTC)

    session.exec(
        delete(FundSectorWeight).where(  # pyright: ignore[reportArgumentType]
            FundSectorWeight.fund_code == normalized
        )
    )

    new_rows: list[FundSectorWeight] = []
    for sector, weight in weights.items():
        row = FundSectorWeight(
            fund_code=normalized,
            sector=sector,
            weight=weight,
            source=source,
            updated_at=now,
        )
        session.add(row)
        new_rows.append(row)

    if autocommit:
        session.commit()
        for row in new_rows:
            session.refresh(row)
    else:
        session.flush()
    return new_rows


def delete_sector_weights(
    session: Session,
    fund_code: str,
    *,
    autocommit: bool = True,
) -> int:
    """Remove all sector weight overrides for a fund. Returns number of rows deleted."""
    normalized = fund_code.upper().strip()
    result = session.exec(  # type: ignore[call-overload]
        delete(FundSectorWeight).where(  # pyright: ignore[reportArgumentType]
            FundSectorWeight.fund_code == normalized
        )
    )
    if autocommit:
        session.commit()
    else:
        session.flush()
    return result.rowcount or 0


def find_all_fund_sector_weights(
    session: Session,
) -> dict[str, list[FundSectorWeight]]:
    """Return all stored sector weights grouped by fund code."""
    stmt = select(FundSectorWeight).order_by(
        FundSectorWeight.fund_code,  # pyright: ignore[reportArgumentType]
        FundSectorWeight.sector,  # pyright: ignore[reportArgumentType]
    )
    result: dict[str, list[FundSectorWeight]] = {}
    for row in session.exec(stmt).all():
        result.setdefault(row.fund_code, []).append(row)
    return result
