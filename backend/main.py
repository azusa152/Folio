"""
Azusa Radar — FastAPI 應用程式進入點。
負責建立 App、註冊路由、管理生命週期。
所有業務邏輯已移至 application/services.py。
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.scan_routes import router as scan_router
from api.stock_routes import router as stock_router
from api.thesis_routes import router as thesis_router
from infrastructure.database import create_db_and_tables
from logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Lifespan: 啟動時建立資料表
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Azusa Radar 後端啟動中 — 初始化資料庫...")
    create_db_and_tables()
    logger.info("資料庫初始化完成，服務就緒。")
    yield
    logger.info("Azusa Radar 後端關閉中...")


# ---------------------------------------------------------------------------
# App Factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Azusa Radar API",
    description="投資雷達 — V2.0 三層漏斗",
    version="2.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok", "service": "azusa-radar-backend"}


# ---------------------------------------------------------------------------
# 註冊路由
# ---------------------------------------------------------------------------

app.include_router(stock_router)
app.include_router(thesis_router)
app.include_router(scan_router)
