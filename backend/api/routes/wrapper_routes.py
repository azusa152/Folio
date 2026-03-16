"""Tax wrapper quota routes."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from api.schemas.wrapper import (
    AllQuotasResponse,
    DeTaxResponse,
    EligibilityCheckResponse,
    EligibleAssetsResponse,
    RestorationForecastResponse,
    RoutingSuggestRequest,
    RoutingSuggestResponse,
)
from application.portfolio.eligibility_service import (
    check_asset_eligibility,
    get_eligible_assets,
)
from application.portfolio.routing_service import (
    get_detax_suggestions,
    suggest_transaction_routing,
)
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


@router.get(
    "/wrappers/{wrapper}/check-eligibility",
    response_model=EligibilityCheckResponse,
)
def check_eligibility_endpoint(
    wrapper: str,
    ticker: str = Query(..., min_length=1),
    broker: str | None = Query(default=None),
    session: Session = Depends(get_session),
):
    result = check_asset_eligibility(
        session=session,
        ticker=ticker,
        wrapper=wrapper,
        broker=broker,
    )
    return {
        "ticker": ticker.strip().upper(),
        "wrapper": wrapper.strip().lower(),
        "eligible": result.eligible,
        "reasons": result.reasons,
        "suggested_wrapper": result.suggested_wrapper,
    }


@router.get(
    "/wrappers/{wrapper}/eligible-assets",
    response_model=EligibleAssetsResponse,
)
def list_eligible_assets(
    wrapper: str,
    broker: str | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    session: Session = Depends(get_session),
):
    assets = get_eligible_assets(
        session=session,
        wrapper=wrapper,
        broker=broker,
        search=search,
        limit=limit,
    )
    return {
        "wrapper": wrapper.strip().lower(),
        "count": len(assets),
        "items": [
            {
                "ticker": asset.ticker,
                "fund_name": asset.fund_name,
                "asset_type": asset.asset_type,
                "broker": asset.broker,
                "trust_fee_pct": asset.trust_fee_pct,
            }
            for asset in assets
        ],
    }


@router.post("/wrappers/suggest-routing", response_model=RoutingSuggestResponse)
def suggest_routing(
    body: RoutingSuggestRequest,
    session: Session = Depends(get_session),
):
    suggestions = suggest_transaction_routing(
        session=session,
        ticker=body.ticker,
        total_amount=body.total_amount,
        user_id=DEFAULT_USER_ID,
    )
    return {
        "ticker": body.ticker.strip().upper(),
        "total_amount": float(body.total_amount),
        "suggestions": [
            {
                "wrapper": item.wrapper,
                "amount": item.amount,
                "reason": item.reason,
            }
            for item in suggestions
        ],
    }


@router.get("/wrappers/detax", response_model=DeTaxResponse)
def detax_opportunities(session: Session = Depends(get_session)):
    opportunities = get_detax_suggestions(
        session=session,
        user_id=DEFAULT_USER_ID,
    )
    return {
        "total_estimated_savings": round(
            sum(item.estimated_tax_saved for item in opportunities), 2
        ),
        "opportunities": [
            {
                "ticker": item.ticker,
                "account_id": item.account_id,
                "unrealized_loss": item.unrealized_loss,
                "estimated_tax_saved": item.estimated_tax_saved,
                "sell_quantity": item.sell_quantity,
                "reason": item.reason,
            }
            for item in opportunities
        ],
    }
