"""
Ledger migration: backfill OPENING_BALANCE transactions for existing holdings.

Usage:
    cd backend && python -m scripts.migrate_ledger [--dry-run]

Idempotent: skips holdings that already have an OPENING_BALANCE transaction.
"""

from __future__ import annotations

import argparse
from datetime import date
from typing import Any

from sqlalchemy.exc import OperationalError
from sqlmodel import Session, select

from domain.constants import DEFAULT_ACCOUNT_NAME, DEFAULT_USER_ID
from domain.entities import Account, Holding, Transaction
from domain.enums import StockCategory, TransactionType
from infrastructure.database import engine
from logging_config import get_logger

logger = get_logger(__name__)


def _create_default_account(session: Session) -> Account:
    account = Account(
        user_id=DEFAULT_USER_ID,
        name=DEFAULT_ACCOUNT_NAME,
        broker=DEFAULT_ACCOUNT_NAME,
        account_type="brokerage",
        currency="USD",
        institution="",
        note="",
        is_active=True,
    )
    session.add(account)
    session.flush()

    # Keep account bootstrapping consistent with normal account creation flow.
    cash_holding = Holding(
        user_id=DEFAULT_USER_ID,
        ticker="USD",
        category=StockCategory.CASH,
        quantity=0.0,
        cost_basis=1.0,
        broker=DEFAULT_ACCOUNT_NAME,
        account_id=account.id,
        currency="USD",
        account_type="brokerage",
        is_cash=True,
        purchase_fx_rate=1.0,
    )
    session.add(cash_holding)
    session.flush()
    return account


def _get_or_prepare_default_account(session: Session) -> Account:
    existing = session.exec(
        select(Account).where(
            Account.name == DEFAULT_ACCOUNT_NAME,
            Account.broker == DEFAULT_ACCOUNT_NAME,
        )
    ).first()
    if existing is not None:
        return existing

    return _create_default_account(session)


def migrate(dry_run: bool = False) -> dict[str, int]:
    stats: dict[str, int] = {
        "orphan_holdings": 0,
        "orphan_transactions": 0,
        "opening_balances": 0,
        "skipped": 0,
    }

    with Session(engine) as session:
        default_account = _get_or_prepare_default_account(session)

        orphan_holdings = session.exec(
            select(Holding).where(Holding.account_id.is_(None))
        ).all()
        for holding in orphan_holdings:
            holding.account_id = default_account.id
            session.add(holding)
            stats["orphan_holdings"] += 1

        orphan_transactions = session.exec(
            select(Transaction).where(Transaction.account_id.is_(None))
        ).all()
        for txn in orphan_transactions:
            txn.account_id = default_account.id
            session.add(txn)
            stats["orphan_transactions"] += 1

        holdings = session.exec(select(Holding)).all()
        for holding in holdings:
            # Defensive handling: skip zero/negative legacy quantities to avoid
            # generating invalid opening-balance rows for corrupted data.
            if holding.quantity <= 0:
                stats["skipped"] += 1
                continue

            # Idempotency key uses holding_id to avoid false positives when the
            # same ticker exists across multiple holdings/accounts.
            has_opening_balance = session.exec(
                select(Transaction)
                .where(Transaction.transaction_type == TransactionType.OPENING_BALANCE)
                .where(Transaction.holding_id == holding.id)
            ).first()
            if has_opening_balance is not None:
                stats["skipped"] += 1
                continue

            price = 1.0 if holding.is_cash else float(holding.cost_basis or 0.0)
            total_amount = (
                float(holding.quantity)
                if holding.is_cash
                else float(holding.quantity) * float(holding.cost_basis or 0.0)
            )

            opening_balance = Transaction(
                user_id=holding.user_id,
                account_id=holding.account_id,
                holding_id=holding.id,
                ticker=holding.ticker,
                transaction_type=TransactionType.OPENING_BALANCE,
                quantity=float(holding.quantity),
                price=price,
                total_amount=total_amount,
                currency=holding.currency,
                fee=0.0,
                note="Auto-generated opening balance from ledger migration",
                transaction_date=date.today(),
            )
            session.add(opening_balance)
            stats["opening_balances"] += 1

        if dry_run:
            session.rollback()
            logger.info("[DRY RUN] Ledger migration preview：%s", stats)
        else:
            session.commit()
            logger.info("Ledger migration 完成：%s", stats)

    return stats


def main(args: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Backfill OPENING_BALANCE transactions for legacy holdings.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without commit")
    parsed = parser.parse_args(args)
    try:
        result: dict[str, Any] = migrate(dry_run=parsed.dry_run)
    except OperationalError as exc:
        logger.error("Ledger migration 失敗：請先完成資料庫初始化。錯誤：%s", exc)
        return 1
    logger.info("遷移結果：%s", result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
