"""交易紀錄 CRUD 與聚合服務。"""

from datetime import date
from typing import Literal

from fastapi import HTTPException
from sqlmodel import Session

from application.portfolio.settlement_service import (
    reverse_settlement,
    settle_transaction,
)
from application.stock.stock_service import ensure_stock_on_radar
from domain.constants import (
    ERROR_ACCOUNT_NOT_FOUND,
    ERROR_INVALID_INPUT,
    ERROR_TRANSACTION_NOT_FOUND,
    GENERIC_VALIDATION_ERROR,
)
from domain.core.entities import Transaction
from domain.enums import StockCategory, TransactionType
from i18n import t
from infrastructure import repositories as repo
from logging_config import get_logger

logger = get_logger(__name__)


def list_transactions(
    session: Session,
    *,
    ticker: str | None = None,
    account_id: int | None = None,
    holding_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int | None = 500,
) -> list[dict]:
    txns = repo.find_all_transactions(
        session,
        ticker=ticker,
        account_id=account_id,
        holding_id=holding_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    holding_meta_cache: dict[int, tuple[str | None, bool | None]] = {}
    return [
        _to_dict(txn, session=session, holding_meta_cache=holding_meta_cache)
        for txn in txns
    ]


def list_transactions_by_account(
    session: Session,
    account_id: int,
    *,
    lang: str,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    account = repo.find_account_by_id(session, account_id)
    if account is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": ERROR_ACCOUNT_NOT_FOUND,
                "detail": t("account.not_found", lang=lang),
            },
        )
    txns = repo.find_transactions_by_account(
        session, account_id, limit=limit, offset=offset
    )
    holding_meta_cache: dict[int, tuple[str | None, bool | None]] = {}
    return [
        _to_dict(txn, session=session, holding_meta_cache=holding_meta_cache)
        for txn in txns
    ]


def create_transaction(
    session: Session, data: dict, lang: str, *, autocommit: bool = True
) -> dict:
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
    ticker = str(data.get("ticker", "")).upper().strip()
    currency = str(data.get("currency", "USD")).upper().strip() or "USD"
    is_cash_ticker = ticker == currency
    thesis = data.pop("thesis", None)
    raw_category = data.pop("category", None)
    category: StockCategory | None = None
    if raw_category is not None:
        try:
            category = StockCategory(str(raw_category).strip())
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail={
                    "error_code": ERROR_INVALID_INPUT,
                    "detail": t("common.validation_error", lang=lang),
                },
            ) from None

    auto_radar = False
    try:
        if ticker and not is_cash_ticker:
            _, auto_radar = ensure_stock_on_radar(
                session, ticker, thesis=thesis, category=category
            )
        saved = settle_transaction(session, data, lang, autocommit=autocommit)
    except Exception:
        # import_transactions continues on per-item failures; clear pending state
        # so later successful items cannot accidentally flush previous changes.
        session.rollback()
        raise

    logger.info(
        "交易紀錄已建立：id=%s ticker=%s type=%s",
        saved.id,
        saved.ticker,
        saved.transaction_type,
    )
    return _to_dict(saved, session=session, auto_radar=auto_radar)


def remove_transaction(session: Session, txn_id: int, lang: str) -> None:
    txn = repo.find_transaction_by_id(session, txn_id)
    if txn is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": ERROR_TRANSACTION_NOT_FOUND,
                "detail": t("transaction.not_found", lang=lang),
            },
        )
    if txn.account_id is not None:
        reverse_settlement(session, txn, lang)
        session.delete(txn)
        session.commit()
    else:
        repo.delete_transaction(session, txn)
    logger.info("交易紀錄已刪除：id=%s", txn_id)


def get_transaction(session: Session, txn_id: int, lang: str) -> dict:
    txn = repo.find_transaction_by_id(session, txn_id)
    if txn is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": ERROR_TRANSACTION_NOT_FOUND,
                "detail": t("transaction.not_found", lang=lang),
            },
        )
    return _to_dict(txn, session=session)


def import_transactions(
    session: Session,
    data: list[dict],
    lang: str,
    *,
    account_id: int | None = None,
    mode: Literal["append", "replace_account"] = "append",
) -> dict:
    if len(data) > 1000:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": ERROR_INVALID_INPUT,
                "detail": t(GENERIC_VALIDATION_ERROR, lang=lang),
            },
        )

    if mode == "replace_account" and account_id is None:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": ERROR_INVALID_INPUT,
                "detail": t(GENERIC_VALIDATION_ERROR, lang=lang),
            },
        )

    if mode == "replace_account" and account_id is not None:
        return _replace_account_and_import(
            session=session,
            data=data,
            lang=lang,
            account_id=account_id,
        )

    deleted = 0
    imported = 0
    errors: list[str] = []
    for index, item in enumerate(data):
        try:
            payload = {**item}
            if account_id is not None:
                payload["account_id"] = account_id
            create_transaction(session, payload, lang)
            imported += 1
        except Exception as exc:
            logger.warning("交易匯入第 %d 筆失敗：%s", index + 1, exc)
            errors.append(t("api.import_item_failed", lang=lang, index=index + 1))

    return {
        "message": t("api.import_done", lang=lang, count=imported),
        "imported": imported,
        "deleted": deleted,
        "errors": errors,
    }


def export_transactions_csv_rows(
    session: Session,
    *,
    ticker: str | None = None,
    account_id: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int | None = None,
) -> list[dict[str, str | float | None]]:
    transactions = list_transactions(
        session,
        ticker=ticker,
        account_id=account_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    account_name_by_id: dict[int, str] = {}
    rows: list[dict[str, str | float | None]] = []
    for txn in transactions:
        txn_account_id = txn.get("account_id")
        account_name: str | None = None
        if isinstance(txn_account_id, int):
            account_name = account_name_by_id.get(txn_account_id)
            if account_name is None:
                account = repo.find_account_by_id(session, txn_account_id)
                account_name = account.name if account is not None else ""
                account_name_by_id[txn_account_id] = account_name
        rows.append(
            {
                "transaction_date": txn.get("transaction_date"),
                "ticker": txn.get("ticker"),
                "transaction_type": txn.get("transaction_type"),
                "quantity": txn.get("quantity"),
                "price": txn.get("price"),
                "total_amount": txn.get("total_amount"),
                "currency": txn.get("currency"),
                "fx_rate": txn.get("fx_rate"),
                "fee": txn.get("fee"),
                "note": txn.get("note"),
                "account_name": account_name or "",
            }
        )
    return rows


def _to_dict(
    txn: Transaction,
    *,
    session: Session,
    auto_radar: bool = False,
    holding_meta_cache: dict[int, tuple[str | None, bool | None]] | None = None,
) -> dict:
    category: str | None = None
    is_cash: bool | None = None
    if txn.holding_id is not None:
        cache_key = txn.holding_id
        if holding_meta_cache is not None and cache_key in holding_meta_cache:
            category, is_cash = holding_meta_cache[cache_key]
        else:
            holding = repo.find_holding_by_id(session, txn.holding_id)
            if holding is not None:
                category = (
                    holding.category.value
                    if hasattr(holding.category, "value")
                    else str(holding.category)
                )
                is_cash = bool(holding.is_cash)
            if holding_meta_cache is not None:
                holding_meta_cache[cache_key] = (category, is_cash)

    return {
        "id": txn.id,
        "user_id": txn.user_id,
        "account_id": txn.account_id,
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
        "auto_radar": auto_radar,
        "category": category,
        "is_cash": is_cash,
    }


def _replace_account_transactions(session: Session, account_id: int, lang: str) -> int:
    existing_transactions = repo.find_all_transactions(
        session,
        account_id=account_id,
        limit=None,
    )
    # Reverse in deterministic LIFO order to avoid non-deterministic same-date behavior.
    existing_transactions_sorted = sorted(
        existing_transactions,
        key=lambda txn: (txn.transaction_date, txn.created_at, txn.id or 0),
        reverse=True,
    )
    for txn in existing_transactions_sorted:
        reverse_settlement(session, txn, lang)
    return repo.delete_transactions_by_account(session, account_id)


def _replace_account_and_import(
    *,
    session: Session,
    data: list[dict],
    lang: str,
    account_id: int,
) -> dict:
    deleted = _replace_account_transactions(session, account_id, lang)

    imported = 0
    for item in data:
        payload = {**item, "account_id": account_id}
        create_transaction(session, payload, lang, autocommit=False)
        imported += 1

    # Commit replace + all imported rows atomically.
    session.commit()
    return {
        "message": t("api.import_done", lang=lang, count=imported),
        "imported": imported,
        "deleted": deleted,
        "errors": [],
    }
