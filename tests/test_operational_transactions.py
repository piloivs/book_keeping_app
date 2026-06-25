import json
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from bookkeeping_app.accounting import create_journal_entry, seed_default_accounts
from bookkeeping_app.database import Base
from bookkeeping_app.models import Account, JournalEntry, ReceiptExtractionStatus, TransactionKind, TransactionStatus
from bookkeeping_app.operations import accounts_receivable_ageing, create_contact, create_operational_transaction, extract_receipt_details
from bookkeeping_app.schemas import ContactCreate, JournalEntryCreate, OperationalTransactionCreate, ReceiptPayload


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


def test_receipt_extraction_records_not_configured_status(db_session, monkeypatch) -> None:
    monkeypatch.setenv("RECEIPT_EXTRACTION_PROVIDER", "tesseract")
    from bookkeeping_app.config import get_settings

    get_settings.cache_clear()
    transaction = create_operational_transaction(
        db_session,
        OperationalTransactionCreate(
            kind=TransactionKind.EXPENSE,
            status=TransactionStatus.DRAFT,
            transaction_date=date(2026, 6, 14),
            description="Receipt only",
            amount=Decimal("12.50"),
            debit_account_id=account_id(db_session, "5100"),
            credit_account_id=account_id(db_session, "1010"),
            receipt=ReceiptPayload(
                filename="receipt.jpg",
                content_type="image/jpeg",
                content_base64="UmVjZWlwdA==",
            ),
        ),
    )
    monkeypatch.setattr(
        "bookkeeping_app.operations._extract_with_tesseract",
        lambda receipt: (_ for _ in ()).throw(RuntimeError("Tesseract was not found. Set TESSERACT_CMD in .env or add tesseract to PATH.")),
    )

    extraction = extract_receipt_details(db_session, transaction.receipt.id)

    assert extraction.status == ReceiptExtractionStatus.NOT_CONFIGURED
    assert "Tesseract" in extraction.error_message


def test_receipt_extraction_stores_structured_result(db_session, monkeypatch) -> None:
    monkeypatch.setenv("RECEIPT_EXTRACTION_PROVIDER", "tesseract")
    from bookkeeping_app.config import get_settings

    get_settings.cache_clear()
    transaction = create_operational_transaction(
        db_session,
        OperationalTransactionCreate(
            kind=TransactionKind.EXPENSE,
            status=TransactionStatus.DRAFT,
            transaction_date=date(2026, 6, 14),
            description="Coffee supplies",
            amount=Decimal("18.30"),
            debit_account_id=account_id(db_session, "5000"),
            credit_account_id=account_id(db_session, "1010"),
            receipt=ReceiptPayload(
                filename="receipt.jpg",
                content_type="image/jpeg",
                content_base64="UmVjZWlwdA==",
            ),
        ),
    )
    monkeypatch.setattr(
        "bookkeeping_app.operations._extract_with_tesseract",
        lambda receipt: {
            "merchant_name": "Corner Cafe",
            "receipt_date": "2026-06-14",
            "currency": "SGD",
            "subtotal": 17.0,
            "tax": 1.3,
            "total": 18.3,
            "confidence": 0.91,
            "raw_text": "Corner Cafe\nCoffee beans 18.30",
            "line_items": [
                {
                    "description": "Coffee beans",
                    "quantity": 1,
                    "unit_price": 18.3,
                    "amount": 18.3,
                    "confidence": 0.88,
                }
            ],
        },
    )

    extraction = extract_receipt_details(db_session, transaction.receipt.id)

    assert extraction.status == ReceiptExtractionStatus.COMPLETED
    assert extraction.merchant_name == "Corner Cafe"
    assert extraction.total == Decimal("18.30")
    assert len(extraction.line_items) == 1
    assert extraction.line_items[0].description == "Coffee beans"


def test_tesseract_ollama_extraction_stores_structured_result(db_session, monkeypatch) -> None:
    monkeypatch.setenv("RECEIPT_EXTRACTION_PROVIDER", "tesseract_ollama")
    from bookkeeping_app.config import get_settings

    get_settings.cache_clear()
    transaction = create_operational_transaction(
        db_session,
        OperationalTransactionCreate(
            kind=TransactionKind.EXPENSE,
            status=TransactionStatus.DRAFT,
            transaction_date=date(2026, 6, 14),
            description="Office receipt",
            amount=Decimal("21.80"),
            debit_account_id=account_id(db_session, "5000"),
            credit_account_id=account_id(db_session, "1010"),
            receipt=ReceiptPayload(
                filename="receipt.jpg",
                content_type="image/jpeg",
                content_base64="UmVjZWlwdA==",
            ),
        ),
    )
    monkeypatch.setattr(
        "bookkeeping_app.operations._extract_with_tesseract",
        lambda receipt: {
            "merchant_name": "Fallback Merchant",
            "receipt_date": None,
            "currency": "SGD",
            "subtotal": None,
            "tax": None,
            "total": Decimal("21.80"),
            "confidence": 0.55,
            "raw_text": "Stationery Shop\n2026-06-14\nNotebook 21.80\nTOTAL 21.80",
            "line_items": [],
        },
    )

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return json.dumps(
                {
                    "response": json.dumps(
                        {
                            "merchant_name": "Stationery Shop",
                            "receipt_date": "2026-06-14",
                            "currency": "SGD",
                            "subtotal": None,
                            "tax": None,
                            "total": 21.8,
                            "confidence": 0.82,
                            "raw_text": "",
                            "line_items": [
                                {
                                    "description": "Notebook",
                                    "quantity": 1,
                                    "unit_price": 21.8,
                                    "amount": 21.8,
                                    "confidence": 0.8,
                                }
                            ],
                        }
                    )
                }
            ).encode("utf-8")

    monkeypatch.setattr("bookkeeping_app.operations.urllib.request.urlopen", lambda request, timeout: FakeResponse())

    extraction = extract_receipt_details(db_session, transaction.receipt.id)

    assert extraction.provider == "tesseract_ollama"
    assert extraction.status == ReceiptExtractionStatus.COMPLETED
    assert extraction.merchant_name == "Stationery Shop"
    assert extraction.total == Decimal("21.80")
    assert extraction.raw_text.startswith("Stationery Shop")
    assert extraction.line_items[0].description == "Notebook"


def test_accounts_receivable_ageing_uses_posted_ledger_lines_and_applies_oldest_credits(db_session) -> None:
    customer = create_contact(db_session, ContactCreate(name="Acme Projects", type="customer"))
    create_operational_transaction(
        db_session,
        OperationalTransactionCreate(
            kind=TransactionKind.INCOME,
            status=TransactionStatus.POSTED,
            transaction_date=date(2026, 2, 1),
            description="February project billing",
            amount=Decimal("1000.00"),
            contact_id=customer.id,
            debit_account_id=account_id(db_session, "1100"),
            credit_account_id=account_id(db_session, "4100"),
        ),
    )
    create_operational_transaction(
        db_session,
        OperationalTransactionCreate(
            kind=TransactionKind.INCOME,
            status=TransactionStatus.POSTED,
            transaction_date=date(2026, 5, 20),
            description="May project billing",
            amount=Decimal("500.00"),
            contact_id=customer.id,
            debit_account_id=account_id(db_session, "1100"),
            credit_account_id=account_id(db_session, "4100"),
        ),
    )
    create_journal_entry(
        db_session,
        JournalEntryCreate(
            entry_date=date(2026, 6, 1),
            memo="Customer payment",
            lines=[
                {
                    "account_id": account_id(db_session, "1010"),
                    "debit": Decimal("300.00"),
                    "description": "Partial customer payment",
                },
                {
                    "account_id": account_id(db_session, "1100"),
                    "credit": Decimal("300.00"),
                    "description": "Partial customer payment",
                },
            ],
        ),
    )

    report = accounts_receivable_ageing(db_session, as_of=date(2026, 6, 21))

    assert report.total == Decimal("1200.00")
    assert report.days_31_60 == Decimal("500.00")
    assert report.days_over_90 == Decimal("700.00")
    assert len(report.rows) == 1
    assert report.rows[0].customer_name == "Acme Projects"
    assert report.rows[0].total == Decimal("1200.00")


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
