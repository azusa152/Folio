"""Transaction CRUD routes."""

import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from api.schemas import ImportResponse, MessageResponse
from api.schemas.transaction import (
    TransactionImportRequest,
    TransactionRequest,
    TransactionResponse,
)
from application.portfolio.transaction_service import (
    create_transaction,
    export_transactions_csv_rows,
    get_transaction,
    import_transactions,
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


@router.post(
    "/transactions/import",
    response_model=ImportResponse,
    summary="Import transactions in bulk",
)
def add_transactions_import(
    body: TransactionImportRequest,
    session: Session = Depends(get_session),
):
    lang = get_user_language(session)
    return import_transactions(
        session,
        [item.model_dump() for item in body.items],
        lang,
        account_id=body.account_id,
    )


@router.get(
    "/transactions/export-csv",
    summary="Export transactions as CSV",
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "CSV export",
            "content": {"text/csv": {"schema": {"type": "string", "format": "binary"}}},
        }
    },
)
def export_transactions_csv(
    ticker: str | None = Query(None),
    account_id: int | None = Query(None),
    start: date | None = Query(None),
    end: date | None = Query(None),
    limit: int | None = Query(None, ge=1, le=100000),
    session: Session = Depends(get_session),
) -> StreamingResponse:
    rows = export_transactions_csv_rows(
        session,
        ticker=ticker,
        account_id=account_id,
        start_date=start,
        end_date=end,
        limit=limit,
    )
    fieldnames = [
        "transaction_date",
        "ticker",
        "transaction_type",
        "quantity",
        "price",
        "total_amount",
        "currency",
        "fx_rate",
        "fee",
        "note",
        "account_name",
    ]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    output.seek(0)
    filename = f"transactions_{date.today().strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
