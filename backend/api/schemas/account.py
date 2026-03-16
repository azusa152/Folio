"""Account API schemas."""

from pydantic import BaseModel, Field

from domain.enums import TaxWrapperType


class AccountRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    broker: str = Field(..., min_length=1, max_length=100)
    account_type: str = Field(default="brokerage", max_length=50)
    tax_wrapper: TaxWrapperType | None = None
    currency: str = Field(default="USD", max_length=10)
    institution: str = Field(default="", max_length=200)
    note: str = Field(default="", max_length=500)


class AccountUpdateRequest(BaseModel):
    name: str | None = None
    broker: str | None = None
    account_type: str | None = None
    tax_wrapper: TaxWrapperType | None = None
    currency: str | None = None
    institution: str | None = None
    note: str | None = None


class AccountResponse(BaseModel):
    id: int
    user_id: str
    name: str
    broker: str
    account_type: str
    tax_wrapper: TaxWrapperType | None = None
    currency: str
    institution: str
    note: str
    is_active: bool
    created_at: str
    updated_at: str


class AccountCashBalanceItem(BaseModel):
    currency: str
    balance: float


class AccountSummaryItem(BaseModel):
    account: AccountResponse | None = None
    holdings_count: int
    tickers: list[str]
    cash_balances: list[AccountCashBalanceItem] = Field(default_factory=list)
