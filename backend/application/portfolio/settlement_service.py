"""Transaction settlement helpers for cash and stock positions."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import HTTPException
from sqlalchemy import case
from sqlmodel import func, select

if TYPE_CHECKING:
    from datetime import date

    from sqlmodel import Session

    from domain.core.entities import Account

from application.portfolio.eligibility_service import check_asset_eligibility
from application.portfolio.wrapper_service import (
    get_ledger_entries,
    record_contribution,
    record_restoration,
)
from domain.constants import (
    DEFAULT_USER_ID,
    ERROR_ACCOUNT_NOT_FOUND,
    ERROR_INSUFFICIENT_BALANCE,
    ERROR_INVALID_INPUT,
    HOLDING_QUANTITY_EPSILON,
    POSITION_VERIFY_EPSILON,
)
from domain.core.entities import _normalize_stock_category
from domain.entities import Holding, Transaction
from domain.enums import StockCategory, TransactionType
from domain.portfolio.tax_wrapper import validate_nisa_purchase
from domain.portfolio.utils import is_cash_ticker
from i18n import t
from infrastructure import repositories as repo

AUTO_CREATE_CASH_TYPES = {
    TransactionType.SELL,
    TransactionType.DIVIDEND,
    TransactionType.DEPOSIT,
    TransactionType.OPENING_BALANCE,
    TransactionType.TRANSFER_IN,
    TransactionType.ADJUSTMENT,
}

AUTO_CREATE_STOCK_TYPES = {
    TransactionType.BUY,
    TransactionType.OPENING_BALANCE,
}

STOCK_MODIFY_TYPES = {
    TransactionType.BUY,
    TransactionType.SELL,
    TransactionType.OPENING_BALANCE,
    TransactionType.ADJUSTMENT,
    TransactionType.STOCK_SPLIT,
}

# Stock OPENING_BALANCE/ADJUSTMENT represent position snapshots or corrections,
# not real cash movements.
SKIP_CASH_FOR_STOCK_TYPES = {
    TransactionType.OPENING_BALANCE,
    TransactionType.ADJUSTMENT,
    TransactionType.STOCK_SPLIT,
}

ELIGIBILITY_CHECK_WRAPPERS = {"nisa_tsumitate", "nisa_growth", "ideco"}


def _validate_settlement_inputs(
    session: Session,
    txn_data: dict,
    txn_type: TransactionType,
    ticker: str,
    cash_position: bool,
    wrapper: str,
    txn_date: date,
    user_id: str,
    lang: str,
    account: Account,
) -> None:
    """Validate NISA quota and asset eligibility.

    Mutates *txn_data* to set the MUTUAL_FUND category when the NISA wrapper
    requires it. Raises HTTPException on any violation.
    """
    if wrapper in {"nisa_tsumitate", "nisa_growth"} and txn_type == TransactionType.BUY:
        amount = abs(float(txn_data.get("total_amount", 0) or 0))
        entries = get_ledger_entries(session, user_id)
        violations = validate_nisa_purchase(
            entries=entries,
            wrapper=wrapper,
            amount=amount,
            year=txn_date.year,
            as_of=txn_date,
        )
        if violations:
            raise HTTPException(
                status_code=422,
                detail={
                    "error_code": "QUOTA_EXCEEDED",
                    "detail": t("wrapper.quota_exceeded", lang=lang),
                    "violations": violations,
                },
            )

    eligibility = None
    if (
        wrapper in ELIGIBILITY_CHECK_WRAPPERS
        and txn_type == TransactionType.BUY
        and not cash_position
    ):
        eligibility = check_asset_eligibility(
            session=session,
            ticker=ticker,
            wrapper=wrapper,
            broker=account.broker,
        )
        if not eligibility.eligible:
            raise HTTPException(
                status_code=422,
                detail={
                    "error_code": "ASSET_NOT_ELIGIBLE",
                    "detail": t("eligibility.not_eligible", lang=lang),
                    "reasons": eligibility.reasons,
                    "suggested_wrapper": eligibility.suggested_wrapper,
                },
            )

    if (
        txn_type == TransactionType.BUY
        and wrapper == "nisa_tsumitate"
        and not cash_position
    ) or (
        txn_type == TransactionType.BUY
        and wrapper == "nisa_growth"
        and not cash_position
        and eligibility is not None
        and eligibility.asset_type == "mutual_fund"
    ):
        txn_data["category"] = StockCategory.MUTUAL_FUND.value


def _apply_cash_update(
    session: Session,
    account_id: int,
    account: Account,
    txn_type: TransactionType,
    txn_data: dict,
    currency: str,
    skip_cash: bool,
    lang: str,
) -> None:
    """Resolve (or auto-create) the cash holding and apply the cash delta."""
    if skip_cash:
        return

    cash_holding = repo.find_cash_holding_by_account_and_currency(
        session, account_id, currency
    )
    if cash_holding is None and txn_type in AUTO_CREATE_CASH_TYPES:
        cash_holding = Holding(
            user_id=DEFAULT_USER_ID,
            ticker=currency,
            category=StockCategory.CASH,
            quantity=0.0,
            cost_basis=1.0,
            broker=account.broker,
            account_id=account_id,
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
    if next_balance < -HOLDING_QUANTITY_EPSILON:
        _raise_insufficient_balance(
            lang=lang,
            available=cash_holding.quantity,
            required=abs(delta),
        )

    cash_holding.quantity = next_balance
    cash_holding.updated_at = datetime.now(UTC)
    session.add(cash_holding)


def _apply_stock_update(
    session: Session,
    account_id: int,
    account: Account,
    txn_type: TransactionType,
    txn_data: dict,
    ticker: str,
    currency: str,
    cash_position: bool,
    lang: str,
) -> float:
    """Resolve (or auto-create) the stock holding and apply quantity / cost updates.

    Returns the restoration amount (> 0 only for SELL transactions with cost basis).
    """
    if txn_type not in STOCK_MODIFY_TYPES or cash_position:
        return 0.0

    stock_holding = repo.find_stock_holding_by_account_and_ticker(
        session, account_id, ticker
    )
    if stock_holding is None and txn_type in AUTO_CREATE_STOCK_TYPES:
        stock_holding = Holding(
            user_id=DEFAULT_USER_ID,
            ticker=ticker,
            category=_infer_category(session, txn_data),
            quantity=0.0,
            cost_basis=txn_data.get("price"),
            broker=account.broker,
            account_id=account_id,
            currency=currency,
            account_type=account.account_type,
            is_cash=False,
        )
        session.add(stock_holding)

    if stock_holding is None:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": ERROR_INVALID_INPUT,
                "detail": t("transaction.stock_holding_not_found", lang=lang),
            },
        )

    # Keep holding category aligned with radar stock/category inference.
    stock_holding.category = _infer_category(session, txn_data)

    restoration_amount = 0.0
    quantity = float(txn_data.get("quantity", 0) or 0)
    if txn_type in (TransactionType.BUY, TransactionType.OPENING_BALANCE):
        _update_cost_basis(stock_holding, quantity, txn_data)
        stock_holding.quantity += quantity
    elif txn_type == TransactionType.SELL:
        restoration_amount = quantity * float(stock_holding.cost_basis or 0.0)
        _raise_if_insufficient_shares(
            lang=lang,
            available=stock_holding.quantity,
            required=quantity,
        )
        stock_holding.quantity -= quantity
    elif txn_type == TransactionType.ADJUSTMENT:
        total_amount = float(txn_data.get("total_amount", 0) or 0)
        if total_amount >= 0:
            stock_holding.quantity += quantity
        else:
            _raise_if_insufficient_shares(
                lang=lang,
                available=stock_holding.quantity,
                required=quantity,
            )
            stock_holding.quantity -= quantity
    elif txn_type == TransactionType.STOCK_SPLIT:
        ratio = float(txn_data.get("price", 0) or 0)
        stock_holding.quantity += quantity
        if ratio > 0 and stock_holding.cost_basis is not None:
            stock_holding.cost_basis = float(stock_holding.cost_basis) / ratio

    stock_holding.updated_at = datetime.now(UTC)
    session.add(stock_holding)
    return restoration_amount


def _record_contribution_if_nisa(
    session: Session,
    txn: Transaction,
    wrapper: str,
    txn_type: TransactionType,
    txn_date: date,
    user_id: str,
    restoration_amount: float,
) -> None:
    """Record a NISA contribution or restoration for the given transaction."""
    if wrapper not in {"nisa_tsumitate", "nisa_growth"}:
        return

    if txn_type == TransactionType.BUY:
        record_contribution(
            session=session,
            user_id=user_id,
            wrapper=wrapper,
            amount=abs(float(txn.total_amount)),
            fiscal_year=txn_date.year,
            transaction_id=txn.id,
            effective_date=txn_date,
            autocommit=False,
        )
    elif txn_type == TransactionType.SELL and restoration_amount > 0:
        record_restoration(
            session=session,
            user_id=user_id,
            wrapper=wrapper,
            amount=restoration_amount,
            fiscal_year=txn_date.year,
            transaction_id=txn.id,
            sell_date=txn_date,
            autocommit=False,
        )


def settle_transaction(
    session: Session,
    txn_data: dict,
    lang: str,
    *,
    autocommit: bool = True,
) -> Transaction:
    """Apply settlement and persist transaction atomically."""
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
    ticker = str(txn_data.get("ticker", "")).upper().strip()
    txn_data["ticker"] = ticker
    currency = str(txn_data.get("currency", "USD")).upper().strip() or "USD"
    txn_data["currency"] = currency
    txn_date: date = txn_data["transaction_date"]
    cash_position = is_cash_ticker(ticker, currency)
    skip_cash = txn_type in SKIP_CASH_FOR_STOCK_TYPES and not cash_position
    wrapper = (account.tax_wrapper or "").strip().lower()
    user_id = account.user_id or DEFAULT_USER_ID

    _validate_settlement_inputs(
        session=session,
        txn_data=txn_data,
        txn_type=txn_type,
        ticker=ticker,
        cash_position=cash_position,
        wrapper=wrapper,
        txn_date=txn_date,
        user_id=user_id,
        lang=lang,
        account=account,
    )

    _apply_cash_update(
        session=session,
        account_id=int(account_id),
        account=account,
        txn_type=txn_type,
        txn_data=txn_data,
        currency=currency,
        skip_cash=skip_cash,
        lang=lang,
    )

    restoration_amount = _apply_stock_update(
        session=session,
        account_id=int(account_id),
        account=account,
        txn_type=txn_type,
        txn_data=txn_data,
        ticker=ticker,
        currency=currency,
        cash_position=cash_position,
        lang=lang,
    )

    txn = Transaction(**txn_data)
    session.add(txn)
    session.flush()
    session.refresh(txn)

    _record_contribution_if_nisa(
        session=session,
        txn=txn,
        wrapper=wrapper,
        txn_type=txn_type,
        txn_date=txn_date,
        user_id=user_id,
        restoration_amount=restoration_amount,
    )

    if autocommit:
        session.commit()
        session.refresh(txn)
    return txn


def reverse_settlement(session: Session, txn: Transaction, lang: str) -> None:
    """Reverse previously-applied settlement for a transaction."""
    if txn.account_id is None:
        return

    txn_type = TransactionType(txn.transaction_type)
    cash_position = is_cash_ticker(txn.ticker, txn.currency)
    skip_cash = txn_type in SKIP_CASH_FOR_STOCK_TYPES and not cash_position

    if not skip_cash:
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

        delta = -_cash_delta(txn_type, txn.model_dump())
        next_balance = cash_holding.quantity + delta
        if next_balance < -HOLDING_QUANTITY_EPSILON:
            _raise_insufficient_balance(
                lang=lang,
                available=cash_holding.quantity,
                required=abs(delta),
            )

        cash_holding.quantity = next_balance
        cash_holding.updated_at = datetime.now(UTC)
        session.add(cash_holding)

    if txn_type in STOCK_MODIFY_TYPES and not cash_position:
        stock_holding = repo.find_stock_holding_by_account_and_ticker(
            session, int(txn.account_id), txn.ticker
        )
        if stock_holding is None:
            raise HTTPException(
                status_code=422,
                detail={
                    "error_code": ERROR_INVALID_INPUT,
                    "detail": t("transaction.stock_holding_not_found", lang=lang),
                },
            )

        quantity = float(txn.quantity)
        if txn_type in (TransactionType.BUY, TransactionType.OPENING_BALANCE):
            _raise_if_insufficient_shares(
                lang=lang,
                available=stock_holding.quantity,
                required=quantity,
            )
            _reverse_cost_basis(stock_holding, quantity, txn.price)
            stock_holding.quantity -= quantity
        elif txn_type == TransactionType.SELL:
            stock_holding.quantity += quantity
        elif txn_type == TransactionType.ADJUSTMENT:
            total_amount = float(txn.total_amount or 0)
            if total_amount >= 0:
                _raise_if_insufficient_shares(
                    lang=lang,
                    available=stock_holding.quantity,
                    required=quantity,
                )
                stock_holding.quantity -= quantity
            else:
                stock_holding.quantity += quantity
        elif txn_type == TransactionType.STOCK_SPLIT:
            # quantity is the additive delta (positive for forward splits, negative for
            # reverse splits). Reversing removes that delta — for a reverse split the
            # delta is negative, so we add abs(quantity) back.
            abs_quantity = abs(quantity)
            _raise_if_insufficient_shares(
                lang=lang,
                available=stock_holding.quantity,
                required=abs_quantity,
            )
            ratio = float(txn.price or 0)
            stock_holding.quantity -= quantity  # subtracts the signed delta
            if ratio > 0 and stock_holding.cost_basis is not None:
                stock_holding.cost_basis = float(stock_holding.cost_basis) * ratio

        stock_holding.updated_at = datetime.now(UTC)
        session.add(stock_holding)


def _cash_delta(txn_type: TransactionType, txn_data: dict) -> float:
    total_amount = float(txn_data.get("total_amount", 0) or 0)
    fee = float(txn_data.get("fee", 0) or 0)
    net_credit = total_amount - fee
    net_debit = total_amount + fee

    if txn_type == TransactionType.BUY:
        return -net_debit
    if txn_type == TransactionType.SELL:
        return net_credit
    if txn_type in (
        TransactionType.DIVIDEND,
        TransactionType.DEPOSIT,
        TransactionType.OPENING_BALANCE,
        TransactionType.TRANSFER_IN,
    ):
        return net_credit
    if txn_type in (TransactionType.WITHDRAWAL, TransactionType.TRANSFER_OUT):
        return -net_debit
    if txn_type == TransactionType.ADJUSTMENT:
        # Signed amount: positive total_amount credits, negative debits.
        return net_credit
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


def _raise_if_insufficient_shares(
    *, lang: str, available: float, required: float
) -> None:
    if available >= required - HOLDING_QUANTITY_EPSILON:
        return
    raise HTTPException(
        status_code=422,
        detail={
            "error_code": ERROR_INSUFFICIENT_BALANCE,
            "detail": t("transaction.insufficient_shares", lang=lang),
            "available": max(0.0, round(available, 8)),
            "required": max(0.0, round(required, 8)),
        },
    )


def _infer_category(session: Session, txn_data: dict) -> StockCategory:
    """Infer category by radar stock first, eligible fund master, then payload fallback."""
    ticker = str(txn_data.get("ticker", "")).upper().strip()
    requested = str(txn_data.get("category", "")).strip()
    if (
        ticker
        and requested == StockCategory.MUTUAL_FUND.value
        and repo.is_active_eligible_mutual_fund(session, ticker)
    ):
        return StockCategory.MUTUAL_FUND
    if ticker:
        stock = repo.find_stock_by_ticker(session, ticker)
        if stock:
            return stock.category
        if repo.is_active_eligible_mutual_fund(session, ticker):
            return StockCategory.MUTUAL_FUND

    raw = str(txn_data.get("category", StockCategory.GROWTH.value))
    return _normalize_stock_category(raw)


def _update_cost_basis(holding: Holding, buy_qty: float, txn_data: dict) -> None:
    """Update holding cost basis with weighted-average method."""
    if buy_qty <= 0:
        return
    price = float(txn_data.get("price", 0) or 0)
    if price <= 0:
        return
    old_qty = float(holding.quantity)
    old_basis = float(holding.cost_basis or 0)
    total_qty = old_qty + buy_qty
    if total_qty <= 0:
        return
    holding.cost_basis = ((old_basis * old_qty) + (price * buy_qty)) / total_qty


def _reverse_cost_basis(
    holding: Holding, removed_qty: float, removed_price: float | None
) -> None:
    """Reverse weighted-average basis after removing a buy-like lot."""
    if removed_qty <= 0:
        return
    price = float(removed_price or 0)
    if price <= 0:
        return

    current_qty = float(holding.quantity or 0)
    current_basis = float(holding.cost_basis or 0)
    remaining_qty = current_qty - removed_qty
    if remaining_qty <= HOLDING_QUANTITY_EPSILON:
        holding.cost_basis = 0.0
        return

    numerator = (current_basis * current_qty) - (price * removed_qty)
    if numerator <= 0:
        holding.cost_basis = 0.0
        return

    holding.cost_basis = numerator / remaining_qty


def verify_positions(session: Session) -> list[dict]:
    """Compare materialized holdings with transaction-derived positions."""
    computed: dict[tuple[int, str, bool], float] = {}

    txn_type_col = func.upper(Transaction.transaction_type)
    ticker_col = func.upper(Transaction.ticker)
    currency_col = func.upper(Transaction.currency)
    is_cash_ticker_expr = ticker_col == currency_col
    is_stock_snapshot_expr = txn_type_col.in_(
        [
            TransactionType.OPENING_BALANCE.value,
            TransactionType.ADJUSTMENT.value,
        ]
    )
    include_cash_expr = (~is_stock_snapshot_expr) | is_cash_ticker_expr
    net_credit_expr = Transaction.total_amount - Transaction.fee
    net_debit_expr = Transaction.total_amount + Transaction.fee

    cash_delta_expr = case(
        (
            include_cash_expr & (txn_type_col == TransactionType.BUY.value),
            -net_debit_expr,
        ),
        (
            include_cash_expr
            & txn_type_col.in_(
                [
                    TransactionType.SELL.value,
                    TransactionType.DIVIDEND.value,
                    TransactionType.DEPOSIT.value,
                    TransactionType.OPENING_BALANCE.value,
                    TransactionType.TRANSFER_IN.value,
                    TransactionType.ADJUSTMENT.value,
                ]
            ),
            net_credit_expr,
        ),
        (
            include_cash_expr
            & txn_type_col.in_(
                [TransactionType.WITHDRAWAL.value, TransactionType.TRANSFER_OUT.value]
            ),
            -net_debit_expr,
        ),
        else_=0.0,
    )

    cash_rows = session.exec(
        select(
            Transaction.account_id,
            currency_col.label("currency"),
            func.sum(cash_delta_expr).label("expected"),
        ).group_by(Transaction.account_id, currency_col)
    ).all()
    for account_id, currency, expected in cash_rows:
        if account_id is None:
            continue
        expected_val = float(expected or 0.0)
        if abs(expected_val) <= POSITION_VERIFY_EPSILON:
            continue
        computed[(int(account_id), str(currency), True)] = expected_val

    stock_delta_expr = case(
        (
            (~is_cash_ticker_expr)
            & txn_type_col.in_(
                [TransactionType.BUY.value, TransactionType.OPENING_BALANCE.value]
            ),
            Transaction.quantity,
        ),
        (
            (~is_cash_ticker_expr) & (txn_type_col == TransactionType.SELL.value),
            -Transaction.quantity,
        ),
        (
            (~is_cash_ticker_expr)
            & (txn_type_col == TransactionType.ADJUSTMENT.value)
            & (Transaction.total_amount >= 0),
            Transaction.quantity,
        ),
        (
            (~is_cash_ticker_expr)
            & (txn_type_col == TransactionType.ADJUSTMENT.value)
            & (Transaction.total_amount < 0),
            -Transaction.quantity,
        ),
        (
            (~is_cash_ticker_expr)
            & (txn_type_col == TransactionType.STOCK_SPLIT.value),
            Transaction.quantity,
        ),
        else_=0.0,
    )

    stock_rows = session.exec(
        select(
            Transaction.account_id,
            ticker_col.label("ticker"),
            func.sum(stock_delta_expr).label("expected"),
        ).group_by(Transaction.account_id, ticker_col)
    ).all()
    for account_id, ticker, expected in stock_rows:
        if account_id is None:
            continue
        expected_val = float(expected or 0.0)
        if abs(expected_val) <= POSITION_VERIFY_EPSILON:
            continue
        key = (int(account_id), str(ticker), False)
        computed[key] = computed.get(key, 0.0) + expected_val

    discrepancies: list[dict] = []
    holding_key_expr = case(
        (Holding.is_cash == True, func.upper(Holding.currency)),  # noqa: E712
        else_=func.upper(Holding.ticker),
    )
    holding_rows = session.exec(
        select(
            Holding.account_id,
            holding_key_expr.label("key_ticker"),
            Holding.is_cash,
            func.sum(Holding.quantity).label("actual"),
        ).group_by(Holding.account_id, holding_key_expr, Holding.is_cash)
    ).all()

    for account_id, key_ticker, is_cash, actual in holding_rows:
        if account_id is None:
            continue
        key = (int(account_id), str(key_ticker), bool(is_cash))
        expected = computed.pop(key, 0.0)
        actual_val = float(actual or 0.0)
        if abs(actual_val - expected) > POSITION_VERIFY_EPSILON:
            discrepancies.append(
                {
                    "account_id": int(account_id),
                    "ticker": str(key_ticker),
                    "is_cash": bool(is_cash),
                    "materialized": actual_val,
                    "computed": expected,
                    "diff": round(actual_val - expected, 8),
                }
            )

    for (account_id, ticker, is_cash), expected in computed.items():
        if abs(expected) > POSITION_VERIFY_EPSILON:
            discrepancies.append(
                {
                    "account_id": account_id,
                    "ticker": ticker,
                    "is_cash": is_cash,
                    "materialized": 0.0,
                    "computed": expected,
                    "diff": round(-expected, 8),
                }
            )

    return discrepancies


# ---------------------------------------------------------------------------
# Mutual-Fund Holding reclassification (data healing)
# ---------------------------------------------------------------------------


def reclassify_mutual_fund_holdings(
    session: Session, *, autocommit: bool = True
) -> int:
    """Fix Holdings whose ticker is an eligible mutual fund but category is wrong.

    Mirrors ``stock_service.reclassify_mutual_fund_stocks`` for the Holding table.
    Should be called at startup and after each NISA eligible-list sync.
    """
    from logging_config import get_logger

    _logger = get_logger(__name__)

    holdings = list(
        session.exec(
            select(Holding).where(
                Holding.is_cash == False,  # noqa: E712
                Holding.category != StockCategory.MUTUAL_FUND,
            )
        ).all()
    )
    updated = 0
    for h in holdings:
        if repo.is_active_eligible_mutual_fund(session, h.ticker):
            h.category = StockCategory.MUTUAL_FUND
            session.add(h)
            updated += 1
    if updated:
        if autocommit:
            session.commit()
        _logger.info("Reclassified %d holdings to Mutual_Fund.", updated)
    return updated
