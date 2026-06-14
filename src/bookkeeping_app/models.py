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


class TransactionKind(StrEnum):
    EXPENSE = "expense"
    INCOME = "income"


class TransactionStatus(StrEnum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    POSTED = "posted"


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
    notes: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    transactions: Mapped[list["OperationalTransaction"]] = relationship(back_populates="contact")


class Receipt(Base):
    __tablename__ = "receipts"

    id: Mapped[int] = mapped_column(primary_key=True)
    original_filename: Mapped[str] = mapped_column(String(240))
    stored_path: Mapped[str] = mapped_column(String(320))
    content_type: Mapped[str | None] = mapped_column(String(120), default=None)
    size_bytes: Mapped[int] = mapped_column(default=0)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    transaction: Mapped["OperationalTransaction | None"] = relationship(back_populates="receipt")


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
