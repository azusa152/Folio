"""
Gooaye Radar — 資料庫模型定義 (SQLModel)
包含 Stock (追蹤清單)、ThesisLog (觀點版控) 與 RemovalLog (移除紀錄)。
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel
from sqlmodel import Field, SQLModel


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class StockCategory(str, Enum):
    """股票分類：風向球 / 護城河 / 成長夢想"""
    TREND_SETTER = "Trend_Setter"
    MOAT = "Moat"
    GROWTH = "Growth"


# ---------------------------------------------------------------------------
# Database Tables
# ---------------------------------------------------------------------------

class Stock(SQLModel, table=True):
    """追蹤清單中的個股。"""
    ticker: str = Field(primary_key=True, description="股票代號")
    category: StockCategory = Field(description="分類")
    current_thesis: str = Field(default="", description="最新觀點")
    is_active: bool = Field(default=True, description="是否追蹤中")


class ThesisLog(SQLModel, table=True):
    """觀點版控紀錄。"""
    id: Optional[int] = Field(default=None, primary_key=True)
    stock_ticker: str = Field(foreign_key="stock.ticker", description="對應股票代號")
    content: str = Field(description="觀點內容")
    version: int = Field(description="版本號")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="建立時間",
    )


class RemovalLog(SQLModel, table=True):
    """移除紀錄（含版控，同一檔股票可多次移除）。"""
    id: Optional[int] = Field(default=None, primary_key=True)
    stock_ticker: str = Field(foreign_key="stock.ticker", description="對應股票代號")
    reason: str = Field(description="移除原因")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="移除時間",
    )


# ---------------------------------------------------------------------------
# Pydantic Request / Response Schemas
# ---------------------------------------------------------------------------

class TickerCreateRequest(BaseModel):
    """POST /ticker 請求 Body。"""
    ticker: str
    category: StockCategory
    thesis: str


class ThesisCreateRequest(BaseModel):
    """POST /ticker/{ticker}/thesis 請求 Body。"""
    content: str


class StockResponse(BaseModel):
    """GET /stocks 回傳的單筆股票資料。"""
    ticker: str
    category: StockCategory
    current_thesis: str
    is_active: bool
    signals: Optional[dict] = None


class DeactivateRequest(BaseModel):
    """POST /ticker/{ticker}/deactivate 請求 Body。"""
    reason: str


class RemovedStockResponse(BaseModel):
    """GET /stocks/removed 回傳的單筆已移除股票資料。"""
    ticker: str
    category: StockCategory
    current_thesis: str
    removal_reason: str
    removed_at: Optional[str] = None


class ScanResult(BaseModel):
    """POST /scan 回傳的掃描結果。"""
    ticker: str
    category: StockCategory
    alerts: list[str]
