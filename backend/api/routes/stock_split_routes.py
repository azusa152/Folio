"""API routes for stock split detection and application."""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from api.schemas.stock_split import (
    StockSplitApplyAllResponse,
    StockSplitApplyResponse,
    StockSplitCheckResponse,
    StockSplitDismissResponse,
    StockSplitEventResponse,
)
from application.portfolio.stock_split_service import (
    apply_all_pending_splits,
    apply_split,
    build_split_preview,
    check_splits,
    dismiss_split,
    list_split_events,
    serialize_split_event,
)
from i18n import get_user_language
from infrastructure.database import get_session

router = APIRouter(tags=["stock-splits"])


@router.post(
    "/stock-splits/check",
    response_model=StockSplitCheckResponse,
    summary="Check held tickers for stock split events",
)
def check_stock_splits(
    session: Session = Depends(get_session),
) -> StockSplitCheckResponse:
    result = check_splits(session)
    return StockSplitCheckResponse(**result)


@router.get(
    "/stock-splits/pending",
    response_model=list[StockSplitEventResponse],
    summary="List pending stock split events",
)
def list_pending_stock_splits(
    session: Session = Depends(get_session),
) -> list[StockSplitEventResponse]:
    events = list_split_events(session, status="pending")
    return [
        StockSplitEventResponse(
            **serialize_split_event(event, preview=build_split_preview(session, event))
        )
        for event in events
    ]


@router.post(
    "/stock-splits/{event_id}/apply",
    response_model=StockSplitApplyResponse,
    summary="Apply one stock split event",
)
def apply_stock_split(
    event_id: int,
    session: Session = Depends(get_session),
) -> StockSplitApplyResponse:
    lang = get_user_language(session)
    result = apply_split(session, event_id, lang=lang)
    return StockSplitApplyResponse(**result)


@router.post(
    "/stock-splits/{event_id}/dismiss",
    response_model=StockSplitDismissResponse,
    summary="Dismiss one stock split event",
)
def dismiss_stock_split(
    event_id: int,
    session: Session = Depends(get_session),
) -> StockSplitDismissResponse:
    lang = get_user_language(session)
    result = dismiss_split(session, event_id, lang=lang)
    return StockSplitDismissResponse(**result)


@router.post(
    "/stock-splits/apply-all",
    response_model=StockSplitApplyAllResponse,
    summary="Apply all pending stock split events",
)
def apply_all_stock_splits(
    session: Session = Depends(get_session),
) -> StockSplitApplyAllResponse:
    lang = get_user_language(session)
    result = apply_all_pending_splits(session, lang=lang)
    return StockSplitApplyAllResponse(**result)
