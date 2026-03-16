"""Tax wrapper quota routes."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from api.schemas.wrapper import AllQuotasResponse, RestorationForecastResponse
from application.portfolio.wrapper_service import (
    get_all_wrapper_quotas,
    get_restoration_forecast,
)
from domain.constants import DEFAULT_USER_ID, NISA_RESTORATION_POLICY
from infrastructure.database import get_session

router = APIRouter(tags=["wrapper"])


@router.get("/wrappers/quota", response_model=AllQuotasResponse)
def quota_status(
    year: int | None = Query(default=None, ge=2000, le=2100),
    as_of: date | None = Query(default=None),
    session: Session = Depends(get_session),
):
    as_of_date = as_of or date.today()
    target_year = year or as_of_date.year
    quotas = get_all_wrapper_quotas(session, DEFAULT_USER_ID, target_year, as_of_date)
    return {
        "year": target_year,
        "as_of": as_of_date,
        "restoration_policy": NISA_RESTORATION_POLICY,
        "quotas": quotas,
    }


@router.get(
    "/wrappers/restoration-forecast",
    response_model=RestorationForecastResponse,
)
def restoration_forecast(session: Session = Depends(get_session)):
    return get_restoration_forecast(session, DEFAULT_USER_ID)
