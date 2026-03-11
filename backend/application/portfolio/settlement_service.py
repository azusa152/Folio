"""Transaction cash settlement helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import HTTPException

if TYPE_CHECKING:
    from sqlmodel import Session

from domain.constants import (
    DEFAULT_USER_ID,
    ERROR_ACCOUNT_NOT_FOUND,
    ERROR_INSUFFICIENT_BALANCE,
    ERROR_INVALID_INPUT,
)
from domain.entities import Holding, Transaction
from domain.enums import StockCategory, TransactionType
from i18n import t
from infrastructure import repositories as repo

AUTO_CREATE_CASH_TYPES = {
    TransactionType.SELL,
    TransactionType.DIVIDEND,
    TransactionType.DEPOSIT,
}


def settle_transaction(session: Session, txn_data: dict, lang: str) -> Transaction:
    """Apply account cash settlement and persist transaction atomically."""
    account_id = txn_data.get("account_id")
    if account_id is None:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": ERROR_INVALID_INPUT,
                "detail": t("common.validation_error", lang=lang),
            },
        )

    account = repo.find_account_by_id(session, int(account_id))
    if account is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": ERROR_ACCOUNT_NOT_FOUND,
                "detail": t("account.not_found", lang=lang),
            },
        )

    txn_type = TransactionType(txn_data["transaction_type"])
    currency = str(txn_data.get("currency", "USD")).upper().strip() or "USD"
    txn_data["currency"] = currency

    cash_holding = repo.find_cash_holding_by_account_and_currency(
        session, int(account_id), currency
    )
    if cash_holding is None and txn_type in AUTO_CREATE_CASH_TYPES:
        cash_holding = Holding(
            user_id=DEFAULT_USER_ID,
            ticker=currency,
            category=StockCategory.CASH,
            quantity=0.0,
            cost_basis=1.0,
            broker=account.broker,
            account_id=int(account_id),
            currency=currency,
            account_type=account.account_type,
            is_cash=True,
            purchase_fx_rate=1.0,
        )
        session.add(cash_holding)

    if cash_holding is None:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": ERROR_INVALID_INPUT,
                "detail": t("transaction.cash_holding_not_found", lang=lang),
            },
        )

    delta = _cash_delta(txn_type, txn_data)
    next_balance = cash_holding.quantity + delta
    if next_balance < -1e-9:
        _raise_insufficient_balance(
            lang=lang,
            available=cash_holding.quantity,
            required=abs(delta),
        )

    cash_holding.quantity = next_balance
    cash_holding.updated_at = datetime.now(UTC)

    txn = Transaction(**txn_data)
    session.add(cash_holding)
    session.add(txn)
    session.commit()
    session.refresh(txn)
    return txn


def reverse_settlement(session: Session, txn: Transaction, lang: str) -> None:
    """Reverse previously-applied settlement for a transaction."""
    if txn.account_id is None:
        return

    cash_holding = repo.find_cash_holding_by_account_and_currency(
        session, int(txn.account_id), txn.currency
    )
    if cash_holding is None:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": ERROR_INVALID_INPUT,
                "detail": t("transaction.cash_holding_not_found", lang=lang),
            },
        )

    delta = -_cash_delta(TransactionType(txn.transaction_type), txn.model_dump())
    next_balance = cash_holding.quantity + delta
    if next_balance < -1e-9:
        _raise_insufficient_balance(
            lang=lang,
            available=cash_holding.quantity,
            required=abs(delta),
        )

    cash_holding.quantity = next_balance
    cash_holding.updated_at = datetime.now(UTC)
    session.add(cash_holding)


def _cash_delta(txn_type: TransactionType, txn_data: dict) -> float:
    total_amount = float(txn_data.get("total_amount", 0) or 0)
    fee = float(txn_data.get("fee", 0) or 0)
    net_credit = total_amount - fee
    net_debit = total_amount + fee

    if txn_type == TransactionType.BUY:
        return -net_debit
    if txn_type == TransactionType.SELL:
        return net_credit
    if txn_type == TransactionType.DIVIDEND:
        return net_credit
    if txn_type == TransactionType.DEPOSIT:
        return net_credit
    if txn_type == TransactionType.WITHDRAWAL:
        return -net_debit
    return 0.0


def _raise_insufficient_balance(
    *, lang: str, available: float, required: float
) -> None:
    raise HTTPException(
        status_code=422,
        detail={
            "error_code": ERROR_INSUFFICIENT_BALANCE,
            "detail": t("transaction.insufficient_balance", lang=lang),
            "available": max(0.0, round(available, 8)),
            "required": max(0.0, round(required, 8)),
        },
    )
