"""API schemas for stock split detection and application."""

from pydantic import BaseModel, Field


class StockSplitHoldingPreview(BaseModel):
    """Before/after preview for one holding that will be affected by the split."""

    account_id: int
    account_name: str | None = None
    before_qty: float
    after_qty: float
    before_cost_basis: float | None = None
    after_cost_basis: float | None = None


class StockSplitEventResponse(BaseModel):
    """Single stock split event payload."""

    id: int
    ticker: str
    split_date: str
    ratio: float
    ratio_label: str
    status: str
    detected_at: str
    applied_at: str | None = None
    preview: list[StockSplitHoldingPreview] = Field(default_factory=list)


class StockSplitCheckResponse(BaseModel):
    """Response payload for split detection check."""

    checked_tickers: int
    detected: int
    auto_applied: int
    events: list[StockSplitEventResponse] = Field(default_factory=list)


class StockSplitApplyResponse(BaseModel):
    """Response payload for applying a split event."""

    event: StockSplitEventResponse
    status: str
    applied_accounts: int
    transactions: int


class StockSplitApplyAllResponse(BaseModel):
    """Response payload for applying all pending split events."""

    total: int
    applied: int
    results: list[StockSplitApplyResponse] = Field(default_factory=list)


class StockSplitDismissResponse(BaseModel):
    """Response payload for dismissing a split event."""

    event: StockSplitEventResponse
    status: str
