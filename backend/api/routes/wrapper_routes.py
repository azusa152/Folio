"""Tax wrapper quota routes."""

import tempfile
from datetime import date
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlmodel import Session

from api.schemas.wrapper import (
    AllQuotasResponse,
    DeTaxResponse,
    EligibilityCheckResponse,
    EligibleAssetsMetadataResponse,
    EligibleAssetsRefreshResponse,
    EligibleAssetsResponse,
    EligibleAssetsUploadResponse,
    RestorationForecastResponse,
    RoutingSuggestRequest,
    RoutingSuggestResponse,
)
from application.portfolio.eligibility_service import (
    check_asset_eligibility,
    get_eligible_assets,
    get_eligible_assets_metadata,
    refresh_eligible_assets,
)
from application.portfolio.eligible_sync_service import (
    sync_wrapper_from_official_source,
)
from application.portfolio.routing_service import (
    get_detax_suggestions,
    suggest_transaction_routing,
)
from application.portfolio.wrapper_service import (
    get_all_wrapper_quotas,
    get_restoration_forecast,
)
from domain.constants import (
    DEFAULT_LANGUAGE,
    DEFAULT_USER_ID,
    ERROR_INVALID_INPUT,
    NISA_RESTORATION_POLICY,
)
from i18n import t
from infrastructure.database import get_session

router = APIRouter(tags=["wrapper"])


def _error_detail(error_code: str, message_key: str) -> dict[str, str]:
    return {"error_code": error_code, "detail": t(message_key, lang=DEFAULT_LANGUAGE)}


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


@router.get(
    "/wrappers/{wrapper}/eligible-assets/metadata",
    response_model=EligibleAssetsMetadataResponse,
)
def eligible_assets_metadata(
    wrapper: str,
    session: Session = Depends(get_session),
):
    metadata = get_eligible_assets_metadata(session=session, wrapper=wrapper)
    return metadata


@router.post(
    "/wrappers/{wrapper}/eligible-assets/refresh",
    response_model=EligibleAssetsRefreshResponse,
)
def refresh_eligible_assets_endpoint(
    wrapper: str,
    session: Session = Depends(get_session),
):
    normalized_wrapper = wrapper.strip().lower()
    if normalized_wrapper not in {"nisa_tsumitate", "nisa_growth"}:
        raise HTTPException(
            status_code=422,
            detail=_error_detail(
                ERROR_INVALID_INPUT, "eligibility.refresh_unsupported_wrapper"
            ),
        )
    try:
        stats = sync_wrapper_from_official_source(session, normalized_wrapper)
    except (ValueError, httpx.HTTPError):
        raise HTTPException(
            status_code=422,
            detail=_error_detail(
                "ELIGIBILITY_REFRESH_FAILED", "eligibility.refresh_failed"
            ),
        ) from None
    except Exception:
        raise HTTPException(
            status_code=422,
            detail=_error_detail(
                "ELIGIBILITY_REFRESH_FAILED", "eligibility.refresh_failed"
            ),
        ) from None
    metadata = get_eligible_assets_metadata(session, normalized_wrapper)
    return {
        "wrapper": normalized_wrapper,
        "source": "official_sync",
        "stats": stats,
        "metadata": metadata,
    }


@router.post(
    "/wrappers/{wrapper}/eligible-assets/upload",
    response_model=EligibleAssetsUploadResponse,
)
async def upload_eligible_assets(
    wrapper: str,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    normalized_wrapper = wrapper.strip().lower()
    if normalized_wrapper not in {"nisa_tsumitate", "nisa_growth"}:
        raise HTTPException(
            status_code=422,
            detail=_error_detail(
                ERROR_INVALID_INPUT, "eligibility.upload_unsupported_wrapper"
            ),
        )
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".csv", ".xlsx"}:
        raise HTTPException(
            status_code=422,
            detail=_error_detail(
                ERROR_INVALID_INPUT, "eligibility.upload_invalid_format"
            ),
        )
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=_error_detail(
                ERROR_INVALID_INPUT, "eligibility.upload_file_too_large"
            ),
        )
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        try:
            stats = refresh_eligible_assets(
                session=session,
                wrapper=normalized_wrapper,
                file_path=tmp_path,
                source="manual_upload",
                autocommit=True,
            )
        except (ValueError, httpx.HTTPError):
            raise HTTPException(
                status_code=422,
                detail=_error_detail(
                    "ELIGIBILITY_UPLOAD_FAILED", "eligibility.upload_failed"
                ),
            ) from None
        except Exception:
            raise HTTPException(
                status_code=422,
                detail=_error_detail(
                    "ELIGIBILITY_UPLOAD_FAILED", "eligibility.upload_failed"
                ),
            ) from None
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    metadata = get_eligible_assets_metadata(session, normalized_wrapper)
    return {
        "wrapper": normalized_wrapper,
        "filename": file.filename or "",
        "source": "manual_upload",
        "stats": stats,
        "metadata": metadata,
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
