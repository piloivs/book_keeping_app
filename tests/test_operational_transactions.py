from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from bookkeeping_app.accounting import seed_default_accounts
from bookkeeping_app.database import Base
from bookkeeping_app.models import Account, JournalEntry, TransactionKind, TransactionStatus
from bookkeeping_app.operations import create_operational_transaction
from bookkeeping_app.schemas import OperationalTransactionCreate, ReceiptPayload


@pytest.fixture()
def db_session(tmp_path, monkeypatch):
    monkeypatch.setattr("bookkeeping_app.operations.RECEIPT_DIR", tmp_path / "receipts")
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as db:
        seed_default_accounts(db)
        yield db


def account_id(db, code: str) -> int:
    return db.scalar(select(Account.id).where(Account.code == code))


def test_posted_expense_creates_journal_entry_and_receipt(db_session, tmp_path) -> None:
    transaction = create_operational_transaction(
        db_session,
        OperationalTransactionCreate(
            kind=TransactionKind.EXPENSE,
            status=TransactionStatus.POSTED,
            transaction_date=date(2026, 6, 14),
            description="Corporate secretary fees",
            amount=Decimal("250.00"),
            debit_account_id=account_id(db_session, "5200"),
            credit_account_id=account_id(db_session, "1010"),
            receipt=ReceiptPayload(
                filename="invoice.txt",
                content_type="text/plain",
                content_base64="UmVjZWlwdA==",
            ),
        ),
    )

    assert transaction.status == TransactionStatus.POSTED
    assert transaction.journal_entry_id is not None
    assert transaction.receipt is not None
    assert (tmp_path / "receipts").exists()
    assert db_session.scalar(select(JournalEntry).where(JournalEntry.id == transaction.journal_entry_id)) is not None


def test_expense_requires_expense_debit_account(db_session) -> None:
    with pytest.raises(ValueError, match="must debit an expense account"):
        create_operational_transaction(
            db_session,
            OperationalTransactionCreate(
                kind=TransactionKind.EXPENSE,
                status=TransactionStatus.POSTED,
                transaction_date=date(2026, 6, 14),
                description="Invalid expense",
                amount=Decimal("25.00"),
                debit_account_id=account_id(db_session, "1010"),
                credit_account_id=account_id(db_session, "1010"),
            ),
        )

