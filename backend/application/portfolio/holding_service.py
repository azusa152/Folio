"""
Application — Holding Service。
封裝持倉的 CRUD 與匯入/匯出邏輯，路由層不直接存取 ORM。
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from fastapi import HTTPException

if TYPE_CHECKING:
    from sqlmodel import Session

    from domain.entities import Holding

from application.portfolio.settlement_service import settle_transaction
from domain.constants import (
    ERROR_ACCOUNT_NOT_FOUND,
    ERROR_HOLDING_NOT_FOUND,
    ERROR_INVALID_INPUT,
    GENERIC_VALIDATION_ERROR,
)
from domain.enums import StockCategory, TransactionType
from i18n import t
from infrastructure import repositories as repo
from infrastructure.market_data import get_exchange_rate
from logging_config import get_logger

logger = get_logger(__name__)


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


def _normalize_coingecko_id(raw_value: str | None) -> str | None:
    if raw_value is None:
        return None
    value = raw_value.strip().lower()
    return value or None


def _validate_crypto_payload(
    *,
    category: StockCategory,
    currency: str,
    coingecko_id: str | None,
    lang: str,
) -> tuple[str, float, str | None]:
    if category != StockCategory.CRYPTO:
        purchase_fx_rate = (
            get_exchange_rate("USD", currency) if currency != "USD" else 1.0
        )
        return currency, purchase_fx_rate, None

    if currency != "USD":
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": ERROR_INVALID_INPUT,
                "detail": t(GENERIC_VALIDATION_ERROR, lang=lang),
            },
        )
    return "USD", 1.0, _normalize_coingecko_id(coingecko_id)


def _get_holding_or_raise(session: Session, holding_id: int, lang: str) -> Holding:
    holding = repo.find_holding_by_id(session, holding_id)
    if not holding:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": ERROR_HOLDING_NOT_FOUND,
                "detail": t("api.holding_not_found", lang=lang),
            },
        )
    return holding


def _ensure_account_exists(session: Session, account_id: int, lang: str) -> None:
    if repo.find_account_by_id(session, account_id) is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": ERROR_ACCOUNT_NOT_FOUND,
                "detail": t("account.not_found", lang=lang),
            },
        )


def _signed_adjustment_amount(
    *, quantity: float, cost_basis: float | None, is_decrease: bool
) -> float:
    """Build a non-zero signed marker amount for stock ADJUSTMENT direction."""
    unit_price = float(cost_basis or 0)
    magnitude = quantity * unit_price
    if magnitude <= 0:
        magnitude = quantity
    return -magnitude if is_decrease else magnitude


def _close_and_delete_holding_for_replace(
    session: Session, *, holding: Holding, lang: str, note: str
) -> None:
    if holding.account_id is None:
        repo.delete_holding(session, holding)
        return
    if float(holding.quantity) > 1e-9:
        txn_data = {
            "account_id": int(holding.account_id),
            "ticker": holding.ticker,
            "transaction_type": TransactionType.ADJUSTMENT.value,
            "quantity": float(holding.quantity),
            "price": holding.cost_basis,
            "total_amount": _signed_adjustment_amount(
                quantity=float(holding.quantity),
                cost_basis=holding.cost_basis,
                is_decrease=True,
            ),
            "currency": holding.currency,
            "fee": 0.0,
            "note": note,
            "transaction_date": date.today(),
        }
        settle_transaction(session, txn_data, lang)
        session.refresh(holding)
    repo.delete_holding(session, holding)


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------


def list_holdings(session: Session) -> list[dict]:
    """Return all holdings as dicts, ordered by id."""
    holdings = repo.find_all_holdings(session)
    return [_holding_to_dict(h) for h in holdings]


def get_holdings_by_account(session: Session, account_id: int, lang: str) -> list[dict]:
    """Return enriched holdings for a specific account."""
    _ensure_account_exists(session, account_id, lang)
    holdings = repo.find_holdings_by_account(session, account_id)
    return [_holding_to_dict(h) for h in holdings]


def create_holding(session: Session, payload: dict, lang: str) -> dict:
    """Create a holding by recording an OPENING_BALANCE transaction."""
    account_id = payload.get("account_id")
    if account_id is None:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": ERROR_INVALID_INPUT,
                "detail": t(GENERIC_VALIDATION_ERROR, lang=lang),
            },
        )
    _ensure_account_exists(session, int(account_id), lang)

    input_category = payload["category"]
    category = (
        input_category
        if isinstance(input_category, StockCategory)
        else StockCategory(str(input_category))
    )
    input_currency = payload["currency"].strip().upper()
    currency, purchase_fx_rate, coingecko_id = _validate_crypto_payload(
        category=category,
        currency=input_currency,
        coingecko_id=payload.get("coingecko_id"),
        lang=lang,
    )
    ticker = payload["ticker"].strip().upper()
    is_cash = bool(payload.get("is_cash", False))
    quantity = float(payload["quantity"])
    cost_basis = payload.get("cost_basis")
    if is_cash:
        ticker = currency
        cost_basis = 1.0

    txn_data = {
        "account_id": int(account_id),
        "ticker": ticker,
        "transaction_type": TransactionType.OPENING_BALANCE.value,
        "quantity": quantity,
        "price": cost_basis,
        "total_amount": quantity * (cost_basis or 0) if not is_cash else quantity,
        "currency": currency,
        "fee": 0.0,
        "note": "Created via holding form",
        "transaction_date": date.today(),
        "category": category.value,
    }
    settle_transaction(session, txn_data, lang)

    holding = (
        repo.find_cash_holding_by_account_and_currency(
            session, int(account_id), currency
        )
        if is_cash
        else repo.find_stock_holding_by_account_and_ticker(
            session, int(account_id), ticker
        )
    )
    if holding is None:
        return {}

    # Keep the same metadata behavior as legacy direct holding creation.
    holding.coingecko_id = coingecko_id
    holding.broker = payload.get("broker")
    holding.account_type = payload.get("account_type")
    holding.purchase_fx_rate = purchase_fx_rate
    saved = repo.save_holding(session, holding)
    logger.info("新增持倉（交易入帳）：%s（%s）", saved.ticker, saved.category)
    return _holding_to_dict(saved)


def create_cash_holding(session: Session, payload: dict, lang: str) -> dict:
    """Create a cash holding by recording an OPENING_BALANCE transaction."""
    account_id = payload.get("account_id")
    if account_id is None:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": ERROR_INVALID_INPUT,
                "detail": t(GENERIC_VALIDATION_ERROR, lang=lang),
            },
        )
    _ensure_account_exists(session, int(account_id), lang)

    currency_upper = payload["currency"].strip().upper()
    purchase_fx_rate = (
        get_exchange_rate("USD", currency_upper) if currency_upper != "USD" else 1.0
    )
    amount = float(payload["amount"])
    txn_data = {
        "account_id": int(account_id),
        "ticker": currency_upper,
        "transaction_type": TransactionType.OPENING_BALANCE.value,
        "quantity": amount,
        "price": 1.0,
        "total_amount": amount,
        "currency": currency_upper,
        "fee": 0.0,
        "note": "Created via cash holding form",
        "transaction_date": date.today(),
    }
    settle_transaction(session, txn_data, lang)

    holding = repo.find_cash_holding_by_account_and_currency(
        session, int(account_id), currency_upper
    )
    if holding is None:
        return {}
    holding.broker = payload.get("broker")
    holding.account_type = payload.get("account_type")
    holding.purchase_fx_rate = purchase_fx_rate
    saved = repo.save_holding(session, holding)
    logger.info("新增現金持倉（交易入帳）：%s %.2f", saved.ticker, saved.quantity)
    return _holding_to_dict(saved)


def update_holding(session: Session, holding_id: int, payload: dict, lang: str) -> dict:
    """Partially update an existing holding. Only provided fields are overwritten.

    Raises HTTPException 404 if not found.
    """
    holding = _get_holding_or_raise(session, holding_id, lang)
    if "ticker" in payload:
        holding.ticker = payload["ticker"].strip().upper()
    if "category" in payload:
        input_category = payload["category"]
        holding.category = (
            input_category
            if isinstance(input_category, StockCategory)
            else StockCategory(str(input_category))
        )
    original_quantity = float(holding.quantity)
    if "cost_basis" in payload:
        holding.cost_basis = payload["cost_basis"]
    if "broker" in payload:
        holding.broker = payload["broker"]
    if "account_id" in payload:
        next_account_id = payload["account_id"]
        if next_account_id is None:
            raise HTTPException(
                status_code=422,
                detail={
                    "error_code": ERROR_INVALID_INPUT,
                    "detail": t(GENERIC_VALIDATION_ERROR, lang=lang),
                },
            )
        _ensure_account_exists(session, int(next_account_id), lang)
        holding.account_id = int(next_account_id)
    if "currency" in payload:
        holding.currency = payload["currency"].strip().upper()
    if "account_type" in payload:
        holding.account_type = payload["account_type"]
    if "is_cash" in payload:
        holding.is_cash = payload["is_cash"]

    if "coingecko_id" in payload:
        holding.coingecko_id = _normalize_coingecko_id(payload["coingecko_id"])

    currency, purchase_fx_rate, normalized_coingecko_id = _validate_crypto_payload(
        category=holding.category,
        currency=holding.currency,
        coingecko_id=holding.coingecko_id,
        lang=lang,
    )
    holding.currency = currency
    holding.purchase_fx_rate = purchase_fx_rate
    holding.coingecko_id = normalized_coingecko_id

    if "quantity" in payload:
        new_quantity = float(payload["quantity"])
        qty_delta = new_quantity - original_quantity
        if abs(qty_delta) > 1e-9:
            if holding.account_id is None:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error_code": ERROR_INVALID_INPUT,
                        "detail": t(GENERIC_VALIDATION_ERROR, lang=lang),
                    },
                )
            abs_delta = abs(qty_delta)
            txn_data = {
                "account_id": int(holding.account_id),
                "ticker": holding.ticker,
                "transaction_type": TransactionType.ADJUSTMENT.value,
                "quantity": abs_delta,
                "price": holding.cost_basis,
                "total_amount": _signed_adjustment_amount(
                    quantity=abs_delta,
                    cost_basis=holding.cost_basis,
                    is_decrease=qty_delta < 0,
                ),
                "currency": holding.currency,
                "fee": 0.0,
                "note": f"Adjusted from {original_quantity} to {new_quantity}",
                "transaction_date": date.today(),
            }
            settle_transaction(session, txn_data, lang)
            session.refresh(holding)
    holding.updated_at = datetime.now(UTC)
    saved = repo.save_holding(session, holding)
    return _holding_to_dict(saved)


def delete_holding(session: Session, holding_id: int, lang: str) -> dict:
    """Delete a holding. Raises HTTPException 404 if not found."""
    holding = _get_holding_or_raise(session, holding_id, lang)
    ticker = holding.ticker
    if float(holding.quantity) > 1e-9:
        if holding.account_id is None:
            raise HTTPException(
                status_code=422,
                detail={
                    "error_code": ERROR_INVALID_INPUT,
                    "detail": t(GENERIC_VALIDATION_ERROR, lang=lang),
                },
            )
        qty = float(holding.quantity)
        txn_data = {
            "account_id": int(holding.account_id),
            "ticker": holding.ticker,
            "transaction_type": TransactionType.ADJUSTMENT.value,
            "quantity": qty,
            "price": holding.cost_basis,
            "total_amount": _signed_adjustment_amount(
                quantity=qty,
                cost_basis=holding.cost_basis,
                is_decrease=True,
            ),
            "currency": holding.currency,
            "fee": 0.0,
            "note": "Position closed via holding deletion",
            "transaction_date": date.today(),
        }
        settle_transaction(session, txn_data, lang)
        session.refresh(holding)
    repo.delete_holding(session, holding)
    logger.info("刪除持倉：%s", ticker)
    return {"message": t("api.holding_deleted", lang=lang, ticker=ticker)}


def export_holdings(session: Session) -> list[dict]:
    """Export all holdings as import-compatible dicts."""
    holdings = repo.find_all_holdings(session)
    return [
        {
            "ticker": h.ticker,
            "coingecko_id": h.coingecko_id,
            "category": h.category.value
            if hasattr(h.category, "value")
            else h.category,
            "quantity": h.quantity,
            "cost_basis": h.cost_basis,
            "broker": h.broker,
            "account_id": h.account_id,
            "currency": h.currency,
            "account_type": h.account_type,
            "is_cash": h.is_cash,
        }
        for h in holdings
    ]


def import_holdings(
    session: Session,
    data: list[dict],
    lang: str,
    *,
    mode: str = "replace_all",
    account_id: int | None = None,
) -> dict:
    """Bulk import holdings with replace/append modes. Returns {imported, errors}."""
    if len(data) > 1000:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": ERROR_INVALID_INPUT,
                "detail": t(GENERIC_VALIDATION_ERROR, lang=lang),
            },
        )

    if mode == "replace_account":
        if account_id is None:
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": ERROR_INVALID_INPUT,
                    "detail": t(GENERIC_VALIDATION_ERROR, lang=lang),
                },
            )
    elif mode not in {"replace_all", "append"}:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": ERROR_INVALID_INPUT,
                "detail": t(GENERIC_VALIDATION_ERROR, lang=lang),
            },
        )

    resolved_account_ids: list[int] = []
    for item in data:
        target_account_id = (
            account_id if account_id is not None else item.get("account_id")
        )
        if target_account_id is None:
            raise HTTPException(
                status_code=422,
                detail={
                    "error_code": ERROR_INVALID_INPUT,
                    "detail": t(GENERIC_VALIDATION_ERROR, lang=lang),
                },
            )
        resolved_account_ids.append(int(target_account_id))

    for candidate_account_id in set(resolved_account_ids):
        _ensure_account_exists(session, candidate_account_id, lang)

    if mode in {"replace_all", "replace_account"}:
        existing_holdings = repo.find_all_holdings(session)
        if mode == "replace_account":
            existing_holdings = [
                h for h in existing_holdings if h.account_id == int(account_id)
            ]
        for existing in existing_holdings:
            _close_and_delete_holding_for_replace(
                session,
                holding=existing,
                lang=lang,
                note=(
                    "Closed via holdings import replace_all"
                    if mode == "replace_all"
                    else "Closed via holdings import replace_account"
                ),
            )

    count = 0
    errors: list[str] = []
    for i, item in enumerate(data):
        try:
            target_account_id = resolved_account_ids[i]
            category = (
                item["category"]
                if isinstance(item["category"], StockCategory)
                else StockCategory(str(item["category"]))
            )
            is_cash = bool(item.get("is_cash", False))
            raw_currency = str(item.get("currency", "USD"))
            raw_ticker = str(item["ticker"])
            quantity = float(item["quantity"])
            cost_basis = item.get("cost_basis")
            if is_cash:
                category = StockCategory.CASH
            currency, purchase_fx_rate, coingecko_id = _validate_crypto_payload(
                category=category,
                currency=raw_currency.strip().upper(),
                coingecko_id=item.get("coingecko_id"),
                lang=lang,
            )
            ticker = currency if is_cash else raw_ticker.strip().upper()
            price = 1.0 if is_cash else cost_basis

            txn_data = {
                "account_id": target_account_id,
                "ticker": ticker,
                "transaction_type": TransactionType.OPENING_BALANCE.value,
                "quantity": quantity,
                "price": price,
                "total_amount": quantity * (cost_basis or 0)
                if not is_cash
                else quantity,
                "currency": currency,
                "fee": 0.0,
                "note": f"Imported row {i + 1}",
                "transaction_date": date.today(),
                "category": category.value,
            }
            settle_transaction(session, txn_data, lang)

            created = (
                repo.find_cash_holding_by_account_and_currency(
                    session, target_account_id, currency
                )
                if is_cash
                else repo.find_stock_holding_by_account_and_ticker(
                    session, target_account_id, ticker
                )
            )
            if created is not None:
                created.broker = item.get("broker")
                created.account_type = item.get("account_type")
                created.coingecko_id = coingecko_id
                created.purchase_fx_rate = purchase_fx_rate
                repo.save_holding(session, created)
            count += 1
        except Exception as e:
            logger.warning("持倉匯入第 %d 筆失敗：%s", i + 1, e)
            errors.append(t("api.import_item_failed", lang=lang, index=i + 1))
    logger.info("匯入持倉完成：%d 筆成功，%d 筆失敗。", count, len(errors))
    return {
        "message": t("api.import_done", lang=lang, count=count),
        "imported": count,
        "errors": errors,
    }
