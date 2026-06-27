from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String, Text, event, func, inspect
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

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
    DEPOSIT = "deposit"


class TransactionStatus(StrEnum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    POSTED = "posted"


class ProjectStatus(StrEnum):
    PLANNED = "planned"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ServiceType(StrEnum):
    AI_AUTOMATION = "ai_automation"
    CONSULTING = "consulting"
    IMPLEMENTATION = "implementation"
    SUPPORT = "support"
    TRAINING = "training"
    OTHER = "other"


class BillingModel(StrEnum):
    FIXED_FEE = "fixed_fee"
    MILESTONE = "milestone"
    RETAINER = "retainer"
    TIME_AND_MATERIALS = "time_and_materials"
    SUBSCRIPTION = "subscription"
    OTHER = "other"


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


class SupplierBillStatus(StrEnum):
    DRAFT = "draft"
    POSTED = "posted"
    VOIDED = "voided"


class SupplierPaymentStatus(StrEnum):
    DRAFT = "draft"
    POSTED = "posted"
    VOIDED = "voided"


class BankStatementLineStatus(StrEnum):
    UNMATCHED = "unmatched"
    RECONCILED = "reconciled"
    IGNORED = "ignored"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class SalesOrderStatus(StrEnum):
    DRAFT = "draft"
    RECEIVED = "received"
    ACCEPTED = "accepted"
    PARTIALLY_INVOICED = "partially_invoiced"
    FULFILLED = "fulfilled"
    INVOICED = "invoiced"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class DepositStatus(StrEnum):
    NOT_REQUESTED = "not_requested"
    REQUESTED = "requested"
    INVOICED = "invoiced"
    PAID = "paid"
    APPLIED = "applied"


class SalesInvoiceStatus(StrEnum):
    DRAFT = "draft"
    ISSUED = "issued"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    VOIDED = "voided"


class CustomerReceiptStatus(StrEnum):
    DRAFT = "draft"
    POSTED = "posted"
    VOIDED = "voided"


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
    supplier_bills: Mapped[list["SupplierBill"]] = relationship(back_populates="vendor")
    supplier_payments: Mapped[list["SupplierPayment"]] = relationship(back_populates="vendor")
    sales_orders: Mapped[list["SalesOrder"]] = relationship(back_populates="customer")
    sales_invoices: Mapped[list["SalesInvoice"]] = relationship(back_populates="customer")
    customer_receipts: Mapped[list["CustomerReceipt"]] = relationship(back_populates="customer")
    projects: Mapped[list["Project"]] = relationship(back_populates="client")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("contacts.id"), index=True)
    status: Mapped[ProjectStatus] = mapped_column(Enum(ProjectStatus), default=ProjectStatus.ACTIVE, index=True)
    service_type: Mapped[ServiceType] = mapped_column(Enum(ServiceType), default=ServiceType.AI_AUTOMATION, index=True)
    billing_model: Mapped[BillingModel] = mapped_column(Enum(BillingModel), default=BillingModel.FIXED_FEE, index=True)
    contract_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    start_date: Mapped[date | None] = mapped_column(Date, default=None)
    end_date: Mapped[date | None] = mapped_column(Date, default=None)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    client: Mapped[Contact] = relationship(back_populates="projects")
    transactions: Mapped[list["OperationalTransaction"]] = relationship(back_populates="project")
    sales_orders: Mapped[list["SalesOrder"]] = relationship(back_populates="project")
    sales_invoices: Mapped[list["SalesInvoice"]] = relationship(back_populates="project")
    supplier_bills: Mapped[list["SupplierBill"]] = relationship(back_populates="project")


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
    bank_statement_lines: Mapped[list["BankStatementLine"]] = relationship(back_populates="bank_account")


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
    sales_invoice: Mapped["SalesInvoice | None"] = relationship(back_populates="journal_entry")
    customer_receipt: Mapped["CustomerReceipt | None"] = relationship(back_populates="journal_entry")
    supplier_bill: Mapped["SupplierBill | None"] = relationship(back_populates="journal_entry")
    supplier_payment: Mapped["SupplierPayment | None"] = relationship(back_populates="journal_entry")
    bank_statement_line: Mapped["BankStatementLine | None"] = relationship(back_populates="journal_entry")


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


class BankStatementLine(Base):
    __tablename__ = "bank_statement_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    bank_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    statement_date: Mapped[date] = mapped_column(Date, index=True)
    description: Mapped[str] = mapped_column(String(240))
    reference: Mapped[str | None] = mapped_column(String(80), default=None, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[BankStatementLineStatus] = mapped_column(
        Enum(BankStatementLineStatus),
        default=BankStatementLineStatus.UNMATCHED,
        index=True,
    )
    journal_entry_id: Mapped[int | None] = mapped_column(ForeignKey("journal_entries.id"), default=None, unique=True)
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    bank_account: Mapped[Account] = relationship(back_populates="bank_statement_lines")
    journal_entry: Mapped[JournalEntry | None] = relationship(back_populates="bank_statement_line")


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_type: Mapped[str] = mapped_column(String(80), index=True)
    document_id: Mapped[int] = mapped_column(index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[ApprovalStatus] = mapped_column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING, index=True)
    requested_by: Mapped[str | None] = mapped_column(String(120), default=None)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    decided_by: Mapped[str | None] = mapped_column(String(120), default=None)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    reason: Mapped[str | None] = mapped_column(Text, default=None)
    decision_notes: Mapped[str | None] = mapped_column(Text, default=None)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(80), index=True)
    entity_id: Mapped[int | None] = mapped_column(index=True, default=None)
    action: Mapped[str] = mapped_column(String(80), index=True)
    actor: Mapped[str | None] = mapped_column(String(120), default=None)
    summary: Mapped[str] = mapped_column(String(240))
    details_json: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


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
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), default=None, index=True)
    debit_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    credit_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    receipt_id: Mapped[int | None] = mapped_column(ForeignKey("receipts.id"), default=None, unique=True)
    journal_entry_id: Mapped[int | None] = mapped_column(ForeignKey("journal_entries.id"), default=None, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    contact: Mapped[Contact | None] = relationship(back_populates="transactions")
    project: Mapped[Project | None] = relationship(back_populates="transactions")
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
    supplier_bills: Mapped[list["SupplierBill"]] = relationship(back_populates="purchase_order")
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


class SupplierBill(Base):
    __tablename__ = "supplier_bills"

    id: Mapped[int] = mapped_column(primary_key=True)
    bill_number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    status: Mapped[SupplierBillStatus] = mapped_column(
        Enum(SupplierBillStatus),
        default=SupplierBillStatus.DRAFT,
        index=True,
    )
    vendor_id: Mapped[int] = mapped_column(ForeignKey("contacts.id"), index=True)
    purchase_order_id: Mapped[int | None] = mapped_column(ForeignKey("purchase_orders.id"), default=None, index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), default=None, index=True)
    bill_date: Mapped[date] = mapped_column(Date, index=True)
    due_date: Mapped[date] = mapped_column(Date, index=True)
    currency: Mapped[str] = mapped_column(String(3), default="SGD")
    payment_terms: Mapped[str | None] = mapped_column(String(120), default=None)
    reference: Mapped[str | None] = mapped_column(String(80), default=None, index=True)
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    journal_entry_id: Mapped[int | None] = mapped_column(ForeignKey("journal_entries.id"), default=None, unique=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    vendor: Mapped[Contact] = relationship(back_populates="supplier_bills")
    purchase_order: Mapped[PurchaseOrder | None] = relationship(back_populates="supplier_bills")
    project: Mapped[Project | None] = relationship(back_populates="supplier_bills")
    journal_entry: Mapped[JournalEntry | None] = relationship(back_populates="supplier_bill")
    lines: Mapped[list["SupplierBillLine"]] = relationship(
        back_populates="bill",
        cascade="all, delete-orphan",
        order_by="SupplierBillLine.id",
    )
    allocations: Mapped[list["SupplierPaymentAllocation"]] = relationship(back_populates="bill")

    @property
    def subtotal(self) -> Decimal:
        return sum((line.quantity * line.unit_price for line in self.lines), Decimal("0.00")).quantize(Decimal("0.01"))

    @property
    def tax_total(self) -> Decimal:
        return sum((line.tax_amount for line in self.lines), Decimal("0.00")).quantize(Decimal("0.01"))

    @property
    def total(self) -> Decimal:
        return (self.subtotal + self.tax_total).quantize(Decimal("0.01"))

    @property
    def amount_paid(self) -> Decimal:
        return sum(
            (
                allocation.amount
                for allocation in self.allocations
                if allocation.payment and allocation.payment.status == SupplierPaymentStatus.POSTED
            ),
            Decimal("0.00"),
        ).quantize(Decimal("0.01"))

    @property
    def amount_due(self) -> Decimal:
        return max(self.total - self.amount_paid, Decimal("0.00")).quantize(Decimal("0.01"))


class SupplierBillLine(Base):
    __tablename__ = "supplier_bill_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    bill_id: Mapped[int] = mapped_column(ForeignKey("supplier_bills.id"), index=True)
    description: Mapped[str] = mapped_column(String(240))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    expense_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))

    bill: Mapped[SupplierBill] = relationship(back_populates="lines")
    expense_account: Mapped[Account] = relationship(foreign_keys=[expense_account_id])

    @property
    def line_subtotal(self) -> Decimal:
        return (self.quantity * self.unit_price).quantize(Decimal("0.01"))

    @property
    def line_total(self) -> Decimal:
        return (self.line_subtotal + self.tax_amount).quantize(Decimal("0.01"))


class SupplierPayment(Base):
    __tablename__ = "supplier_payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    payment_number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    status: Mapped[SupplierPaymentStatus] = mapped_column(
        Enum(SupplierPaymentStatus),
        default=SupplierPaymentStatus.POSTED,
        index=True,
    )
    vendor_id: Mapped[int] = mapped_column(ForeignKey("contacts.id"), index=True)
    payment_date: Mapped[date] = mapped_column(Date, index=True)
    currency: Mapped[str] = mapped_column(String(3), default="SGD")
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    bank_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    reference: Mapped[str | None] = mapped_column(String(80), default=None, index=True)
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    journal_entry_id: Mapped[int | None] = mapped_column(ForeignKey("journal_entries.id"), default=None, unique=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    vendor: Mapped[Contact] = relationship(back_populates="supplier_payments")
    bank_account: Mapped[Account] = relationship(foreign_keys=[bank_account_id])
    journal_entry: Mapped[JournalEntry | None] = relationship(back_populates="supplier_payment")
    allocations: Mapped[list["SupplierPaymentAllocation"]] = relationship(
        back_populates="payment",
        cascade="all, delete-orphan",
        order_by="SupplierPaymentAllocation.id",
    )


class SupplierPaymentAllocation(Base):
    __tablename__ = "supplier_payment_allocations"

    id: Mapped[int] = mapped_column(primary_key=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("supplier_payments.id"), index=True)
    bill_id: Mapped[int] = mapped_column(ForeignKey("supplier_bills.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    payment: Mapped[SupplierPayment] = relationship(back_populates="allocations")
    bill: Mapped[SupplierBill] = relationship(back_populates="allocations")


class SalesOrder(Base):
    __tablename__ = "sales_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    client_po_number: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[SalesOrderStatus] = mapped_column(
        Enum(SalesOrderStatus),
        default=SalesOrderStatus.RECEIVED,
        index=True,
    )
    customer_id: Mapped[int] = mapped_column(ForeignKey("contacts.id"), index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), default=None, index=True)
    received_date: Mapped[date] = mapped_column(Date, index=True)
    expected_delivery_date: Mapped[date | None] = mapped_column(Date, default=None)
    currency: Mapped[str] = mapped_column(String(3), default="SGD")
    payment_terms: Mapped[str | None] = mapped_column(String(120), default=None)
    deposit_required: Mapped[bool] = mapped_column(default=False)
    deposit_rate: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=Decimal("0.0000"))
    deposit_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    deposit_due_date: Mapped[date | None] = mapped_column(Date, default=None)
    deposit_status: Mapped[DepositStatus] = mapped_column(
        Enum(DepositStatus),
        default=DepositStatus.NOT_REQUESTED,
        index=True,
    )
    deposit_transaction_id: Mapped[int | None] = mapped_column(ForeignKey("operational_transactions.id"), default=None, unique=True)
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    delivery_instructions: Mapped[str | None] = mapped_column(Text, default=None)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    customer: Mapped[Contact] = relationship(back_populates="sales_orders")
    project: Mapped[Project | None] = relationship(back_populates="sales_orders")
    deposit_transaction: Mapped[OperationalTransaction | None] = relationship(foreign_keys=[deposit_transaction_id])
    invoices: Mapped[list["SalesInvoice"]] = relationship(back_populates="sales_order")
    lines: Mapped[list["SalesOrderLine"]] = relationship(
        back_populates="sales_order",
        cascade="all, delete-orphan",
        order_by="SalesOrderLine.id",
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

    @property
    def invoiced_total(self) -> Decimal:
        return sum(
            (
                invoice.total
                for invoice in self.invoices
                if invoice.status not in {SalesInvoiceStatus.DRAFT, SalesInvoiceStatus.VOIDED}
            ),
            Decimal("0.00"),
        ).quantize(Decimal("0.01"))

    @property
    def paid_total(self) -> Decimal:
        return sum(
            (
                invoice.amount_paid
                for invoice in self.invoices
                if invoice.status not in {SalesInvoiceStatus.DRAFT, SalesInvoiceStatus.VOIDED}
            ),
            Decimal("0.00"),
        ).quantize(Decimal("0.01"))

    @property
    def unbilled_total(self) -> Decimal:
        return max(self.total - self.invoiced_total, Decimal("0.00")).quantize(Decimal("0.01"))


class SalesOrderLine(Base):
    __tablename__ = "sales_order_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    sales_order_id: Mapped[int] = mapped_column(ForeignKey("sales_orders.id"), index=True)
    description: Mapped[str] = mapped_column(String(240))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    revenue_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))

    sales_order: Mapped[SalesOrder] = relationship(back_populates="lines")
    revenue_account: Mapped[Account] = relationship(foreign_keys=[revenue_account_id])

    @property
    def line_total(self) -> Decimal:
        return (self.quantity * self.unit_price + self.tax_amount).quantize(Decimal("0.01"))


class SalesInvoice(Base):
    __tablename__ = "sales_invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    status: Mapped[SalesInvoiceStatus] = mapped_column(
        Enum(SalesInvoiceStatus),
        default=SalesInvoiceStatus.DRAFT,
        index=True,
    )
    customer_id: Mapped[int] = mapped_column(ForeignKey("contacts.id"), index=True)
    sales_order_id: Mapped[int | None] = mapped_column(ForeignKey("sales_orders.id"), default=None, index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), default=None, index=True)
    issue_date: Mapped[date] = mapped_column(Date, index=True)
    due_date: Mapped[date] = mapped_column(Date, index=True)
    currency: Mapped[str] = mapped_column(String(3), default="SGD")
    payment_terms: Mapped[str | None] = mapped_column(String(120), default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    journal_entry_id: Mapped[int | None] = mapped_column(ForeignKey("journal_entries.id"), default=None, unique=True)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    customer: Mapped[Contact] = relationship(back_populates="sales_invoices")
    sales_order: Mapped[SalesOrder | None] = relationship(back_populates="invoices")
    project: Mapped[Project | None] = relationship(back_populates="sales_invoices")
    journal_entry: Mapped[JournalEntry | None] = relationship(back_populates="sales_invoice")
    lines: Mapped[list["SalesInvoiceLine"]] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="SalesInvoiceLine.id",
    )
    allocations: Mapped[list["CustomerReceiptAllocation"]] = relationship(back_populates="invoice")

    @property
    def subtotal(self) -> Decimal:
        return sum((line.quantity * line.unit_price for line in self.lines), Decimal("0.00")).quantize(Decimal("0.01"))

    @property
    def tax_total(self) -> Decimal:
        return sum((line.tax_amount for line in self.lines), Decimal("0.00")).quantize(Decimal("0.01"))

    @property
    def total(self) -> Decimal:
        return (self.subtotal + self.tax_total).quantize(Decimal("0.01"))

    @property
    def amount_paid(self) -> Decimal:
        return sum(
            (
                allocation.amount
                for allocation in self.allocations
                if allocation.receipt and allocation.receipt.status == CustomerReceiptStatus.POSTED
            ),
            Decimal("0.00"),
        ).quantize(Decimal("0.01"))

    @property
    def amount_due(self) -> Decimal:
        return max(self.total - self.amount_paid, Decimal("0.00")).quantize(Decimal("0.01"))


class SalesInvoiceLine(Base):
    __tablename__ = "sales_invoice_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("sales_invoices.id"), index=True)
    description: Mapped[str] = mapped_column(String(240))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    revenue_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))

    invoice: Mapped[SalesInvoice] = relationship(back_populates="lines")
    revenue_account: Mapped[Account] = relationship(foreign_keys=[revenue_account_id])

    @property
    def line_total(self) -> Decimal:
        return (self.quantity * self.unit_price + self.tax_amount).quantize(Decimal("0.01"))


class CustomerReceipt(Base):
    __tablename__ = "customer_receipts"

    id: Mapped[int] = mapped_column(primary_key=True)
    receipt_number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    status: Mapped[CustomerReceiptStatus] = mapped_column(
        Enum(CustomerReceiptStatus),
        default=CustomerReceiptStatus.POSTED,
        index=True,
    )
    customer_id: Mapped[int] = mapped_column(ForeignKey("contacts.id"), index=True)
    receipt_date: Mapped[date] = mapped_column(Date, index=True)
    currency: Mapped[str] = mapped_column(String(3), default="SGD")
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    bank_account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    reference: Mapped[str | None] = mapped_column(String(80), default=None, index=True)
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    journal_entry_id: Mapped[int | None] = mapped_column(ForeignKey("journal_entries.id"), default=None, unique=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    customer: Mapped[Contact] = relationship(back_populates="customer_receipts")
    bank_account: Mapped[Account] = relationship(foreign_keys=[bank_account_id])
    journal_entry: Mapped[JournalEntry | None] = relationship(back_populates="customer_receipt")
    allocations: Mapped[list["CustomerReceiptAllocation"]] = relationship(
        back_populates="receipt",
        cascade="all, delete-orphan",
        order_by="CustomerReceiptAllocation.id",
    )


class CustomerReceiptAllocation(Base):
    __tablename__ = "customer_receipt_allocations"

    id: Mapped[int] = mapped_column(primary_key=True)
    receipt_id: Mapped[int] = mapped_column(ForeignKey("customer_receipts.id"), index=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("sales_invoices.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    receipt: Mapped[CustomerReceipt] = relationship(back_populates="allocations")
    invoice: Mapped[SalesInvoice] = relationship(back_populates="allocations")


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


def _has_column_changes(obj: object, column_names: set[str]) -> bool:
    state = inspect(obj)
    return any(state.attrs[name].history.has_changes() for name in column_names)


def _was_posted(obj: object, posted_status: StrEnum) -> bool:
    state = inspect(obj)
    history = state.attrs.status.history
    if history.deleted:
        return history.deleted[0] == posted_status
    return getattr(obj, "status") == posted_status


@event.listens_for(Session, "before_flush")
def protect_posted_accounting_records(session: Session, _flush_context, _instances) -> None:
    for obj in session.deleted:
        if isinstance(obj, (JournalEntry, JournalLine)):
            raise ValueError("Posted journal entries and lines cannot be deleted; create a reversal instead.")

    for obj in session.new:
        if isinstance(obj, JournalLine) and obj.entry is not None and obj.entry not in session.new:
            raise ValueError("Posted journal entries cannot receive new lines; create a reversal instead.")
        if isinstance(obj, SalesInvoiceLine) and obj.invoice is not None and obj.invoice.journal_entry_id is not None:
            raise ValueError("Posted sales invoice lines cannot be changed; create an adjustment or reversal instead.")
        if isinstance(obj, CustomerReceiptAllocation) and obj.receipt is not None and obj.receipt.journal_entry_id is not None:
            raise ValueError("Posted receipt allocations cannot be changed; create a reversal or adjustment instead.")
        if isinstance(obj, SupplierBillLine) and obj.bill is not None and obj.bill.journal_entry_id is not None:
            raise ValueError("Posted supplier bill lines cannot be changed; create an adjustment or reversal instead.")
        if isinstance(obj, SupplierPaymentAllocation) and obj.payment is not None and obj.payment.journal_entry_id is not None:
            raise ValueError("Posted supplier payment allocations cannot be changed; create a reversal or adjustment instead.")

    for obj in session.dirty:
        if not inspect(obj).persistent:
            continue
        if getattr(obj, "_allow_accounting_post_mutation", False):
            delattr(obj, "_allow_accounting_post_mutation")
            continue
        if isinstance(obj, JournalEntry) and _has_column_changes(obj, {"entry_date", "memo", "reference"}):
            raise ValueError("Posted journal entries are immutable; create a reversal instead.")
        if isinstance(obj, JournalLine) and _has_column_changes(obj, {"account_id", "debit", "credit", "description"}):
            raise ValueError("Posted journal lines are immutable; create a reversal instead.")
        if isinstance(obj, OperationalTransaction) and _was_posted(obj, TransactionStatus.POSTED):
            protected = {
                "kind",
                "transaction_date",
                "description",
                "reference",
                "amount",
                "contact_id",
                "project_id",
                "debit_account_id",
                "credit_account_id",
                "receipt_id",
                "journal_entry_id",
                "posted_at",
            }
            if _has_column_changes(obj, protected):
                raise ValueError("Posted operational transactions are immutable; create a reversal or adjustment instead.")
        if isinstance(obj, PayrollRun) and _was_posted(obj, PayrollStatus.POSTED):
            protected = {
                "employee_id",
                "employee_name",
                "period_start",
                "period_end",
                "pay_date",
                "gross_salary",
                "cpf_subject_wage",
                "employee_cpf_rate",
                "employer_cpf_rate",
                "employee_cpf",
                "employer_cpf",
                "net_pay",
                "salary_account_id",
                "employer_cpf_account_id",
                "cash_account_id",
                "cpf_payable_account_id",
                "journal_entry_id",
                "posted_at",
            }
            if _has_column_changes(obj, protected):
                raise ValueError("Posted payroll runs are immutable; create an adjustment instead.")
        if isinstance(obj, SalesInvoiceLine) and obj.invoice is not None and obj.invoice.journal_entry_id is not None:
            if _has_column_changes(obj, {"description", "quantity", "unit_price", "tax_amount", "revenue_account_id"}):
                raise ValueError("Posted sales invoice lines cannot be changed; create an adjustment or reversal instead.")
        if isinstance(obj, CustomerReceiptAllocation) and obj.receipt is not None and obj.receipt.journal_entry_id is not None:
            if _has_column_changes(obj, {"invoice_id", "amount"}):
                raise ValueError("Posted receipt allocations cannot be changed; create a reversal or adjustment instead.")
        if isinstance(obj, SupplierBill) and _was_posted(obj, SupplierBillStatus.POSTED):
            protected = {
                "bill_number",
                "vendor_id",
                "purchase_order_id",
                "project_id",
                "bill_date",
                "due_date",
                "currency",
                "payment_terms",
                "reference",
                "notes",
                "journal_entry_id",
                "posted_at",
            }
            if _has_column_changes(obj, protected):
                raise ValueError("Posted supplier bills are immutable; create an adjustment or reversal instead.")
        if isinstance(obj, SupplierBillLine) and obj.bill is not None and obj.bill.journal_entry_id is not None:
            if _has_column_changes(obj, {"description", "quantity", "unit_price", "tax_amount", "expense_account_id"}):
                raise ValueError("Posted supplier bill lines cannot be changed; create an adjustment or reversal instead.")
        if isinstance(obj, SupplierPayment) and _was_posted(obj, SupplierPaymentStatus.POSTED):
            protected = {
                "payment_number",
                "vendor_id",
                "payment_date",
                "currency",
                "amount",
                "bank_account_id",
                "reference",
                "notes",
                "journal_entry_id",
                "posted_at",
            }
            if _has_column_changes(obj, protected):
                raise ValueError("Posted supplier payments are immutable; create a reversal or adjustment instead.")
        if isinstance(obj, SupplierPaymentAllocation) and obj.payment is not None and obj.payment.journal_entry_id is not None:
            if _has_column_changes(obj, {"bill_id", "amount"}):
                raise ValueError("Posted supplier payment allocations cannot be changed; create a reversal or adjustment instead.")
