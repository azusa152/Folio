"""帳戶管理與持倉分組服務。"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import HTTPException

if TYPE_CHECKING:
    from sqlmodel import Session

from domain.constants import ERROR_ACCOUNT_NOT_FOUND
from domain.entities import Account
from i18n import t
from infrastructure import repositories as repo
from logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _acct_to_dict(acct: Account) -> dict:
    return {
        "id": acct.id,
        "user_id": acct.user_id,
        "name": acct.name,
        "broker": acct.broker,
        "account_type": acct.account_type,
        "currency": acct.currency,
        "institution": acct.institution,
        "note": acct.note,
        "is_active": acct.is_active,
        "created_at": acct.created_at.isoformat(),
        "updated_at": acct.updated_at.isoformat(),
    }


def _get_account_or_raise(session: Session, account_id: int, lang: str) -> Account:
    account = repo.find_account_by_id(session, account_id)
    if account is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": ERROR_ACCOUNT_NOT_FOUND,
                "detail": t("account.not_found", lang=lang),
            },
        )
    return account


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------


def list_accounts(session: Session) -> list[dict]:
    """Return all active accounts as dicts."""
    return [_acct_to_dict(a) for a in repo.find_all_accounts(session)]


def create_account(session: Session, data: dict, lang: str) -> dict:
    """Create a new account. Returns the created account dict."""
    account = Account(**data)
    saved = repo.save_account(session, account)
    logger.info("新增帳戶：%s（%s）", saved.name, saved.broker)
    return _acct_to_dict(saved)


def update_account(session: Session, account_id: int, data: dict, lang: str) -> dict:
    """Partially update an existing account. Only provided fields are overwritten."""
    account = _get_account_or_raise(session, account_id, lang)
    for key, value in data.items():
        if hasattr(account, key) and key not in ("id", "user_id", "created_at"):
            setattr(account, key, value)
    account.updated_at = datetime.now(UTC)
    saved = repo.save_account(session, account)
    return _acct_to_dict(saved)


def remove_account(session: Session, account_id: int, lang: str) -> None:
    """Soft-delete an account (set is_active = False)."""
    account = _get_account_or_raise(session, account_id, lang)
    repo.deactivate_account(session, account)
    logger.info("停用帳戶：%s (id=%d)", account.name, account_id)


def get_account_summary(session: Session) -> list[dict]:
    """Group holdings by account for aggregation view."""
    accounts = repo.find_all_accounts(session)
    holdings = repo.find_all_holdings(session)

    account_map: dict[int | None, list] = {a.id: [] for a in accounts}
    account_map[None] = []

    for h in holdings:
        bucket = h.account_id if h.account_id in account_map else None
        account_map[bucket].append(h)

    result = []
    for acct in accounts:
        acct_holdings = account_map.get(acct.id, [])
        result.append(
            {
                "account": _acct_to_dict(acct),
                "holdings_count": len(acct_holdings),
                "tickers": [h.ticker for h in acct_holdings],
            }
        )

    unlinked = account_map.get(None, [])
    if unlinked:
        result.append(
            {
                "account": None,
                "holdings_count": len(unlinked),
                "tickers": [h.ticker for h in unlinked],
            }
        )

    return result
