"""Transaction API schemas."""

from datetime import date

from pydantic import BaseModel, Field, field_validator

from domain.enums import TransactionType


class TransactionRequest(BaseModel):
    account_id: int = Field(..., description="帳戶 ID（必填）")
    holding_id: int | None = None
    ticker: str = Field(..., min_length=1, max_length=20)
    transaction_type: str = Field(
        ..., description="BUY / SELL / DIVIDEND / DEPOSIT / WITHDRAWAL"
    )
    quantity: float = Field(..., gt=0)
    price: float | None = None
    total_amount: float = Field(..., description="Total transaction amount")
    currency: str = Field(default="USD", max_length=10)
    fx_rate: float | None = None
    fee: float = Field(default=0.0, ge=0)
    note: str = Field(default="", max_length=500)
    transaction_date: date

    @field_validator("ticker")
    @classmethod
    def ticker_must_be_uppercase(cls, v: str) -> str:
        """Ticker must be uppercase."""
        return v.upper().strip()

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, v: str) -> str:
        """Currency code must be uppercase."""
        return v.upper().strip()

    @field_validator("transaction_type")
    @classmethod
    def validate_transaction_type(cls, v: str) -> str:
        """Transaction type must be one of the supported enum values."""
        normalized = v.upper().strip()
        return TransactionType(normalized).value


class TransactionResponse(BaseModel):
    id: int
    user_id: str
    account_id: int | None = None
    holding_id: int | None = None
    ticker: str
    transaction_type: str
    quantity: float
    price: float | None = None
    total_amount: float
    currency: str
    fx_rate: float | None = None
    fee: float
    note: str
    transaction_date: date
    created_at: str


class TransactionImportItem(BaseModel):
    account_id: int | None = None
    ticker: str = Field(..., min_length=1, max_length=20)
    transaction_type: str = Field(
        ..., description="BUY / SELL / DIVIDEND / DEPOSIT / WITHDRAWAL"
    )
    quantity: float = Field(..., gt=0)
    price: float | None = None
    total_amount: float = Field(..., description="Total transaction amount")
    currency: str = Field(default="USD", max_length=10)
    fx_rate: float | None = None
    fee: float = Field(default=0.0, ge=0)
    note: str = Field(default="", max_length=500)
    transaction_date: date

    @field_validator("ticker")
    @classmethod
    def import_ticker_must_be_uppercase(cls, v: str) -> str:
        return v.upper().strip()

    @field_validator("currency")
    @classmethod
    def import_currency_must_be_uppercase(cls, v: str) -> str:
        return v.upper().strip()

    @field_validator("transaction_type")
    @classmethod
    def import_validate_transaction_type(cls, v: str) -> str:
        normalized = v.upper().strip()
        return TransactionType(normalized).value


class TransactionImportRequest(BaseModel):
    account_id: int | None = None
    items: list[TransactionImportItem]
