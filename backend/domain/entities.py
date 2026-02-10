"""
Domain — 資料庫實體 (SQLModel Tables)。
定義核心業務實體：Stock、ThesisLog、RemovalLog。
"""

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel

from domain.enums import StockCategory


class Stock(SQLModel, table=True):
    """追蹤清單中的個股。"""

    ticker: str = Field(primary_key=True, description="股票代號")
    category: StockCategory = Field(description="分類")
    current_thesis: str = Field(default="", description="最新觀點")
    current_tags: str = Field(default="", description="最新標籤（逗號分隔）")
    display_order: int = Field(default=0, description="顯示順位（數字越小越前面）")
    last_scan_signal: str = Field(default="NORMAL", description="上次掃描訊號")
    is_active: bool = Field(default=True, description="是否追蹤中")


class ThesisLog(SQLModel, table=True):
    """觀點版控紀錄。"""

    id: Optional[int] = Field(default=None, primary_key=True)
    stock_ticker: str = Field(foreign_key="stock.ticker", description="對應股票代號")
    content: str = Field(description="觀點內容")
    tags: str = Field(default="", description="該版本的標籤快照（逗號分隔）")
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


class ScanLog(SQLModel, table=True):
    """掃描紀錄（每次掃描、每檔股票一筆）。"""

    id: Optional[int] = Field(default=None, primary_key=True)
    stock_ticker: str = Field(foreign_key="stock.ticker", description="對應股票代號")
    signal: str = Field(description="掃描訊號（ScanSignal value）")
    market_status: str = Field(description="掃描時的市場情緒")
    details: str = Field(default="", description="警報詳情（JSON）")
    scanned_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="掃描時間",
    )


class PriceAlert(SQLModel, table=True):
    """自訂價格警報。"""

    id: Optional[int] = Field(default=None, primary_key=True)
    stock_ticker: str = Field(foreign_key="stock.ticker", description="對應股票代號")
    metric: str = Field(description="指標名稱：rsi, price, bias")
    operator: str = Field(description="比較運算：lt, gt")
    threshold: float = Field(description="門檻值")
    is_active: bool = Field(default=True, description="是否啟用")
    last_triggered_at: Optional[datetime] = Field(
        default=None, description="上次觸發時間"
    )
