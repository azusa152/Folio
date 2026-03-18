"""
Application — Holding Service。
封裝持倉的 CRUD 與匯入/匯出邏輯，路由層不直接存取 ORM。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, TypedDict

from fastapi import HTTPException

if TYPE_CHECKING:
    from sqlmodel import Session

    from domain.entities import Holding

from application.portfolio.pricing_service import (
    build_nav_cache as _build_nav_cache,
)
from application.portfolio.pricing_service import (
    resolve_holding_price as _resolve_holding_price,
)
from domain.constants import ERROR_ACCOUNT_NOT_FOUND
from i18n import t
from infrastructure import repositories as repo
from logging_config import get_logger

logger = get_logger(__name__)

SellableValueSource = Literal["live_price", "cost_basis", "unavailable"]


class SellablePositionPayload(TypedDict):
    ticker: str
    fund_name: str
    quantity: float
    cost_basis: float | None
    current_price: float | None
    market_value: float | None
    currency: str
    value_source: SellableValueSource


class SellablePositionsPayload(TypedDict):
    items: list[SellablePositionPayload]
    count: int


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _holding_to_dict(h: Holding) -> dict:
    return {
        "id": h.id,
        "ticker": h.ticker,
        "coingecko_id": h.coingecko_id,
        "category": h.category,
        "quantity": h.quantity,
        "cost_basis": h.cost_basis,
        "broker": h.broker,
        "account_id": h.account_id,
        "currency": h.currency,
        "account_type": h.account_type,
        "is_cash": h.is_cash,
        "purchase_fx_rate": h.purchase_fx_rate,
        "updated_at": h.updated_at.isoformat(),
    }


def _ensure_account_exists(session: Session, account_id: int, lang: str) -> None:
    if repo.find_account_by_id(session, account_id) is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": ERROR_ACCOUNT_NOT_FOUND,
                "detail": t("account.not_found", lang=lang),
            },
        )


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------


def list_holdings(session: Session) -> list[dict]:
    """Return all holdings as dicts, ordered by id."""
    holdings = repo.find_holdings_for_active_accounts(session, include_unlinked=False)
    return [_holding_to_dict(h) for h in holdings]


def get_holdings_by_account(session: Session, account_id: int, lang: str) -> list[dict]:
    """Return enriched holdings for a specific account."""
    _ensure_account_exists(session, account_id, lang)
    holdings = repo.find_holdings_by_account(session, account_id)
    return [_holding_to_dict(h) for h in holdings]


def _fund_name_or_ticker(ticker: str, names_by_ticker: dict[str, str]) -> str:
    """Return the curated fund name, or fallback to ticker.

    Resolution order:
    1. EligibleAsset.fund_name  (pre-normalized NFKC, curated NISA asset list)
    2. ticker                   (final fallback — always available)

    Note: The watchlist Stock entity stores no human-readable name, so
    EligibleAsset.fund_name is the only local curated name source.
    """
    return names_by_ticker.get(ticker) or ticker


def get_sellable_positions(
    session: Session, account_id: int, lang: str
) -> SellablePositionsPayload:
    """Return sellable non-cash holdings enriched with names and market values."""
    _ensure_account_exists(session, account_id, lang)
    holdings = [
        h
        for h in repo.find_holdings_by_account(session, account_id)
        if not h.is_cash and h.quantity > 0
    ]
    if not holdings:
        return {"items": [], "count": 0}

    names_by_ticker = repo.find_fund_names_by_tickers(
        session, {h.ticker for h in holdings}
    )
    nav_cache = _build_nav_cache(session, holdings)
    items: list[SellablePositionPayload] = []

    for holding in holdings:
        normalized_ticker = holding.ticker.upper().strip()
        fund_name = _fund_name_or_ticker(normalized_ticker, names_by_ticker)
        current_price: float | None = None
        market_value: float | None = None
        value_source: SellableValueSource = "unavailable"

        try:
            resolved_price = _resolve_holding_price(holding, nav_cache)
            if isinstance(resolved_price, (int, float)):
                current_price = float(resolved_price)
                market_value = float(holding.quantity) * current_price
                value_source = "live_price"
        except Exception as exc:  # pragma: no cover - external adapters are best effort
            logger.warning(
                "sellable position price resolution failed for %s: %s",
                normalized_ticker,
                exc,
            )

        if market_value is None and holding.cost_basis is not None:
            market_value = float(holding.quantity) * float(holding.cost_basis)
            value_source = "cost_basis"

        items.append(
            {
                "ticker": normalized_ticker,
                "fund_name": fund_name,
                "quantity": float(holding.quantity),
                "cost_basis": float(holding.cost_basis)
                if holding.cost_basis is not None
                else None,
                "current_price": current_price,
                "market_value": market_value,
                "currency": holding.currency or "USD",
                "value_source": value_source,
            }
        )

    items.sort(
        key=lambda item: (
            (
                -item["market_value"]
                if isinstance(item["market_value"], (int, float))
                else float("inf")
            ),
            item["ticker"],
        )
    )

    return {"items": items, "count": len(items)}
