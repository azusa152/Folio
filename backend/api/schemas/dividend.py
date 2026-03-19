"""API schemas for dividend detection and application."""

from pydantic import BaseModel, Field


class DividendHoldingPreview(BaseModel):
    """Estimated dividend cash impact for one holding."""

    account_id: int | None = None
    account_name: str | None = None
    shares: float
    amount_per_share: float
    estimated_cash: float
    currency: str


class DividendEventResponse(BaseModel):
    """Single dividend event payload."""

    id: int
    ticker: str
    ex_dividend_date: str
    amount_per_share: float
    status: str
    detected_at: str
    applied_at: str | None = None
    preview: list[DividendHoldingPreview] = Field(default_factory=list)


class DividendCheckResponse(BaseModel):
    """Response payload for dividend detection check."""

    checked_tickers: int
    detected: int
    auto_applied: int
    events: list[DividendEventResponse] = Field(default_factory=list)


class DividendApplyResponse(BaseModel):
    """Response payload for applying a dividend event."""

    event: DividendEventResponse
    status: str
    applied_accounts: int
    transactions: int


class DividendApplyAllResponse(BaseModel):
    """Response payload for applying all pending dividend events."""

    total: int
    applied: int
    results: list[DividendApplyResponse] = Field(default_factory=list)


class DividendDismissResponse(BaseModel):
    """Response payload for dismissing a dividend event."""

    event: DividendEventResponse
    status: str
