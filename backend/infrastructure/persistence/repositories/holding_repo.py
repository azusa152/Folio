"""Infrastructure — Holding Repository."""

from __future__ import annotations

from sqlmodel import Session, select

from domain.constants import HOLDING_QUANTITY_EPSILON
from domain.entities import Account, Holding

# ===========================================================================
# Holding Repository
# ===========================================================================


def find_all_holdings(
    session: Session, *, include_zero_quantity: bool = True
) -> list[Holding]:
    """查詢所有持倉（依 ID 排序，可選擇是否包含 0/負數數量）。"""
    stmt = select(Holding).order_by(Holding.id)
    if not include_zero_quantity:
        stmt = stmt.where(Holding.quantity > HOLDING_QUANTITY_EPSILON)
    return list(session.exec(stmt).all())


def find_holdings_for_active_accounts(
    session: Session,
    *,
    include_unlinked: bool = True,
    user_id: str | None = None,
    include_zero_quantity: bool = False,
) -> list[Holding]:
    """查詢啟用帳戶持倉（可選擇是否含未綁定資料與 0/負數數量）。"""
    stmt = select(Holding).order_by(Holding.id)
    if include_unlinked:
        stmt = stmt.outerjoin(Account, Holding.account_id == Account.id).where(
            (Holding.account_id == None)  # noqa: E711
            | (Account.is_active == True)  # noqa: E712
        )
    else:
        stmt = stmt.join(Account, Holding.account_id == Account.id).where(
            Account.is_active == True  # noqa: E712
        )
    if user_id is not None:
        stmt = stmt.where(Holding.user_id == user_id)
    if not include_zero_quantity:
        stmt = stmt.where(Holding.quantity > HOLDING_QUANTITY_EPSILON)
    return list(session.exec(stmt).all())


def find_holdings_by_account(
    session: Session,
    account_id: int,
    *,
    include_zero_quantity: bool = False,
) -> list[Holding]:
    """查詢指定帳戶的持倉（依 ticker 排序，可排除 0/負數數量）。"""
    stmt = (
        select(Holding).where(Holding.account_id == account_id).order_by(Holding.ticker)
    )
    if not include_zero_quantity:
        stmt = stmt.where(Holding.quantity > HOLDING_QUANTITY_EPSILON)
    return list(session.exec(stmt).all())


def find_holding_by_id(session: Session, holding_id: int) -> Holding | None:
    """根據 ID 查詢單一持倉。"""
    return session.get(Holding, holding_id)


def find_cash_holding_by_account_and_currency(
    session: Session, account_id: int, currency: str
) -> Holding | None:
    """查詢指定帳戶與幣別的現金持倉。"""
    normalized_currency = currency.upper().strip()
    stmt = select(Holding).where(
        Holding.account_id == account_id,
        Holding.is_cash == True,  # noqa: E712
        Holding.currency == normalized_currency,
    )
    return session.exec(stmt).first()


def find_stock_holding_by_account_and_ticker(
    session: Session, account_id: int, ticker: str
) -> Holding | None:
    """查詢指定帳戶與代號的非現金持倉。"""
    normalized_ticker = ticker.upper().strip()
    exact_stmt = (
        select(Holding)
        .where(Holding.account_id == account_id)
        .where(Holding.ticker == normalized_ticker)
        .where(Holding.is_cash == False)  # noqa: E712
    )
    exact = session.exec(exact_stmt).first()
    if exact is not None:
        return exact

    # Backward-compat fallback for legacy rows that were not normalized to uppercase.
    nocase_stmt = (
        select(Holding)
        .where(Holding.account_id == account_id)
        .where(Holding.ticker.collate("NOCASE") == normalized_ticker)  # pyright: ignore[reportAttributeAccessIssue]
        .where(Holding.is_cash == False)  # noqa: E712
    )
    return session.exec(nocase_stmt).first()


def find_holding_by_ticker(session: Session, ticker: str) -> Holding | None:
    """Return the first Holding matching the ticker (any account), or None."""
    return session.exec(
        select(Holding).where(Holding.ticker == ticker.upper().strip()).limit(1)
    ).first()


def save_holding(session: Session, holding: Holding) -> Holding:
    """新增或更新持倉（含 refresh）。"""
    session.add(holding)
    session.commit()
    session.refresh(holding)
    return holding


def delete_holding(session: Session, holding: Holding) -> None:
    """刪除一筆持倉。"""
    session.delete(holding)
    session.commit()


def delete_all_holdings(session: Session) -> int:
    """刪除所有持倉，回傳刪除筆數。"""
    holdings = find_all_holdings(session)
    count = len(holdings)
    for h in holdings:
        session.delete(h)
    session.commit()
    return count


def delete_holdings_by_account(session: Session, account_id: int) -> int:
    """刪除指定帳戶的所有持倉，回傳刪除筆數。"""
    stmt = select(Holding).where(Holding.account_id == account_id)
    holdings = list(session.exec(stmt).all())
    count = len(holdings)
    for h in holdings:
        session.delete(h)
    session.commit()
    return count
