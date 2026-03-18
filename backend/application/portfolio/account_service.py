"""帳戶管理與持倉分組服務。"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import HTTPException

if TYPE_CHECKING:
    from sqlmodel import Session

from application.portfolio.insight_service import invalidate_insight_cache
from application.portfolio.rebalance_service import invalidate_rebalance_cache
from application.portfolio.transaction_service import cleanup_account_transactions
from domain.constants import (
    DEFAULT_ACCOUNT_NAME,
    DEFAULT_USER_ID,
    ERROR_ACCOUNT_NOT_FOUND,
    ERROR_INVALID_INPUT,
    TAX_WRAPPER_OPTIONS,
)
from domain.entities import Account, Holding
from domain.enums import StockCategory
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
        "tax_wrapper": acct.tax_wrapper,
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


def _normalize_tax_wrapper(value: str | None, lang: str) -> str | None:
    """Normalize and validate tax wrapper values for internal callers."""
    if value is None:
        return None
    normalized = value.strip().lower()
    if not normalized:
        return None
    if normalized not in TAX_WRAPPER_OPTIONS:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": ERROR_INVALID_INPUT,
                "detail": t("common.validation_error", lang=lang),
            },
        )
    return normalized


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------


def list_accounts(session: Session, include_inactive: bool = False) -> list[dict]:
    """Return all active accounts as dicts."""
    return [
        _acct_to_dict(a)
        for a in repo.find_all_accounts(session, active_only=not include_inactive)
    ]


def create_account(session: Session, data: dict, lang: str) -> dict:
    """Create a new account. Returns the created account dict."""
    payload = dict(data)
    payload["tax_wrapper"] = _normalize_tax_wrapper(payload.get("tax_wrapper"), lang)
    account = Account(**payload)
    session.add(account)
    session.flush()

    normalized_currency = (account.currency or "USD").upper().strip() or "USD"
    account.currency = normalized_currency
    cash_holding = Holding(
        user_id=account.user_id or DEFAULT_USER_ID,
        ticker=normalized_currency,
        category=StockCategory.CASH,
        quantity=0.0,
        cost_basis=1.0,
        broker=account.broker,
        account_id=account.id,
        currency=normalized_currency,
        account_type=account.account_type,
        is_cash=True,
        purchase_fx_rate=1.0,
    )
    session.add(cash_holding)
    session.commit()
    session.refresh(account)
    logger.info("新增帳戶：%s（%s）", account.name, account.broker)
    return _acct_to_dict(account)


def ensure_default_account(session: Session) -> Account:
    """Return the default account, creating it if it doesn't exist."""
    existing = repo.find_all_accounts(session, active_only=False)
    for account in existing:
        if (
            account.name == DEFAULT_ACCOUNT_NAME
            and account.broker == DEFAULT_ACCOUNT_NAME
        ):
            return account

    account_dict = create_account(
        session,
        {
            "name": DEFAULT_ACCOUNT_NAME,
            "broker": DEFAULT_ACCOUNT_NAME,
            "account_type": "brokerage",
            "currency": "USD",
        },
        lang="en",
    )
    created = repo.find_account_by_id(session, account_dict["id"])
    if created is None:
        raise RuntimeError("default account creation failed")
    return created


def update_account(session: Session, account_id: int, data: dict, lang: str) -> dict:
    """Partially update an existing account. Only provided fields are overwritten."""
    account = _get_account_or_raise(session, account_id, lang)
    normalized_data = dict(data)
    if "tax_wrapper" in normalized_data:
        normalized_data["tax_wrapper"] = _normalize_tax_wrapper(
            normalized_data.get("tax_wrapper"), lang
        )
    for key, value in normalized_data.items():
        if hasattr(account, key) and key not in ("id", "user_id", "created_at"):
            setattr(account, key, value)
    account.updated_at = datetime.now(UTC)
    saved = repo.save_account(session, account)
    return _acct_to_dict(saved)


def remove_account(session: Session, account_id: int, lang: str) -> None:
    """Cascade-clean account transactions/holdings, then soft-delete the account."""
    account = _get_account_or_raise(session, account_id, lang)
    cleanup_account_transactions(session, account_id, lang)
    repo.delete_holdings_by_account(session, account_id)
    repo.deactivate_account(session, account)
    invalidate_rebalance_cache()
    invalidate_insight_cache()
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
        non_cash_holdings = [
            holding for holding in acct_holdings if not holding.is_cash
        ]
        cash_balances: dict[str, float] = {}
        for holding in acct_holdings:
            if not holding.is_cash:
                continue
            currency = (holding.currency or "USD").upper()
            cash_balances[currency] = cash_balances.get(currency, 0.0) + float(
                holding.quantity
            )
        result.append(
            {
                "account": _acct_to_dict(acct),
                "holdings_count": len(non_cash_holdings),
                "tickers": [h.ticker for h in non_cash_holdings],
                "cash_balances": [
                    {"currency": currency, "balance": round(balance, 8)}
                    for currency, balance in sorted(cash_balances.items())
                ],
            }
        )

    unlinked = account_map.get(None, [])
    if unlinked:
        result.append(
            {
                "account": None,
                "holdings_count": len(unlinked),
                "tickers": [h.ticker for h in unlinked],
                "cash_balances": [],
            }
        )

    return result


def get_account_cash_balances(
    session: Session, account_id: int, lang: str
) -> list[dict]:
    """Return account cash balances grouped by currency."""
    _get_account_or_raise(session, account_id, lang)
    holdings = repo.find_all_holdings(session)

    balances: dict[str, float] = {}
    for h in holdings:
        if h.account_id != account_id or not h.is_cash:
            continue
        currency = (h.currency or "USD").upper()
        balances[currency] = balances.get(currency, 0.0) + float(h.quantity)

    return [
        {"currency": currency, "balance": round(balance, 8)}
        for currency, balance in sorted(balances.items())
    ]
