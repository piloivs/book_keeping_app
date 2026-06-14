from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .models import AccountType


class AccountCreate(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=120)
    type: AccountType
    description: str | None = None


class AccountRead(AccountCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime
    balance: Decimal = Decimal("0.00")


class JournalLineCreate(BaseModel):
    account_id: int
    debit: Decimal = Decimal("0.00")
    credit: Decimal = Decimal("0.00")
    description: str | None = Field(default=None, max_length=180)

    @field_validator("debit", "credit")
    @classmethod
    def amount_cannot_be_negative(cls, value: Decimal) -> Decimal:
        if value < 0:
            raise ValueError("Amounts cannot be negative.")
        return value.quantize(Decimal("0.01"))

    @model_validator(mode="after")
    def line_has_one_side(self) -> "JournalLineCreate":
        if self.debit == 0 and self.credit == 0:
            raise ValueError("Each line needs a debit or credit amount.")
        if self.debit > 0 and self.credit > 0:
            raise ValueError("A line cannot have both debit and credit.")
        return self


class JournalEntryCreate(BaseModel):
    entry_date: date
    memo: str = Field(min_length=1, max_length=240)
    reference: str | None = Field(default=None, max_length=80)
    lines: list[JournalLineCreate] = Field(min_length=2)

    @model_validator(mode="after")
    def entry_balances(self) -> "JournalEntryCreate":
        total_debits = sum(line.debit for line in self.lines)
        total_credits = sum(line.credit for line in self.lines)
        if total_debits != total_credits:
            raise ValueError("Journal entry must balance: total debits must equal total credits.")
        return self


class JournalLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    account_code: str
    account_name: str
    debit: Decimal
    credit: Decimal
    description: str | None


class JournalEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entry_date: date
    memo: str
    reference: str | None
    created_at: datetime
    lines: list[JournalLineRead]


class DashboardSummary(BaseModel):
    cash_balance: Decimal
    receivables: Decimal
    payables: Decimal
    revenue: Decimal
    expenses: Decimal
    net_income: Decimal
    recent_entries: list[JournalEntryRead]

