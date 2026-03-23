"""Account CRUD and aggregation routes."""

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from api.error_mapping import to_http_exception
from api.schemas import MessageResponse
from api.schemas.account import (
    AccountCashBalanceItem,
    AccountRequest,
    AccountResponse,
    AccountSummaryItem,
    AccountUpdateRequest,
)
from api.schemas.portfolio import HoldingResponse, SellablePositionsResponse
from api.schemas.transaction import TransactionResponse
from application.errors import ApplicationError
from application.portfolio.account_service import (
    create_account,
    get_account_cash_balances,
    get_account_summary,
    list_accounts,
    remove_account,
    update_account,
)
from application.portfolio.holding_service import (
    get_holdings_by_account,
    get_sellable_positions,
)
from application.portfolio.transaction_service import list_transactions_by_account
from i18n import get_user_language, t
from infrastructure.database import get_session

router = APIRouter(tags=["accounts"])


@router.get("/accounts", response_model=list[AccountResponse])
def get_accounts(
    include_inactive: bool = False,
    session: Session = Depends(get_session),
):
    return list_accounts(session, include_inactive=include_inactive)


@router.post("/accounts", response_model=AccountResponse, status_code=201)
def add_account(body: AccountRequest, session: Session = Depends(get_session)):
    lang = get_user_language(session)
    try:
        return create_account(session, body.model_dump(), lang)
    except ApplicationError as exc:
        raise to_http_exception(exc, lang=lang) from exc


@router.get("/accounts/summary", response_model=list[AccountSummaryItem])
def get_accounts_summary(session: Session = Depends(get_session)):
    return get_account_summary(session)


@router.get(
    "/accounts/{account_id}/cash-balances",
    response_model=list[AccountCashBalanceItem],
)
def get_account_cash_balance_list(
    account_id: int,
    session: Session = Depends(get_session),
):
    lang = get_user_language(session)
    try:
        return get_account_cash_balances(session, account_id, lang)
    except ApplicationError as exc:
        raise to_http_exception(exc, lang=lang) from exc


@router.get(
    "/accounts/{account_id}/positions",
    response_model=list[HoldingResponse],
)
def get_account_positions(
    account_id: int,
    session: Session = Depends(get_session),
):
    """Return all holdings (positions) for a given account."""
    lang = get_user_language(session)
    return get_holdings_by_account(session, account_id, lang)


@router.get(
    "/accounts/{account_id}/sellable-positions",
    response_model=SellablePositionsResponse,
)
def get_account_sellable_positions(
    account_id: int,
    session: Session = Depends(get_session),
):
    """Return sellable non-cash positions for a given account."""
    lang = get_user_language(session)
    return get_sellable_positions(session, account_id, lang)


@router.get(
    "/accounts/{account_id}/transactions",
    response_model=list[TransactionResponse],
)
def get_account_transactions(
    account_id: int,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
):
    """Return paginated transactions for a given account."""
    lang = get_user_language(session)
    return list_transactions_by_account(
        session,
        account_id,
        lang=lang,
        limit=limit,
        offset=offset,
    )


@router.put("/accounts/{account_id}", response_model=AccountResponse)
def edit_account(
    account_id: int,
    body: AccountUpdateRequest,
    session: Session = Depends(get_session),
):
    lang = get_user_language(session)
    try:
        return update_account(
            session, account_id, body.model_dump(exclude_unset=True), lang
        )
    except ApplicationError as exc:
        raise to_http_exception(exc, lang=lang) from exc


@router.delete("/accounts/{account_id}", response_model=MessageResponse)
def deactivate_account_route(account_id: int, session: Session = Depends(get_session)):
    lang = get_user_language(session)
    try:
        remove_account(session, account_id, lang)
    except ApplicationError as exc:
        raise to_http_exception(exc, lang=lang) from exc
    return MessageResponse(message=t("account.deactivated", lang=lang))
