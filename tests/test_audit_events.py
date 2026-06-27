from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from bookkeeping_app.accounting import create_journal_entry, seed_default_accounts
from bookkeeping_app.database import Base
from bookkeeping_app.models import Account, ContactType
from bookkeeping_app.operations import (
    approve_request,
    create_bank_statement_line,
    create_contact,
    create_supplier_bill,
    list_audit_events,
    post_supplier_bill,
    reconcile_bank_statement_line,
    request_approval,
)
from bookkeeping_app.schemas import (
    ApprovalDecision,
    ApprovalRequestCreate,
    BankStatementLineCreate,
    ContactCreate,
    JournalEntryCreate,
    SupplierBillCreate,
    SupplierBillLineCreate,
)


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    seed_default_accounts(db)
    return db


def account_id(db, code: str) -> int:
    return db.scalar(select(Account.id).where(Account.code == code))


def test_approval_request_and_decision_write_audit_events() -> None:
    db = make_session()
    request = request_approval(
        db,
        ApprovalRequestCreate(
            document_type="supplier_bill",
            document_id=42,
            action="post",
            requested_by="ops",
        ),
    )

    approve_request(db, request.id, ApprovalDecision(decided_by="manager"))

    events = list_audit_events(db)
    assert [event.action for event in events[:2]] == ["approved", "requested"]
    assert events[0].entity_type == "approval_request"
    assert events[0].actor == "manager"


def test_supplier_bill_post_writes_audit_event() -> None:
    db = make_session()
    supplier = create_contact(db, ContactCreate(name="Audit Vendor", type=ContactType.VENDOR))
    bill = create_supplier_bill(
        db,
        SupplierBillCreate(
            vendor_id=supplier.id,
            bill_date=date(2026, 6, 20),
            due_date=date(2026, 7, 20),
            lines=[
                SupplierBillLineCreate(
                    description="Audit service",
                    quantity=Decimal("1"),
                    unit_price=Decimal("125.00"),
                    expense_account_id=account_id(db, "5200"),
                )
            ],
        ),
    )

    post_supplier_bill(db, bill.id)

    event = list_audit_events(db)[0]
    assert event.entity_type == "supplier_bill"
    assert event.entity_id == bill.id
    assert event.action == "posted"
    assert "Accounts Payable" in event.summary


def test_bank_reconciliation_writes_audit_event() -> None:
    db = make_session()
    entry = create_journal_entry(
        db,
        JournalEntryCreate(
            entry_date=date(2026, 6, 25),
            memo="Customer receipt",
            lines=[
                {"account_id": account_id(db, "1010"), "debit": Decimal("75.00")},
                {"account_id": account_id(db, "1100"), "credit": Decimal("75.00")},
            ],
        ),
    )
    statement_line = create_bank_statement_line(
        db,
        BankStatementLineCreate(
            bank_account_id=account_id(db, "1010"),
            statement_date=date(2026, 6, 25),
            description="Incoming transfer",
            amount=Decimal("75.00"),
        ),
    )

    reconcile_bank_statement_line(db, statement_line.id, entry.id)

    event = list_audit_events(db)[0]
    assert event.entity_type == "bank_statement_line"
    assert event.entity_id == statement_line.id
    assert event.action == "reconciled"
