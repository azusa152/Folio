"""
API — 股票管理路由。
薄控制器：僅負責解析請求、呼叫 Service、回傳回應。
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from api.schemas import (
    CategoryUpdateRequest,
    DeactivateRequest,
    ReorderRequest,
    RemovedStockResponse,
    StockResponse,
    TickerCreateRequest,
)
from application.services import (
    CategoryUnchangedError,
    StockAlreadyExistsError,
    StockAlreadyInactiveError,
    StockNotFoundError,
    create_stock,
    deactivate_stock,
    export_stocks,
    get_removal_history,
    list_active_stocks,
    list_removed_stocks,
    update_display_order,
    update_stock_category,
)
from infrastructure.database import get_session
from infrastructure.market_data import analyze_moat_trend, get_technical_signals

router = APIRouter()


@router.post("/ticker", response_model=StockResponse)
def create_ticker_route(
    payload: TickerCreateRequest,
    session: Session = Depends(get_session),
) -> StockResponse:
    """新增股票到追蹤清單。"""
    try:
        stock = create_stock(
            session, payload.ticker, payload.category, payload.thesis, payload.tags
        )
    except StockAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return StockResponse(
        ticker=stock.ticker,
        category=stock.category,
        current_thesis=stock.current_thesis,
        current_tags=payload.tags,
        is_active=stock.is_active,
    )


@router.get("/stocks", response_model=list[StockResponse])
def list_stocks_route(
    session: Session = Depends(get_session),
) -> list[StockResponse]:
    """取得所有追蹤中股票（僅 DB 資料，不含技術訊號）。"""
    results = list_active_stocks(session)
    return [StockResponse(**r) for r in results]


@router.put("/stocks/reorder")
def reorder_stocks_route(
    payload: ReorderRequest,
    session: Session = Depends(get_session),
) -> dict:
    """批次更新股票顯示順位。"""
    return update_display_order(session, payload.ordered_tickers)


@router.get("/ticker/{ticker}/signals")
def get_signals_route(ticker: str) -> dict:
    """取得指定股票的技術訊號（yfinance，含快取）。"""
    return get_technical_signals(ticker.upper()) or {}


@router.get("/stocks/export")
def export_stocks_route(
    session: Session = Depends(get_session),
) -> list[dict]:
    """匯出所有追蹤中股票（精簡格式，適用於 JSON 下載與匯入）。"""
    return export_stocks(session)


@router.get("/ticker/{ticker}/moat")
def get_moat_route(ticker: str) -> dict:
    """取得指定股票的護城河趨勢（毛利率 5 季走勢 + YoY 診斷）。"""
    return analyze_moat_trend(ticker.upper())


@router.patch("/ticker/{ticker}/category")
def update_category_route(
    ticker: str,
    payload: CategoryUpdateRequest,
    session: Session = Depends(get_session),
) -> dict:
    """切換股票分類。"""
    try:
        return update_stock_category(session, ticker, payload.category)
    except StockNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except CategoryUnchangedError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/ticker/{ticker}/deactivate")
def deactivate_ticker_route(
    ticker: str,
    payload: DeactivateRequest,
    session: Session = Depends(get_session),
) -> dict:
    """移除追蹤股票。"""
    try:
        return deactivate_stock(session, ticker, payload.reason)
    except StockNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except StockAlreadyInactiveError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/stocks/removed", response_model=list[RemovedStockResponse])
def list_removed_stocks_route(
    session: Session = Depends(get_session),
) -> list[RemovedStockResponse]:
    """取得所有已移除股票。"""
    results = list_removed_stocks(session)
    return [RemovedStockResponse(**r) for r in results]


@router.get("/ticker/{ticker}/removals")
def get_removal_history_route(
    ticker: str,
    session: Session = Depends(get_session),
) -> list[dict]:
    """取得指定股票的移除歷史。"""
    try:
        return get_removal_history(session, ticker)
    except StockNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
