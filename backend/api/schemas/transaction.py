"""Transaction API schemas."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from domain.enums import StockCategory, TransactionType


class TransactionRequest(BaseModel):
    account_id: int = Field(..., description="帳戶 ID（必填）")
    holding_id: int | None = None
    ticker: str = Field(..., min_length=1, max_length=50)
    transaction_type: str = Field(
        ...,
        description=(
            "BUY / SELL / DIVIDEND / DEPOSIT / WITHDRAWAL / "
            "OPENING_BALANCE / ADJUSTMENT / STOCK_SPLIT / TRANSFER_IN / TRANSFER_OUT"
        ),
    )
    quantity: float = Field(...)
    price: float | None = None
    total_amount: float = Field(..., description="Total transaction amount")
    currency: str = Field(default="USD", max_length=10)
    fx_rate: float | None = None
    fee: float = Field(default=0.0, ge=0)
    note: str = Field(default="", max_length=500)
    thesis: str | None = Field(
        default=None,
        max_length=5000,
        description="Thesis used when auto-adding a new ticker to radar",
    )
    category: str | None = Field(
        default=None,
        description="Stock category used when auto-adding a new ticker to radar",
    )
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

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str | None) -> str | None:
        """Category must be one of supported stock categories when provided."""
        if v is None:
            return None
        normalized = v.strip()
        return StockCategory(normalized).value

    @model_validator(mode="after")
    def validate_quantity_by_type(self):
        """Allow signed quantity only for STOCK_SPLIT additive delta."""
        qty = float(self.quantity)
        txn_type = self.transaction_type.upper().strip()
        if txn_type == TransactionType.STOCK_SPLIT.value:
            if abs(qty) <= 0:
                raise ValueError("quantity must be non-zero for STOCK_SPLIT")
            return self
        if qty <= 0:
            raise ValueError("quantity must be greater than 0")
        return self


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
    auto_radar: bool = False
    category: str | None = None
    is_cash: bool | None = None


class TransactionImportItem(BaseModel):
    account_id: int | None = None
    ticker: str = Field(..., min_length=1, max_length=50)
    transaction_type: str = Field(
        ...,
        description=(
            "BUY / SELL / DIVIDEND / DEPOSIT / WITHDRAWAL / "
            "OPENING_BALANCE / ADJUSTMENT / STOCK_SPLIT / TRANSFER_IN / TRANSFER_OUT"
        ),
    )
    quantity: float = Field(...)
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

    @model_validator(mode="after")
    def import_validate_quantity_by_type(self):
        qty = float(self.quantity)
        txn_type = self.transaction_type.upper().strip()
        if txn_type == TransactionType.STOCK_SPLIT.value:
            if abs(qty) <= 0:
                raise ValueError("quantity must be non-zero for STOCK_SPLIT")
            return self
        if qty <= 0:
            raise ValueError("quantity must be greater than 0")
        return self


class TransactionImportRequest(BaseModel):
    account_id: int | None = None
    mode: Literal["append", "replace_account"] = "append"
    items: list[TransactionImportItem]
