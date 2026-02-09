"""
API — 掃描路由。
"""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from api.schemas import ScanResponse
from application.services import run_scan
from infrastructure.database import get_session

router = APIRouter()


@router.post("/scan", response_model=ScanResponse)
def run_scan_route(
    session: Session = Depends(get_session),
) -> ScanResponse:
    """V2 三層漏斗掃描。"""
    result = run_scan(session)
    return ScanResponse(**result)
