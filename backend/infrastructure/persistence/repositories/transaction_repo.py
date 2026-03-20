"""Infrastructure — Transaction Repository."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlmodel import Session, select

if TYPE_CHECKING:
    from datetime import date

from domain.entities import ContributionLedgerEntry, Transaction

# ===========================================================================
# Transaction Repository
# ===========================================================================


def find_all_transactions(
    session: Session,
    ticker: str | None = None,
    account_id: int | None = None,
    holding_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int | None = 500,
) -> list[Transaction]:
    """查詢交易紀錄（支援篩選）。"""
    stmt = select(Transaction).order_by(Transaction.transaction_date.desc())
    if ticker:
        stmt = stmt.where(Transaction.ticker == ticker)
    if account_id is not None:
        stmt = stmt.where(Transaction.account_id == account_id)
    if holding_id is not None:
        stmt = stmt.where(Transaction.holding_id == holding_id)
    if start_date is not None:
        stmt = stmt.where(Transaction.transaction_date >= start_date)
    if end_date is not None:
        stmt = stmt.where(Transaction.transaction_date <= end_date)
    if limit is not None:
        stmt = stmt.limit(limit)
    return list(session.exec(stmt).all())


def find_transactions_by_account(
    session: Session, account_id: int, *, limit: int = 100, offset: int = 0
) -> list[Transaction]:
    """查詢指定帳戶的交易紀錄（依日期新到舊，含分頁）。"""
    stmt = (
        select(Transaction)
        .where(Transaction.account_id == account_id)
        .order_by(Transaction.transaction_date.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(session.exec(stmt).all())


def delete_transactions_by_account(session: Session, account_id: int) -> int:
    """刪除指定帳戶的所有交易紀錄（不 commit）。"""
    transactions = find_all_transactions(session, account_id=account_id, limit=None)
    for txn in transactions:
        session.delete(txn)
    return len(transactions)


def find_transaction_by_id(session: Session, txn_id: int) -> Transaction | None:
    """根據 ID 查詢單一交易紀錄。"""
    return session.get(Transaction, txn_id)


def save_transaction(session: Session, txn: Transaction) -> Transaction:
    """新增或更新交易紀錄（含 refresh）。"""
    session.add(txn)
    session.commit()
    session.refresh(txn)
    return txn


def delete_transaction(session: Session, txn: Transaction) -> None:
    """刪除交易紀錄。"""
    session.delete(txn)
    session.commit()


# ===========================================================================
# ContributionLedgerEntry Repository
# ===========================================================================


def find_ledger_entry_by_transaction_and_type(
    session: Session,
    transaction_id: int,
    entry_type: str,
) -> ContributionLedgerEntry | None:
    """Find one ledger entry by transaction id and entry type."""
    stmt = (
        select(ContributionLedgerEntry)
        .where(ContributionLedgerEntry.transaction_id == transaction_id)
        .where(ContributionLedgerEntry.entry_type == entry_type)
        .order_by(ContributionLedgerEntry.id.desc())
    )
    return session.exec(stmt).first()


def find_ledger_entries(
    session: Session,
    user_id: str,
) -> list[ContributionLedgerEntry]:
    """All ledger entries for one user ordered by creation time."""
    stmt = (
        select(ContributionLedgerEntry)
        .where(ContributionLedgerEntry.user_id == user_id)
        .order_by(ContributionLedgerEntry.created_at, ContributionLedgerEntry.id)
    )
    return list(session.exec(stmt).all())


def find_ledger_entries_by_wrapper(
    session: Session,
    user_id: str,
    wrapper: str,
    year: int | None = None,
) -> list[ContributionLedgerEntry]:
    """Ledger entries filtered by wrapper and optional fiscal year."""
    stmt = (
        select(ContributionLedgerEntry)
        .where(ContributionLedgerEntry.user_id == user_id)
        .where(ContributionLedgerEntry.tax_wrapper == wrapper)
    )
    if year is not None:
        stmt = stmt.where(ContributionLedgerEntry.fiscal_year == year)
    stmt = stmt.order_by(ContributionLedgerEntry.created_at, ContributionLedgerEntry.id)
    return list(session.exec(stmt).all())


def create_ledger_entry(
    session: Session,
    entry: ContributionLedgerEntry,
    *,
    autocommit: bool = True,
) -> ContributionLedgerEntry:
    """Create one contribution ledger entry."""
    session.add(entry)
    if autocommit:
        session.commit()
    else:
        session.flush()
    session.refresh(entry)
    return entry


def delete_ledger_entries_by_transaction(
    session: Session,
    transaction_id: int,
) -> int:
    """Delete all ledger entries for one transaction. Returns deleted count."""
    entries = session.exec(
        select(ContributionLedgerEntry).where(
            ContributionLedgerEntry.transaction_id == transaction_id
        )
    ).all()
    count = len(entries)
    for entry in entries:
        session.delete(entry)
    return count
