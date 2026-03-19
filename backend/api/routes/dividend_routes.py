"""API routes for dividend detection and application."""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from api.schemas.dividend import (
    DividendApplyAllResponse,
    DividendApplyResponse,
    DividendCheckResponse,
    DividendDismissResponse,
    DividendEventResponse,
)
from application.portfolio.dividend_service import (
    apply_all_pending_dividends,
    apply_dividend,
    build_dividend_preview,
    check_dividends,
    dismiss_dividend,
    list_dividend_events,
    serialize_dividend_event,
)
from i18n import get_user_language
from infrastructure.database import get_session

router = APIRouter(tags=["dividends"])


@router.post(
    "/dividends/check",
    response_model=DividendCheckResponse,
    summary="Check held tickers for dividend events",
)
def check_dividends_route(
    session: Session = Depends(get_session),
) -> DividendCheckResponse:
    result = check_dividends(session)
    return DividendCheckResponse(**result)


@router.get(
    "/dividends/pending",
    response_model=list[DividendEventResponse],
    summary="List pending dividend events",
)
def list_pending_dividends(
    session: Session = Depends(get_session),
) -> list[DividendEventResponse]:
    events = list_dividend_events(session, status="pending")
    return [
        DividendEventResponse(
            **serialize_dividend_event(
                event, preview=build_dividend_preview(session, event)
            )
        )
        for event in events
    ]


@router.post(
    "/dividends/{event_id}/apply",
    response_model=DividendApplyResponse,
    summary="Apply one dividend event",
)
def apply_dividend_route(
    event_id: int,
    session: Session = Depends(get_session),
) -> DividendApplyResponse:
    lang = get_user_language(session)
    result = apply_dividend(session, event_id, lang=lang)
    return DividendApplyResponse(**result)


@router.post(
    "/dividends/{event_id}/dismiss",
    response_model=DividendDismissResponse,
    summary="Dismiss one dividend event",
)
def dismiss_dividend_route(
    event_id: int,
    session: Session = Depends(get_session),
) -> DividendDismissResponse:
    lang = get_user_language(session)
    result = dismiss_dividend(session, event_id, lang=lang)
    return DividendDismissResponse(**result)


@router.post(
    "/dividends/apply-all",
    response_model=DividendApplyAllResponse,
    summary="Apply all pending dividend events",
)
def apply_all_dividends_route(
    session: Session = Depends(get_session),
) -> DividendApplyAllResponse:
    lang = get_user_language(session)
    result = apply_all_pending_dividends(session, lang=lang)
    return DividendApplyAllResponse(**result)
