"""
Application — Holding Service。
封裝持倉的 CRUD 與匯入/匯出邏輯，路由層不直接存取 ORM。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import HTTPException

if TYPE_CHECKING:
    from sqlmodel import Session

    from domain.entities import Holding

from domain.constants import ERROR_ACCOUNT_NOT_FOUND
from i18n import t
from infrastructure import repositories as repo

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
