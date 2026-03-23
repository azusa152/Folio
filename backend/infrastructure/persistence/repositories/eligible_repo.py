"""Infrastructure — Eligible Asset Repository.

EligibleAsset, EligibleAssetSyncState, and ISIN lookup functions.
"""

from __future__ import annotations

import unicodedata
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_
from sqlmodel import Session, func, select

from domain.entities import EligibleAsset, EligibleAssetSyncState
from logging_config import get_logger

logger = get_logger(__name__)


def find_eligible_tickers(
    session: Session,
    wrapper: str,
    broker: str | None = None,
) -> set[str]:
    """Return active eligible tickers for one wrapper (broker-aware)."""
    stmt = select(EligibleAsset.ticker).where(
        EligibleAsset.tax_wrapper == wrapper,
        EligibleAsset.is_active == True,  # noqa: E712
    )
    if broker:
        stmt = stmt.where(
            or_(EligibleAsset.broker == broker, EligibleAsset.broker == None)  # noqa: E711
        )
    return {str(ticker).upper() for ticker in session.exec(stmt).all()}


def find_fund_names_by_tickers(
    session: Session,
    tickers: list[str] | set[str],
) -> dict[str, str]:
    """Return active eligible-asset fund names keyed by normalized ticker."""
    normalized_tickers = {
        str(ticker).strip().upper() for ticker in tickers if str(ticker).strip()
    }
    if not normalized_tickers:
        return {}

    stmt = (
        select(EligibleAsset.ticker, EligibleAsset.fund_name)
        .where(
            EligibleAsset.ticker.in_(normalized_tickers),  # pyright: ignore[reportAttributeAccessIssue]
            EligibleAsset.is_active == True,  # noqa: E712
        )
        .order_by(EligibleAsset.ticker, EligibleAsset.updated_at.desc())  # pyright: ignore[reportAttributeAccessIssue]
    )

    names_by_ticker: dict[str, str] = {}
    for ticker, fund_name in session.exec(stmt).all():
        normalized_ticker = str(ticker).strip().upper()
        normalized_name = str(fund_name or "").strip()
        if not normalized_ticker or not normalized_name:
            continue
        if normalized_ticker not in names_by_ticker:
            names_by_ticker[normalized_ticker] = normalized_name
    return names_by_ticker


def is_active_eligible_mutual_fund(session: Session, ticker: str) -> bool:
    """Return whether ticker has any active eligible mutual_fund record."""
    normalized_ticker = ticker.upper().strip()
    if not normalized_ticker:
        return False
    stmt = select(func.count()).where(
        EligibleAsset.ticker == normalized_ticker,
        EligibleAsset.is_active == True,  # noqa: E712
        EligibleAsset.asset_type == "mutual_fund",
    )
    return bool(session.exec(stmt).one() > 0)


def find_eligible_asset_by_ticker(
    session: Session,
    wrapper: str,
    ticker: str,
    broker: str | None = None,
) -> EligibleAsset | None:
    """Return one active eligible asset for an exact ticker match."""
    normalized_ticker = ticker.upper().strip()
    if not normalized_ticker:
        return None
    stmt = select(EligibleAsset).where(
        EligibleAsset.tax_wrapper == wrapper,
        EligibleAsset.ticker == normalized_ticker,
        EligibleAsset.is_active == True,  # noqa: E712
    )
    if broker:
        stmt = stmt.where(
            or_(EligibleAsset.broker == broker, EligibleAsset.broker == None)  # noqa: E711
        )
    return session.exec(stmt.order_by(EligibleAsset.broker.is_not(None).desc())).first()  # pyright: ignore[reportAttributeAccessIssue, reportOptionalMemberAccess]


def find_eligible_assets(
    session: Session,
    wrapper: str,
    broker: str | None = None,
    search: str | None = None,
    asset_type: str | None = None,
    limit: int = 50,
) -> list[EligibleAsset]:
    """Search active eligible assets with optional broker/text filters."""
    stmt = _build_eligible_assets_stmt(
        wrapper=wrapper,
        broker=broker,
        search=search,
        asset_type=asset_type,
    )
    stmt = stmt.order_by(EligibleAsset.ticker).limit(limit)
    return list(session.exec(stmt).all())


def count_eligible_assets(
    session: Session,
    wrapper: str,
    broker: str | None = None,
    search: str | None = None,
    asset_type: str | None = None,
) -> int:
    """Count active eligible assets with optional broker/text filters."""
    stmt = _build_eligible_assets_stmt(
        wrapper=wrapper,
        broker=broker,
        search=search,
        asset_type=asset_type,
    )
    count_stmt = select(func.count()).select_from(stmt.subquery())
    count_result = session.exec(count_stmt).one()
    return int(count_result or 0)


def _build_eligible_assets_stmt(
    *,
    wrapper: str,
    broker: str | None = None,
    search: str | None = None,
    asset_type: str | None = None,
):
    """Build base eligible-assets query with optional filters."""
    stmt = select(EligibleAsset).where(
        EligibleAsset.tax_wrapper == wrapper,
        EligibleAsset.is_active == True,  # noqa: E712
    )
    if broker:
        stmt = stmt.where(
            or_(EligibleAsset.broker == broker, EligibleAsset.broker == None)  # noqa: E711
        )
    normalized_asset_type = asset_type.strip().lower() if asset_type else ""
    if normalized_asset_type:
        stmt = stmt.where(EligibleAsset.asset_type == normalized_asset_type)
    normalized_search_raw = search.strip() if search else ""
    if normalized_search_raw:
        normalized_search = unicodedata.normalize("NFKC", normalized_search_raw).lower()
        pattern = f"%{normalized_search}%"
        stmt = stmt.where(
            or_(
                EligibleAsset.ticker.ilike(pattern),  # pyright: ignore[reportAttributeAccessIssue]
                EligibleAsset.fund_name.ilike(pattern),  # pyright: ignore[reportAttributeAccessIssue]
            )
        )
    return stmt


def upsert_eligible_assets(
    session: Session,
    wrapper: str,
    rows: list[dict],
    *,
    broker: str | None = None,
    source: str = "unknown",
    autocommit: bool = True,
) -> dict[str, int]:
    """Idempotent bulk upsert and deactivate-missing for eligible assets."""
    _CANONICAL_ASSET_TYPES = {"mutual_fund", "etf", "stock", "reit"}

    def _canonical_asset_type(raw: Any) -> str:
        normalized = str(raw or "mutual_fund").strip().lower() or "mutual_fund"
        if normalized not in _CANONICAL_ASSET_TYPES:
            logger.warning(
                "upsert_eligible_assets: unknown asset_type %r — defaulting to 'mutual_fund'",
                raw,
            )
            return "mutual_fund"
        return normalized

    # Deduplicate by ticker before processing; last occurrence wins.
    deduped: dict[str, dict[str, Any]] = {}
    for row in rows:
        ticker = str(row.get("ticker", "")).strip().upper()
        if not ticker:
            continue
        deduped[ticker] = {
            "ticker": ticker,
            "fund_name": unicodedata.normalize(
                "NFKC", str(row.get("fund_name", "")).strip()
            ),
            "asset_type": _canonical_asset_type(row.get("asset_type")),
            "trust_fee_pct": row.get("trust_fee_pct"),
            "isin_code": row.get("isin_code"),
        }
    normalized_rows = list(deduped.values())

    active_tickers = {row["ticker"] for row in normalized_rows}
    existing = session.exec(
        select(EligibleAsset).where(
            EligibleAsset.tax_wrapper == wrapper,
            EligibleAsset.broker == broker,
        )
    ).all()
    existing_by_ticker = {asset.ticker: asset for asset in existing}

    added = 0
    updated = 0
    deactivated = 0

    for row in normalized_rows:
        found = existing_by_ticker.get(row["ticker"])
        if found is None:
            session.add(
                EligibleAsset(
                    tax_wrapper=wrapper,
                    ticker=row["ticker"],
                    fund_name=row["fund_name"],
                    asset_type=row["asset_type"],
                    broker=broker,
                    trust_fee_pct=row["trust_fee_pct"],
                    isin_code=row.get("isin_code"),
                    is_active=True,
                    updated_at=datetime.now(UTC),
                )
            )
            added += 1
            continue

        new_isin = row.get("isin_code")
        changed = (
            found.fund_name != row["fund_name"]
            or found.asset_type != row["asset_type"]
            or found.trust_fee_pct != row["trust_fee_pct"]
            or (new_isin is not None and found.isin_code != new_isin)
            or not found.is_active
        )
        if changed:
            found.fund_name = row["fund_name"]
            found.asset_type = row["asset_type"]
            found.trust_fee_pct = row["trust_fee_pct"]
            if new_isin is not None:
                found.isin_code = new_isin
            found.is_active = True
            found.updated_at = datetime.now(UTC)
            session.add(found)
            updated += 1

    for asset in existing:
        if asset.ticker not in active_tickers and asset.is_active:
            asset.is_active = False
            asset.updated_at = datetime.now(UTC)
            session.add(asset)
            deactivated += 1

    if autocommit:
        session.commit()
    else:
        session.flush()

    if not broker:
        sync_state = session.get(EligibleAssetSyncState, wrapper)
        now = datetime.now(UTC)
        if sync_state is None:
            session.add(
                EligibleAssetSyncState(
                    tax_wrapper=wrapper,
                    source=source,
                    last_refreshed_at=now,
                    updated_at=now,
                )
            )
        else:
            sync_state.source = source
            sync_state.last_refreshed_at = now
            sync_state.updated_at = now
            session.add(sync_state)
        if autocommit:
            session.commit()
        else:
            session.flush()

    return {
        "added": added,
        "updated": updated,
        "deactivated": deactivated,
    }


def get_eligible_assets_metadata(
    session: Session,
    wrapper: str,
) -> dict[str, object]:
    """Get active count and sync metadata for one wrapper."""
    normalized_wrapper = wrapper.strip().lower()
    count_stmt = select(func.count()).where(
        EligibleAsset.tax_wrapper == normalized_wrapper,
        EligibleAsset.is_active == True,  # noqa: E712
    )
    active_count = int(session.exec(count_stmt).first() or 0)
    sync_state = session.get(EligibleAssetSyncState, normalized_wrapper)
    last_refreshed_at = sync_state.last_refreshed_at if sync_state else None
    source = sync_state.source if sync_state else "unknown"
    return {
        "wrapper": normalized_wrapper,
        "count": active_count,
        "last_refreshed_at": last_refreshed_at,
        "source": source,
    }


# ===========================================================================
# ISIN / Fund Code lookup (EligibleAsset-backed)
# ===========================================================================


def find_isin_for_ticker(session: Session, ticker: str) -> str | None:
    """Look up ISIN code from EligibleAsset for a given ticker."""
    normalized = ticker.upper().strip()
    strict_stmt = (
        select(EligibleAsset.isin_code)
        .where(
            EligibleAsset.ticker == normalized,
            EligibleAsset.is_active == True,  # noqa: E712
            EligibleAsset.isin_code != None,  # noqa: E711
        )
        .limit(1)
    )
    isin = session.exec(strict_stmt).first()
    if isin:
        return isin

    # Fallback: allow inactive rows so historical/temporarily deactivated
    # eligible assets can still provide ISIN for NAV sync.
    fallback_stmt = (
        select(EligibleAsset.isin_code)
        .where(
            EligibleAsset.ticker == normalized,
            EligibleAsset.isin_code != None,  # noqa: E711
        )
        .limit(1)
    )
    return session.exec(fallback_stmt).first()


def find_fund_code_by_isin(session: Session, isin: str) -> str | None:
    """Find a likely 8-char fund-code ticker for a given ISIN."""
    normalized = isin.strip()
    if not normalized:
        return None

    # Prefer active rows first, then fallback to inactive.
    active_stmt = select(EligibleAsset.ticker).where(
        EligibleAsset.isin_code == normalized,
        EligibleAsset.is_active == True,  # noqa: E712
    )
    active_tickers = [str(t).strip().upper() for t in session.exec(active_stmt).all()]
    for ticker in active_tickers:
        if len(ticker) == 8 and ticker.isalnum():
            return ticker

    fallback_stmt = select(EligibleAsset.ticker).where(
        EligibleAsset.isin_code == normalized
    )
    tickers = [str(t).strip().upper() for t in session.exec(fallback_stmt).all()]
    for ticker in tickers:
        if len(ticker) == 8 and ticker.isalnum():
            return ticker
    return None


def backfill_isin_for_ticker(
    session: Session, ticker: str, isin: str, *, autocommit: bool = True
) -> bool:
    """Set ``isin_code`` on matching EligibleAsset rows that lack one."""
    normalized = ticker.upper().strip()
    stmt = select(EligibleAsset).where(
        EligibleAsset.ticker == normalized,
        or_(EligibleAsset.isin_code == None, EligibleAsset.isin_code == ""),  # noqa: E711
    )
    rows = list(session.exec(stmt).all())
    if not rows:
        return False
    for row in rows:
        row.isin_code = isin
    if autocommit:
        session.commit()
    return True
