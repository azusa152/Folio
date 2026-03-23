"""
API — Fund Sector Weight 路由。
允許查詢、設定及刪除基金的行業板塊權重覆寫，用於改善 Sector Exposure 分析精度。
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from api.schemas.fund_sector import (
    FundSectorWeightItem,
    FundSectorWeightsRequest,
    FundSectorWeightsResponse,
)
from application.portfolio.fund_sector_service import (
    get_fund_sector_source,
    get_sector_weights,
    remove_sector_weights,
    set_sector_weights,
)
from infrastructure.database import get_session
from logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/funds", tags=["funds"])


@router.get(
    "/{fund_code}/sector-weights",
    response_model=FundSectorWeightsResponse,
    summary="Get sector weight overrides for a fund",
)
def get_fund_sector_weights(
    fund_code: str,
    session: Session = Depends(get_session),
) -> FundSectorWeightsResponse:
    """Return stored sector weight overrides for a fund code."""
    weights = get_sector_weights(session, fund_code)
    source = get_fund_sector_source(session, fund_code)
    items = [
        FundSectorWeightItem(sector=s, weight=w) for s, w in sorted(weights.items())
    ]
    return FundSectorWeightsResponse(
        fund_code=fund_code.upper().strip(),
        weights=items,
        source=source,
        total_weight=round(sum(i.weight for i in items), 6),
    )


@router.put(
    "/{fund_code}/sector-weights",
    response_model=FundSectorWeightsResponse,
    summary="Set sector weight overrides for a fund",
)
def set_fund_sector_weights(
    fund_code: str,
    body: FundSectorWeightsRequest,
    session: Session = Depends(get_session),
) -> FundSectorWeightsResponse:
    """Replace all sector weight overrides for a fund (delete-then-insert)."""
    weights = {item.sector: item.weight for item in body.weights}
    if not weights:
        raise HTTPException(status_code=422, detail="weights must not be empty")

    set_sector_weights(session, fund_code, weights, source=body.source)
    logger.info(
        "基金 %s 行業板塊覆寫已更新（%d 板塊，來源=%s）。",
        fund_code,
        len(weights),
        body.source,
    )

    items = [
        FundSectorWeightItem(sector=s, weight=w) for s, w in sorted(weights.items())
    ]
    return FundSectorWeightsResponse(
        fund_code=fund_code.upper().strip(),
        weights=items,
        source=body.source,
        total_weight=round(sum(i.weight for i in items), 6),
    )


@router.delete(
    "/{fund_code}/sector-weights",
    summary="Remove sector weight overrides for a fund",
)
def delete_fund_sector_weights(
    fund_code: str,
    session: Session = Depends(get_session),
) -> dict:
    """Delete all stored sector weight overrides for a fund."""
    count = remove_sector_weights(session, fund_code)
    logger.info("基金 %s 行業板塊覆寫已刪除（%d 筆）。", fund_code, count)
    return {"fund_code": fund_code.upper().strip(), "deleted": count}
