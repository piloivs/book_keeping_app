from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class AccountType(StrEnum):
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    REVENUE = "revenue"
    EXPENSE = "expense"


class ContactType(StrEnum):
    CUSTOMER = "customer"
    VENDOR = "vendor"
    BOTH = "both"


class VendorQualificationStatus(StrEnum):
    PENDING = "pending"
    QUALIFIED = "qualified"
    SUSPENDED = "suspended"
    REJECTED = "rejected"


class TransactionKind(StrEnum):
    EXPENSE = "expense"
    INCOME = "income"


class TransactionStatus(StrEnum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    POSTED = "posted"


class PayrollStatus(StrEnum):
    DRAFT = "draft"
    POSTED = "posted"


class PurchaseOrderStatus(StrEnum):
    DRAFT = "draft"
    ISSUED = "issued"
    PARTIALLY_RECEIVED = "partially_received"
    RECEIVED = "received"
    BILLED = "billed"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class ReceiptExtractionStatus(StrEnum):
    NOT_CONFIGURED = "not_configured"
    COMPLETED = "completed"
    FAILED = "failed"


class EmployeeStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class CpfProfile(StrEnum):
    SC_OR_THIRD_YEAR_PR_55_BELOW = "sc_or_third_year_pr_55_below"
    CUSTOM = "custom"
    NOT_APPLICABLE = "not_applicable"


class CompanySettings(Base):
    __tablename__ = "company_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_name: Mapped[str] = mapped_column(String(160), default="IntelliArtAI")
    registration_number: Mapped[str | None] = mapped_column(String(40), default=None)
    fiscal_year_start_month: Mapped[int] = mapped_column(default=1)
    base_currency: Mapped[str] = mapped_column(String(3), default="SGD")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    type: Mapped[ContactType] = mapped_column(Enum(ContactType), index=True)
    email: Mapped[str | None] = mapped_column(String(160), default=None)
    phone: Mapped[str | None] = mapped_column(String(60), default=None)
    tax_identifier: Mapped[str | None] = mapped_column(String(80), default=None)
    vendor_qualification_status: Mapped[VendorQualificationStatus] = mapped_column(
        Enum(VendorQualificationStatus),
        default=VendorQualificationStatus.PENDING,
        index=True,
    )
    payment_terms: Mapped[str | None] = mapped_column(String(80), default=None)
    default_expense_account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), default=None)
    qualification_notes: Mapped[str | None] = mapped_column(Text, default=None)
    qualification_expires_on: Mapped[date | None] = mapped_column(Date, default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    transactions: Mapped[list["OperationalTransaction"]] = relationship(back_populates="contact")
    default_expense_account: Mapped["Account | None"] = relationship(foreign_keys=[default_expense_account_id])
    purchase_orders: Mapped[list["PurchaseOrder"]] = relationship(back_populates="vendor")


class Receipt(Base):
    __tablename__ = "receipts"

    id: Mapped[int] = mapped_column(primary_key=True)
    original_filename: Mapped[str] = mapped_column(String(240))
    stored_path: Mapped[str] = mapped_column(String(320))
    content_type: Mapped[str | None] = mapped_column(String(120), default=None)
    size_bytes: Mapped[int] = mapped_column(default=0)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    transaction: Mapped["OperationalTransaction | None"] = relationship(back_populates="receipt")
    extraction: Mapped["ReceiptExtraction | None"] = relationship(
        back_populates="receipt",
        cascade="all, delete-orphan",
    )


class ReceiptExtraction(Base):
    __tablename__ = "receipt_extractions"

    id: Mapped[int] = mapped_column(primary_key=True)
    receipt_id: Mapped[int] = mapped_column(ForeignKey("receipts.id"), unique=True, index=True)
    status: Mapped[ReceiptExtractionStatus] = mapped_column(Enum(ReceiptExtractionStatus), index=True)
    provider: Mapped[str] = mapped_column(String(40), default="openai")
    model: Mapped[str | None] = mapped_column(String(80), default=None)
    merchant_name: Mapped[str | None] = mapped_column(String(180), default=None)
    receipt_date: Mapped[date | None] = mapped_column(Date, default=None)
    currency: Mapped[str | None] = mapped_column(String(3), default=None)
    subtotal: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=None)
    tax: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=None)
    total: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=None)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), default=None)
    raw_text: Mapped[str | None] = mapped_column(Text, default=None)
    error_message: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    receipt: Mapped[Receipt] = relationship(back_populates="extraction")
    line_items: Mapped[list["ReceiptLineItem"]] = relationship(
        back_populates="extraction",
        cascade="all, delete-orphan",
        order_by="ReceiptLineItem.id",
    )


class ReceiptLineItem(Base):
    __tablename__ = "receipt_line_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    extraction_id: Mapped[int] = mapped_column(ForeignKey("receipt_extractions.id"), index=True)
    description: Mapped[str] = mapped_column(String(240))
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), default=None)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=None)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), default=None)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), default=None)

    extraction: Mapped[ReceiptExtraction] = relationship(back_populates="line_items")


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    staff_id: Mapped[str | None] = mapped_column(String(40), unique=True, default=None)
    name: Mapped[str] = mapped_column(String(160), index=True)
    email: Mapped[str | None] = mapped_column(String(160), default=None)
    phone: Mapped[str | None] = mapped_column(String(60), default=None)
    job_title: Mapped[str | None] = mapped_column(String(120), default=None)
    status: Mapped[EmployeeStatus] = mapped_column(Enum(EmployeeStatus), default=EmployeeStatus.ACTIVE, index=True)
    start_date: Mapped[date | None] = mapped_column(Date, default=None)
    monthly_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    cpf_profile: Mapped[CpfProfile] = mapped_column(
        Enum(CpfProfile),
        default=CpfProfile.SC_OR_THIRD_YEAR_PR_55_BELOW,
        index=True,
    )
    employee_cpf_rate: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=Decimal("0.2000"))
    employer_cpf_rate: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=Decimal("0.1700"))
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    payroll_runs: Mapped[list["PayrollRun"]] = relationship(back_populates="employee")


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    type: Mapped[AccountType] = mapped_column(Enum(AccountType))
    description: Mapped[str | None] = mapped_column(Text, default=None)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lines: Mapped[list["JournalLine"]] = relationship(back_populates="account")


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_date: Mapped[date] = mapped_column(Date, index=True)
    memo: Mapped[str] = mapped_column(String(240))
    reference: Mapped[str | None] = mapped_column(String(80), default=None, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lines: Mapped[list["JournalLine"]] = relationship(
        back_populates="entry",
        cascade="all, delete-orphan",
        order_by="JournalLine.id",
    )
    operational_transaction: Mapped["OperationalTransaction | None"] = relationship(back_populates="journal_entry")
    payroll_run: Mapped["PayrollRun | None"] = relationship(back_populates="journal_entry")


class JournalLine(Base):
    __tablename__ = "journal_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    journal_entry_id: Mapped[int] = mapped_column(ForeignKey("journal_entries.id"))
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    debit: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    credit: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    description: Mapped[str | None] = mapped_column(String(180), default=None)

    entry: Mapped[JournalEntry] = relationship(back_populates="lines")
    account: Mapped[Account] = relationship(back_populates="lines")


class OperationalTransaction(Base):
    __tablename__ = "operational_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[TransactionKind] = mapped_column(Enum(TransactionKind), index=True)
    status: Mapped[TransactionStatus] = mapped_column(Enum(TransactionStatus), default=TransactionStatus.DRAFT, index=True)
    transaction_date: Mapped[date] = mapped_column(Date, index=True)
    description: Mapped[str] = mapped_column(String(240))
    reference: Mapped[str | None] = mapped_column(String(80), default=None, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    contact_id: Mapped[int | None] = mapped_column(ForeignKey("contacts.id"), default=None)
    debit_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    credit_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    receipt_id: Mapped[int | None] = mapped_column(ForeignKey("receipts.id"), default=None, unique=True)
    journal_entry_id: Mapped[int | None] = mapped_column(ForeignKey("journal_entries.id"), default=None, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    contact: Mapped[Contact | None] = relationship(back_populates="transactions")
    debit_account: Mapped[Account] = relationship(foreign_keys=[debit_account_id])
    credit_account: Mapped[Account] = relationship(foreign_keys=[credit_account_id])
    receipt: Mapped[Receipt | None] = relationship(back_populates="transaction")
    journal_entry: Mapped[JournalEntry | None] = relationship(back_populates="operational_transaction")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    po_number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    status: Mapped[PurchaseOrderStatus] = mapped_column(
        Enum(PurchaseOrderStatus),
        default=PurchaseOrderStatus.DRAFT,
        index=True,
    )
    vendor_id: Mapped[int] = mapped_column(ForeignKey("contacts.id"), index=True)
    issue_date: Mapped[date] = mapped_column(Date, index=True)
    expected_delivery_date: Mapped[date | None] = mapped_column(Date, default=None)
    currency: Mapped[str] = mapped_column(String(3), default="SGD")
    payment_terms: Mapped[str | None] = mapped_column(String(120), default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    delivery_instructions: Mapped[str | None] = mapped_column(Text, default=None)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    vendor: Mapped[Contact] = relationship(back_populates="purchase_orders")
    lines: Mapped[list["PurchaseOrderLine"]] = relationship(
        back_populates="purchase_order",
        cascade="all, delete-orphan",
        order_by="PurchaseOrderLine.id",
    )

    @property
    def subtotal(self) -> Decimal:
        return sum((line.quantity * line.unit_price for line in self.lines), Decimal("0.00")).quantize(Decimal("0.01"))

    @property
    def tax_total(self) -> Decimal:
        return sum((line.tax_amount for line in self.lines), Decimal("0.00")).quantize(Decimal("0.01"))

    @property
    def total(self) -> Decimal:
        return (self.subtotal + self.tax_total).quantize(Decimal("0.01"))


class PurchaseOrderLine(Base):
    __tablename__ = "purchase_order_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    purchase_order_id: Mapped[int] = mapped_column(ForeignKey("purchase_orders.id"), index=True)
    description: Mapped[str] = mapped_column(String(240))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    expense_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))

    purchase_order: Mapped[PurchaseOrder] = relationship(back_populates="lines")
    expense_account: Mapped[Account] = relationship(foreign_keys=[expense_account_id])

    @property
    def line_total(self) -> Decimal:
        return (self.quantity * self.unit_price + self.tax_amount).quantize(Decimal("0.01"))


class PayrollRun(Base):
    __tablename__ = "payroll_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[PayrollStatus] = mapped_column(Enum(PayrollStatus), default=PayrollStatus.DRAFT, index=True)
    employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), default=None)
    employee_name: Mapped[str] = mapped_column(String(160), index=True)
    period_start: Mapped[date] = mapped_column(Date, index=True)
    period_end: Mapped[date] = mapped_column(Date, index=True)
    pay_date: Mapped[date] = mapped_column(Date, index=True)
    gross_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    cpf_subject_wage: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    employee_cpf_rate: Mapped[Decimal] = mapped_column(Numeric(6, 4))
    employer_cpf_rate: Mapped[Decimal] = mapped_column(Numeric(6, 4))
    employee_cpf: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    employer_cpf: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    net_pay: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    salary_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    employer_cpf_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    cash_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    cpf_payable_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    journal_entry_id: Mapped[int | None] = mapped_column(ForeignKey("journal_entries.id"), default=None, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    employee: Mapped[Employee | None] = relationship(back_populates="payroll_runs")
    salary_account: Mapped[Account] = relationship(foreign_keys=[salary_account_id])
    employer_cpf_account: Mapped[Account] = relationship(foreign_keys=[employer_cpf_account_id])
    cash_account: Mapped[Account] = relationship(foreign_keys=[cash_account_id])
    cpf_payable_account: Mapped[Account] = relationship(foreign_keys=[cpf_payable_account_id])
    journal_entry: Mapped[JournalEntry | None] = relationship(back_populates="payroll_run")
