from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .models import AccountType, ContactType, TransactionKind, TransactionStatus


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


class CompanySettingsUpdate(BaseModel):
    company_name: str = Field(min_length=1, max_length=160)
    registration_number: str | None = Field(default=None, max_length=40)
    fiscal_year_start_month: int = Field(ge=1, le=12)
    base_currency: str = Field(min_length=3, max_length=3)

    @field_validator("base_currency")
    @classmethod
    def currency_uppercase(cls, value: str) -> str:
        return value.upper()


class CompanySettingsRead(CompanySettingsUpdate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    updated_at: datetime


class ContactCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    type: ContactType
    email: str | None = Field(default=None, max_length=160)
    phone: str | None = Field(default=None, max_length=60)
    tax_identifier: str | None = Field(default=None, max_length=80)
    notes: str | None = None


class ContactRead(ContactCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class ReceiptPayload(BaseModel):
    filename: str = Field(min_length=1, max_length=240)
    content_type: str | None = Field(default=None, max_length=120)
    content_base64: str = Field(min_length=1)


class ReceiptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    stored_path: str
    content_type: str | None
    size_bytes: int
    uploaded_at: datetime


class OperationalTransactionCreate(BaseModel):
    kind: TransactionKind
    status: TransactionStatus = TransactionStatus.DRAFT
    transaction_date: date
    description: str = Field(min_length=1, max_length=240)
    reference: str | None = Field(default=None, max_length=80)
    amount: Decimal
    contact_id: int | None = None
    debit_account_id: int
    credit_account_id: int
    receipt: ReceiptPayload | None = None

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("Amount must be greater than zero.")
        return value.quantize(Decimal("0.01"))


class OperationalTransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: TransactionKind
    status: TransactionStatus
    transaction_date: date
    description: str
    reference: str | None
    amount: Decimal
    contact: ContactRead | None
    debit_account: AccountRead
    credit_account: AccountRead
    receipt: ReceiptRead | None
    journal_entry_id: int | None
    created_at: datetime
    posted_at: datetime | None


class ProfitAndLossReport(BaseModel):
    revenue: Decimal
    expenses: Decimal
    net_income: Decimal
    revenue_accounts: list[AccountRead]
    expense_accounts: list[AccountRead]


class BalanceSheetReport(BaseModel):
    assets: Decimal
    liabilities: Decimal
    equity: Decimal
    retained_earnings: Decimal
    total_liabilities_and_equity: Decimal
    asset_accounts: list[AccountRead]
    liability_accounts: list[AccountRead]
    equity_accounts: list[AccountRead]
