"""Portfolio analytics routes — drawdown, risk metrics, contribution."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlmodel import Session

from api.schemas.analytics import (
    ContributionGrowthPoint,
    DrawdownPointResponse,
    RiskMetricsResponse,
)
from application.portfolio.analytics_service import (
    get_contribution_vs_growth,
    get_drawdown_series,
    get_risk_metrics,
)
from infrastructure.database import get_session

router = APIRouter(tags=["analytics"])


def _validate_date_range(start: date | None, end: date | None) -> None:
    if (start is None) != (end is None):
        raise HTTPException(
            status_code=422,
            detail="start 與 end 必須同時提供",
        )
    if start is not None and end is not None and start > end:
        raise HTTPException(status_code=422, detail="start 不得晚於 end")


@router.get("/analytics/drawdown", response_model=list[DrawdownPointResponse])
def drawdown(
    response: Response,
    start: date | None = Query(None),
    end: date | None = Query(None),
    session: Session = Depends(get_session),
):
    _validate_date_range(start, end)
    response.headers["Cache-Control"] = (
        "private, max-age=300, stale-while-revalidate=3600"
    )
    return get_drawdown_series(session, start=start, end=end)


@router.get("/analytics/risk-metrics", response_model=RiskMetricsResponse)
def risk_metrics(
    response: Response,
    start: date | None = Query(None),
    end: date | None = Query(None),
    session: Session = Depends(get_session),
):
    _validate_date_range(start, end)
    response.headers["Cache-Control"] = (
        "private, max-age=300, stale-while-revalidate=3600"
    )
    return get_risk_metrics(session, start=start, end=end)


@router.get(
    "/analytics/contribution-growth",
    response_model=list[ContributionGrowthPoint],
)
def contribution_growth(
    response: Response,
    start: date | None = Query(None),
    end: date | None = Query(None),
    session: Session = Depends(get_session),
):
    _validate_date_range(start, end)
    response.headers["Cache-Control"] = (
        "private, max-age=300, stale-while-revalidate=3600"
    )
    return get_contribution_vs_growth(session, start=start, end=end)
