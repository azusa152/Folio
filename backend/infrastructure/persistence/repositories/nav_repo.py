"""Infrastructure — MutualFundNav Repository."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlmodel import Session, select

from domain.entities import MutualFundNav

if TYPE_CHECKING:
    from datetime import date


# ===========================================================================
# MutualFundNav Repository
# ===========================================================================


def get_latest_nav(session: Session, fund_code: str) -> MutualFundNav | None:
    """Get the most recent NAV row for a fund."""
    stmt = (
        select(MutualFundNav)
        .where(MutualFundNav.fund_code == fund_code.upper().strip())
        .order_by(MutualFundNav.nav_date.desc())
        .limit(1)
    )
    return session.exec(stmt).first()


def get_nav_history(
    session: Session, fund_code: str, *, limit: int = 365
) -> list[MutualFundNav]:
    """Get NAV history for charting (newest first, up to `limit` rows)."""
    stmt = (
        select(MutualFundNav)
        .where(MutualFundNav.fund_code == fund_code.upper().strip())
        .order_by(MutualFundNav.nav_date.desc())
        .limit(limit)
    )
    return list(session.exec(stmt).all())


def upsert_nav(
    session: Session,
    fund_code: str,
    isin_code: str,
    nav: float,
    nav_date: date,
    *,
    nav_previous: float | None = None,
    net_assets: float | None = None,
    autocommit: bool = True,
) -> MutualFundNav:
    """Insert or update a single NAV record (unique by fund_code + nav_date)."""
    normalized = fund_code.upper().strip()
    stmt = select(MutualFundNav).where(
        MutualFundNav.fund_code == normalized,
        MutualFundNav.nav_date == nav_date,
    )
    existing = session.exec(stmt).first()
    now = datetime.now(UTC)
    if existing:
        existing.nav = nav
        existing.nav_previous = nav_previous
        existing.net_assets = net_assets
        existing.isin_code = isin_code
        existing.fetched_at = now
        session.add(existing)
        result = existing
    else:
        result = MutualFundNav(
            fund_code=normalized,
            isin_code=isin_code,
            nav=nav,
            nav_previous=nav_previous,
            nav_date=nav_date,
            net_assets=net_assets,
            fetched_at=now,
        )
        session.add(result)
    if autocommit:
        session.commit()
        session.refresh(result)
    else:
        session.flush()
    return result


def bulk_upsert_nav(
    session: Session,
    fund_code: str,
    isin_code: str,
    rows: list[dict],
    *,
    autocommit: bool = True,
) -> int:
    """Bulk upsert NAV rows. Returns count of rows written."""
    normalized = fund_code.upper().strip()
    existing_stmt = select(MutualFundNav).where(MutualFundNav.fund_code == normalized)
    existing_by_date = {r.nav_date: r for r in session.exec(existing_stmt).all()}
    now = datetime.now(UTC)
    count = 0
    for row in rows:
        nav_date = row["date"]
        found = existing_by_date.get(nav_date)
        if found:
            found.nav = row["nav"]
            found.nav_previous = row.get("nav_previous")
            found.net_assets = row.get("net_assets")
            found.isin_code = isin_code
            found.fetched_at = now
            session.add(found)
        else:
            session.add(
                MutualFundNav(
                    fund_code=normalized,
                    isin_code=isin_code,
                    nav=row["nav"],
                    nav_previous=row.get("nav_previous"),
                    nav_date=nav_date,
                    net_assets=row.get("net_assets"),
                    fetched_at=now,
                )
            )
        count += 1
    if autocommit:
        session.commit()
    else:
        session.flush()
    return count
