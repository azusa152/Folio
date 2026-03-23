"""Infrastructure — Account Repository."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Session, select

from domain.entities import Account

# ===========================================================================
# Account Repository
# ===========================================================================


def find_all_accounts(session: Session, active_only: bool = True) -> list[Account]:
    """查詢帳戶（預設僅啟用中，依名稱排序）。"""
    stmt = select(Account).order_by(Account.name)
    if active_only:
        stmt = stmt.where(Account.is_active == True)  # noqa: E712
    return list(session.exec(stmt).all())


def find_account_by_id(session: Session, account_id: int) -> Account | None:
    """根據 ID 查詢單一帳戶。"""
    return session.get(Account, account_id)


def save_account(session: Session, account: Account) -> Account:
    """新增或更新帳戶（含 refresh）。"""
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


def deactivate_account(session: Session, account: Account) -> None:
    """軟刪除帳戶（設為停用）。"""
    account.is_active = False
    account.updated_at = datetime.now(UTC)
    session.add(account)
    session.commit()
