"""Transaction CRUD routes."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from api.schemas import MessageResponse
from api.schemas.transaction import TransactionRequest, TransactionResponse
from application.portfolio.transaction_service import (
    create_transaction,
    get_transaction,
    list_transactions,
    remove_transaction,
)
from i18n import get_user_language, t
from infrastructure.database import get_session

router = APIRouter(tags=["transactions"])


@router.get(
    "/transactions",
    response_model=list[TransactionResponse],
    summary="List transactions",
)
def get_transactions(
    ticker: str | None = Query(None),
    account_id: int | None = Query(None),
    holding_id: int | None = Query(None),
    start: date | None = Query(None),
    end: date | None = Query(None),
    limit: int = Query(500, ge=1, le=1000),
    session: Session = Depends(get_session),
):
    return list_transactions(
        session,
        ticker=ticker,
        account_id=account_id,
        holding_id=holding_id,
        start_date=start,
        end_date=end,
        limit=limit,
    )


@router.post(
    "/transactions",
    response_model=TransactionResponse,
    status_code=201,
    summary="Add a transaction",
)
def add_transaction(
    body: TransactionRequest,
    session: Session = Depends(get_session),
):
    lang = get_user_language(session)
    return create_transaction(session, body.model_dump(), lang)


@router.get(
    "/transactions/{txn_id}",
    response_model=TransactionResponse,
    summary="Get a transaction",
)
def get_single_transaction(
    txn_id: int,
    session: Session = Depends(get_session),
):
    lang = get_user_language(session)
    return get_transaction(session, txn_id, lang)


@router.delete(
    "/transactions/{txn_id}",
    response_model=MessageResponse,
    summary="Delete a transaction",
)
def delete_single_transaction(
    txn_id: int,
    session: Session = Depends(get_session),
):
    lang = get_user_language(session)
    remove_transaction(session, txn_id, lang)
    return MessageResponse(message=t("transaction.deleted", lang=lang))
