"""
Gooaye Radar — FastAPI 後端主程式
定義所有 API Routes，包含股票管理、觀點版控、全域掃描與 Telegram 通知。
"""

import os
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import requests as http_requests
from fastapi import Depends, FastAPI, HTTPException
from sqlmodel import Session, select, func

from database import create_db_and_tables, get_session
from logging_config import get_logger
from logic import get_technical_signals, scan_stock
from models import (
    DeactivateRequest,
    RemovalLog,
    RemovedStockResponse,
    ScanResult,
    Stock,
    StockCategory,
    StockResponse,
    ThesisCreateRequest,
    ThesisLog,
    TickerCreateRequest,
)

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Lifespan: 啟動時建立資料表
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Gooaye Radar 後端啟動中 — 初始化資料庫...")
    create_db_and_tables()
    logger.info("資料庫初始化完成，服務就緒。")
    yield
    logger.info("Gooaye Radar 後端關閉中...")


app = FastAPI(
    title="Gooaye Radar API",
    description="股癌投資雷達 — Phase 1 MVP",
    version="0.1.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

@app.get("/health")
def health_check() -> dict:
    return {"status": "ok", "service": "gooaye-radar-backend"}


# ---------------------------------------------------------------------------
# POST /ticker — 新增追蹤股票
# ---------------------------------------------------------------------------

@app.post("/ticker", response_model=StockResponse)
def create_ticker(
    payload: TickerCreateRequest,
    session: Session = Depends(get_session),
) -> StockResponse:
    """新增股票到追蹤清單，同時建立第一筆觀點紀錄。"""
    ticker_upper = payload.ticker.upper()
    logger.info("新增股票請求：%s（分類：%s）", ticker_upper, payload.category.value)

    # 檢查是否已存在
    existing = session.get(Stock, ticker_upper)
    if existing:
        logger.warning("股票 %s 已存在，拒絕重複新增。", ticker_upper)
        raise HTTPException(status_code=409, detail=f"股票 {ticker_upper} 已存在追蹤清單中。")

    # 建立 Stock
    stock = Stock(
        ticker=ticker_upper,
        category=payload.category,
        current_thesis=payload.thesis,
        is_active=True,
    )
    session.add(stock)

    # 建立第一筆 ThesisLog
    thesis_log = ThesisLog(
        stock_ticker=ticker_upper,
        content=payload.thesis,
        version=1,
    )
    session.add(thesis_log)
    session.commit()
    session.refresh(stock)

    logger.info("股票 %s 已成功新增至追蹤清單。", ticker_upper)

    return StockResponse(
        ticker=stock.ticker,
        category=stock.category,
        current_thesis=stock.current_thesis,
        is_active=stock.is_active,
    )


# ---------------------------------------------------------------------------
# POST /ticker/{ticker}/thesis — 新增觀點 (自動版控)
# ---------------------------------------------------------------------------

@app.post("/ticker/{ticker}/thesis")
def create_thesis(
    ticker: str,
    payload: ThesisCreateRequest,
    session: Session = Depends(get_session),
) -> dict:
    """為指定股票新增觀點，自動遞增版本號。"""
    ticker_upper = ticker.upper()
    logger.info("更新觀點請求：%s", ticker_upper)

    stock = session.get(Stock, ticker_upper)
    if not stock:
        logger.warning("找不到股票 %s，無法更新觀點。", ticker_upper)
        raise HTTPException(status_code=404, detail=f"找不到股票 {ticker_upper}。")

    # 查詢當前最大版本號
    statement = select(func.max(ThesisLog.version)).where(
        ThesisLog.stock_ticker == ticker_upper
    )
    max_version = session.exec(statement).one()
    new_version = (max_version or 0) + 1

    # 建立新 ThesisLog
    thesis_log = ThesisLog(
        stock_ticker=ticker_upper,
        content=payload.content,
        version=new_version,
    )
    session.add(thesis_log)

    # 更新 Stock 的 current_thesis
    stock.current_thesis = payload.content
    session.add(stock)
    session.commit()

    logger.info("股票 %s 觀點已更新至第 %d 版。", ticker_upper, new_version)

    return {
        "message": f"✅ {ticker_upper} 觀點已更新至第 {new_version} 版。",
        "version": new_version,
        "content": payload.content,
    }


# ---------------------------------------------------------------------------
# GET /ticker/{ticker}/thesis — 取得觀點歷史
# ---------------------------------------------------------------------------

@app.get("/ticker/{ticker}/thesis")
def get_thesis_history(
    ticker: str,
    session: Session = Depends(get_session),
) -> list[dict]:
    """取得指定股票的完整觀點版控歷史。"""
    ticker_upper = ticker.upper()

    stock = session.get(Stock, ticker_upper)
    if not stock:
        raise HTTPException(status_code=404, detail=f"找不到股票 {ticker_upper}。")

    statement = (
        select(ThesisLog)
        .where(ThesisLog.stock_ticker == ticker_upper)
        .order_by(ThesisLog.version.desc())  # type: ignore[union-attr]
    )
    logs = session.exec(statement).all()

    return [
        {
            "version": log.version,
            "content": log.content,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


# ---------------------------------------------------------------------------
# POST /ticker/{ticker}/deactivate — 移除追蹤 (含原因版控)
# ---------------------------------------------------------------------------

@app.post("/ticker/{ticker}/deactivate")
def deactivate_ticker(
    ticker: str,
    payload: DeactivateRequest,
    session: Session = Depends(get_session),
) -> dict:
    """移除追蹤股票，記錄移除原因。"""
    ticker_upper = ticker.upper()
    logger.info("移除追蹤請求：%s", ticker_upper)

    stock = session.get(Stock, ticker_upper)
    if not stock:
        logger.warning("找不到股票 %s，無法移除。", ticker_upper)
        raise HTTPException(status_code=404, detail=f"找不到股票 {ticker_upper}。")

    if not stock.is_active:
        raise HTTPException(status_code=409, detail=f"股票 {ticker_upper} 已經是移除狀態。")

    # 設為停用
    stock.is_active = False
    session.add(stock)

    # 建立移除紀錄
    removal_log = RemovalLog(
        stock_ticker=ticker_upper,
        reason=payload.reason,
    )
    session.add(removal_log)

    # 同時在觀點歷史中記錄移除事件
    max_version_stmt = select(func.max(ThesisLog.version)).where(
        ThesisLog.stock_ticker == ticker_upper
    )
    max_version = session.exec(max_version_stmt).one()
    new_version = (max_version or 0) + 1

    thesis_log = ThesisLog(
        stock_ticker=ticker_upper,
        content=f"[已移除] {payload.reason}",
        version=new_version,
    )
    session.add(thesis_log)

    session.commit()
    logger.info("股票 %s 已移除追蹤（原因：%s）。", ticker_upper, payload.reason)

    return {
        "message": f"✅ {ticker_upper} 已從追蹤清單移除。",
        "reason": payload.reason,
    }


# ---------------------------------------------------------------------------
# GET /stocks/removed — 取得所有已移除股票
# ---------------------------------------------------------------------------

@app.get("/stocks/removed", response_model=list[RemovedStockResponse])
def list_removed_stocks(
    session: Session = Depends(get_session),
) -> list[RemovedStockResponse]:
    """取得所有已移除的股票，含最新移除原因。"""
    logger.info("取得已移除股票清單...")
    statement = select(Stock).where(Stock.is_active == False)  # noqa: E712
    stocks = session.exec(statement).all()

    results: list[RemovedStockResponse] = []
    for stock in stocks:
        # 取得最新的移除紀錄
        removal_stmt = (
            select(RemovalLog)
            .where(RemovalLog.stock_ticker == stock.ticker)
            .order_by(RemovalLog.created_at.desc())  # type: ignore[union-attr]
        )
        latest_removal = session.exec(removal_stmt).first()

        results.append(
            RemovedStockResponse(
                ticker=stock.ticker,
                category=stock.category,
                current_thesis=stock.current_thesis,
                removal_reason=latest_removal.reason if latest_removal else "未知",
                removed_at=latest_removal.created_at.isoformat() if latest_removal and latest_removal.created_at else None,
            )
        )

    logger.info("共 %d 檔已移除股票。", len(results))
    return results


# ---------------------------------------------------------------------------
# GET /ticker/{ticker}/removals — 取得移除歷史
# ---------------------------------------------------------------------------

@app.get("/ticker/{ticker}/removals")
def get_removal_history(
    ticker: str,
    session: Session = Depends(get_session),
) -> list[dict]:
    """取得指定股票的完整移除紀錄歷史。"""
    ticker_upper = ticker.upper()

    stock = session.get(Stock, ticker_upper)
    if not stock:
        raise HTTPException(status_code=404, detail=f"找不到股票 {ticker_upper}。")

    statement = (
        select(RemovalLog)
        .where(RemovalLog.stock_ticker == ticker_upper)
        .order_by(RemovalLog.created_at.desc())  # type: ignore[union-attr]
    )
    logs = session.exec(statement).all()

    return [
        {
            "reason": log.reason,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


# ---------------------------------------------------------------------------
# GET /stocks — 取得所有追蹤股票 (含最新技術指標)
# ---------------------------------------------------------------------------

@app.get("/stocks", response_model=list[StockResponse])
def list_stocks(
    session: Session = Depends(get_session),
) -> list[StockResponse]:
    """取得所有啟用中的追蹤股票，含最新技術訊號。"""
    logger.info("取得所有追蹤股票清單...")
    statement = select(Stock).where(Stock.is_active == True)  # noqa: E712
    stocks = session.exec(statement).all()
    logger.info("共 %d 檔追蹤中股票，開始取得技術訊號。", len(stocks))

    results: list[StockResponse] = []
    for stock in stocks:
        signals = get_technical_signals(stock.ticker)
        results.append(
            StockResponse(
                ticker=stock.ticker,
                category=stock.category,
                current_thesis=stock.current_thesis,
                is_active=stock.is_active,
                signals=signals,
            )
        )

    return results


# ---------------------------------------------------------------------------
# POST /scan — 全域掃描 + Telegram 通知
# ---------------------------------------------------------------------------

def _send_telegram_message(text: str) -> None:
    """透過 Telegram Bot API 發送通知。"""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    if not token or not chat_id or token.startswith("your-"):
        logger.debug("Telegram Token 未設定，跳過發送通知。")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        http_requests.post(
            url,
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        logger.info("Telegram 通知已發送。")
    except Exception as e:
        logger.error("Telegram 通知發送失敗：%s", e)


@app.post("/scan")
def run_scan(
    session: Session = Depends(get_session),
) -> list[ScanResult]:
    """
    執行全域掃描，依分類觸發不同檢查邏輯：
    - Trend_Setter: RSI < 30 或跌破 200MA
    - Moat: 毛利 YoY 衰退
    - Growth: 跌破 60MA
    掃描結果透過 Telegram Bot 發送通知。
    """
    logger.info("全域掃描啟動...")
    statement = select(Stock).where(Stock.is_active == True)  # noqa: E712
    stocks = session.exec(statement).all()
    logger.info("掃描對象：%d 檔股票。", len(stocks))

    results: list[ScanResult] = []
    all_alerts: list[str] = []

    for stock in stocks:
        alerts = scan_stock(stock.ticker, stock.category.value)
        results.append(
            ScanResult(
                ticker=stock.ticker,
                category=stock.category,
                alerts=alerts,
            )
        )
        all_alerts.extend(alerts)

    # 發送 Telegram 通知
    if all_alerts:
        logger.warning("掃描發現 %d 項警報。", len(all_alerts))
        for alert in all_alerts:
            logger.warning("  警報：%s", alert)
        header = "🔔 <b>Gooaye Radar 掃描警報</b>\n\n"
        body = "\n".join(all_alerts)
        _send_telegram_message(header + body)
    else:
        logger.info("掃描完成，無異常警報。")
        _send_telegram_message("✅ Gooaye Radar 掃描完成 — 目前無異常警報。")

    return results
