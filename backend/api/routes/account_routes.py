"""Account CRUD and aggregation routes."""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from api.schemas import MessageResponse
from api.schemas.account import (
    AccountCashBalanceItem,
    AccountRequest,
    AccountResponse,
    AccountSummaryItem,
    AccountUpdateRequest,
)
from application.portfolio.account_service import (
    create_account,
    get_account_cash_balances,
    get_account_summary,
    list_accounts,
    remove_account,
    update_account,
)
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
    return create_account(session, body.model_dump(), lang)


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
    return get_account_cash_balances(session, account_id, lang)


@router.put("/accounts/{account_id}", response_model=AccountResponse)
def edit_account(
    account_id: int,
    body: AccountUpdateRequest,
    session: Session = Depends(get_session),
):
    lang = get_user_language(session)
    return update_account(
        session, account_id, body.model_dump(exclude_unset=True), lang
    )


@router.delete("/accounts/{account_id}", response_model=MessageResponse)
def deactivate_account_route(account_id: int, session: Session = Depends(get_session)):
    lang = get_user_language(session)
    remove_account(session, account_id, lang)
    return MessageResponse(message=t("account.deactivated", lang=lang))
