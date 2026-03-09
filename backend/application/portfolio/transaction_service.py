"""交易紀錄 CRUD 與聚合服務。"""

from datetime import date

from fastapi import HTTPException
from sqlmodel import Session

from domain.constants import ERROR_INVALID_INPUT, ERROR_TRANSACTION_NOT_FOUND
from domain.core.entities import Transaction
from domain.enums import TransactionType
from i18n import t
from infrastructure.persistence.repositories import (
    delete_transaction,
    find_all_transactions,
    find_transaction_by_id,
    save_transaction,
)
from logging_config import get_logger

logger = get_logger(__name__)


def list_transactions(
    session: Session,
    *,
    ticker: str | None = None,
    holding_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 500,
) -> list[dict]:
    txns = find_all_transactions(
        session,
        ticker=ticker,
        holding_id=holding_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    return [_to_dict(txn) for txn in txns]


def create_transaction(session: Session, data: dict, lang: str) -> dict:
    raw_type = data.get("transaction_type", "")
    try:
        data["transaction_type"] = TransactionType(str(raw_type).upper())
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": ERROR_INVALID_INPUT,
                "detail": t("common.validation_error", lang=lang),
            },
        ) from None
    txn = Transaction(**data)
    saved = save_transaction(session, txn)
    logger.info(
        "交易紀錄已建立：id=%s ticker=%s type=%s",
        saved.id,
        saved.ticker,
        saved.transaction_type,
    )
    return _to_dict(saved)


def remove_transaction(session: Session, txn_id: int, lang: str) -> None:
    txn = find_transaction_by_id(session, txn_id)
    if txn is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": ERROR_TRANSACTION_NOT_FOUND,
                "detail": t("transaction.not_found", lang=lang),
            },
        )
    delete_transaction(session, txn)
    logger.info("交易紀錄已刪除：id=%s", txn_id)


def get_transaction(session: Session, txn_id: int, lang: str) -> dict:
    txn = find_transaction_by_id(session, txn_id)
    if txn is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": ERROR_TRANSACTION_NOT_FOUND,
                "detail": t("transaction.not_found", lang=lang),
            },
        )
    return _to_dict(txn)


def _to_dict(txn: Transaction) -> dict:
    return {
        "id": txn.id,
        "user_id": txn.user_id,
        "holding_id": txn.holding_id,
        "ticker": txn.ticker,
        "transaction_type": txn.transaction_type,
        "quantity": txn.quantity,
        "price": txn.price,
        "total_amount": txn.total_amount,
        "currency": txn.currency,
        "fx_rate": txn.fx_rate,
        "fee": txn.fee,
        "note": txn.note,
        "transaction_date": txn.transaction_date.isoformat(),
        "created_at": txn.created_at.isoformat(),
    }
