from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .models import (
    AccountType,
    ContactType,
    CpfProfile,
    EmployeeStatus,
    PayrollStatus,
    PurchaseOrderStatus,
    ReceiptExtractionStatus,
    TransactionKind,
    TransactionStatus,
    VendorQualificationStatus,
)


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
    vendor_qualification_status: VendorQualificationStatus = VendorQualificationStatus.PENDING
    payment_terms: str | None = Field(default=None, max_length=80)
    default_expense_account_id: int | None = None
    qualification_notes: str | None = None
    qualification_expires_on: date | None = None
    notes: str | None = None


class ContactRead(ContactCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class EmployeeCreate(BaseModel):
    staff_id: str | None = Field(default=None, max_length=40)
    name: str = Field(min_length=1, max_length=160)
    email: str | None = Field(default=None, max_length=160)
    phone: str | None = Field(default=None, max_length=60)
    job_title: str | None = Field(default=None, max_length=120)
    status: EmployeeStatus = EmployeeStatus.ACTIVE
    start_date: date | None = None
    monthly_salary: Decimal
    cpf_profile: CpfProfile = CpfProfile.SC_OR_THIRD_YEAR_PR_55_BELOW
    employee_cpf_rate: Decimal = Decimal("0.20")
    employer_cpf_rate: Decimal = Decimal("0.17")
    notes: str | None = None

    @field_validator("monthly_salary")
    @classmethod
    def salary_must_be_positive(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("Monthly salary must be greater than zero.")
        return value.quantize(Decimal("0.01"))

    @field_validator("employee_cpf_rate", "employer_cpf_rate")
    @classmethod
    def employee_cpf_rates_are_percentages(cls, value: Decimal) -> Decimal:
        if value < 0 or value > 1:
            raise ValueError("CPF rates must be between 0 and 1.")
        return value.quantize(Decimal("0.0001"))

    @model_validator(mode="after")
    def cpf_profile_controls_rates(self) -> "EmployeeCreate":
        if self.cpf_profile == CpfProfile.NOT_APPLICABLE:
            self.employee_cpf_rate = Decimal("0.0000")
            self.employer_cpf_rate = Decimal("0.0000")
        if self.cpf_profile == CpfProfile.SC_OR_THIRD_YEAR_PR_55_BELOW:
            self.employee_cpf_rate = Decimal("0.2000")
            self.employer_cpf_rate = Decimal("0.1700")
        return self


class EmployeeRead(EmployeeCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class ReceiptPayload(BaseModel):
    filename: str = Field(min_length=1, max_length=240)
    content_type: str | None = Field(default=None, max_length=120)
    content_base64: str = Field(min_length=1)


class ReceiptLineItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    description: str
    quantity: Decimal | None
    unit_price: Decimal | None
    amount: Decimal | None
    confidence: Decimal | None


class ReceiptExtractionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    receipt_id: int
    status: ReceiptExtractionStatus
    provider: str
    model: str | None
    merchant_name: str | None
    receipt_date: date | None
    currency: str | None
    subtotal: Decimal | None
    tax: Decimal | None
    total: Decimal | None
    confidence: Decimal | None
    raw_text: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    line_items: list[ReceiptLineItemRead]


class ReceiptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    stored_path: str
    content_type: str | None
    size_bytes: int
    uploaded_at: datetime
    extraction: ReceiptExtractionRead | None = None


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


class PurchaseOrderLineCreate(BaseModel):
    description: str = Field(min_length=1, max_length=240)
    quantity: Decimal
    unit_price: Decimal
    tax_amount: Decimal = Decimal("0.00")
    expense_account_id: int

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("Quantity must be greater than zero.")
        return value.quantize(Decimal("0.001"))

    @field_validator("unit_price")
    @classmethod
    def unit_price_cannot_be_negative(cls, value: Decimal) -> Decimal:
        if value < 0:
            raise ValueError("Unit price cannot be negative.")
        return value.quantize(Decimal("0.01"))

    @field_validator("tax_amount")
    @classmethod
    def tax_amount_cannot_be_negative(cls, value: Decimal) -> Decimal:
        if value < 0:
            raise ValueError("Tax amount cannot be negative.")
        return value.quantize(Decimal("0.01"))


class PurchaseOrderCreate(BaseModel):
    po_number: str | None = Field(default=None, max_length=40)
    status: PurchaseOrderStatus = PurchaseOrderStatus.DRAFT
    vendor_id: int
    issue_date: date
    expected_delivery_date: date | None = None
    currency: str = Field(default="SGD", min_length=3, max_length=3)
    payment_terms: str | None = Field(default=None, max_length=120)
    notes: str | None = None
    delivery_instructions: str | None = None
    lines: list[PurchaseOrderLineCreate] = Field(min_length=1)

    @field_validator("currency")
    @classmethod
    def currency_uppercase(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def delivery_date_is_valid(self) -> "PurchaseOrderCreate":
        if self.expected_delivery_date and self.expected_delivery_date < self.issue_date:
            raise ValueError("Expected delivery date cannot be before issue date.")
        return self


class PurchaseOrderLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    description: str
    quantity: Decimal
    unit_price: Decimal
    tax_amount: Decimal
    line_total: Decimal
    expense_account: AccountRead


class PurchaseOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    po_number: str
    status: PurchaseOrderStatus
    vendor: ContactRead
    issue_date: date
    expected_delivery_date: date | None
    currency: str
    payment_terms: str | None
    notes: str | None
    delivery_instructions: str | None
    subtotal: Decimal
    tax_total: Decimal
    total: Decimal
    lines: list[PurchaseOrderLineRead]
    issued_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime


class PayrollRunCreate(BaseModel):
    status: PayrollStatus = PayrollStatus.DRAFT
    employee_id: int | None = None
    employee_name: str = Field(min_length=1, max_length=160)
    period_start: date
    period_end: date
    pay_date: date
    gross_salary: Decimal
    cpf_subject_wage: Decimal | None = None
    employee_cpf_rate: Decimal = Decimal("0.20")
    employer_cpf_rate: Decimal = Decimal("0.17")
    salary_account_id: int
    employer_cpf_account_id: int
    cash_account_id: int
    cpf_payable_account_id: int
    notes: str | None = None

    @field_validator("gross_salary")
    @classmethod
    def gross_salary_must_be_positive(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("Gross salary must be greater than zero.")
        return value.quantize(Decimal("0.01"))

    @field_validator("cpf_subject_wage")
    @classmethod
    def cpf_subject_wage_cannot_be_negative(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return value
        if value < 0:
            raise ValueError("CPF subject wage cannot be negative.")
        return value.quantize(Decimal("0.01"))

    @field_validator("employee_cpf_rate", "employer_cpf_rate")
    @classmethod
    def cpf_rates_are_percentages(cls, value: Decimal) -> Decimal:
        if value < 0 or value > 1:
            raise ValueError("CPF rates must be between 0 and 1.")
        return value.quantize(Decimal("0.0001"))

    @model_validator(mode="after")
    def period_is_valid(self) -> "PayrollRunCreate":
        if self.period_end < self.period_start:
            raise ValueError("Payroll period end cannot be before period start.")
        return self


class PayrollRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: PayrollStatus
    employee: EmployeeRead | None
    employee_name: str
    period_start: date
    period_end: date
    pay_date: date
    gross_salary: Decimal
    cpf_subject_wage: Decimal
    employee_cpf_rate: Decimal
    employer_cpf_rate: Decimal
    employee_cpf: Decimal
    employer_cpf: Decimal
    net_pay: Decimal
    salary_account: AccountRead
    employer_cpf_account: AccountRead
    cash_account: AccountRead
    cpf_payable_account: AccountRead
    notes: str | None
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
