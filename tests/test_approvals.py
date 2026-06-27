from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from bookkeeping_app.accounting import seed_default_accounts
from bookkeeping_app.database import Base
from bookkeeping_app.models import Account, ApprovalStatus, ContactType
from bookkeeping_app.operations import (
    approve_request,
    create_contact,
    create_supplier_bill,
    post_supplier_bill,
    reject_request,
    request_approval,
)
from bookkeeping_app.schemas import (
    ApprovalDecision,
    ApprovalRequestCreate,
    ContactCreate,
    SupplierBillCreate,
    SupplierBillLineCreate,
)


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as db:
        seed_default_accounts(db)
        yield db


def account_id(db, code: str) -> int:
    return db.scalar(select(Account.id).where(Account.code == code))


def draft_supplier_bill(db):
    supplier = create_contact(db, ContactCreate(name="Approval Vendor", type=ContactType.VENDOR))
    return create_supplier_bill(
        db,
        SupplierBillCreate(
            vendor_id=supplier.id,
            bill_date=date(2026, 6, 20),
            due_date=date(2026, 7, 20),
            lines=[
                SupplierBillLineCreate(
                    description="Approval controlled service",
                    quantity=Decimal("1"),
                    unit_price=Decimal("800.00"),
                    expense_account_id=account_id(db, "5200"),
                )
            ],
        ),
    )


def test_pending_approval_blocks_supplier_bill_posting(db_session) -> None:
    bill = draft_supplier_bill(db_session)
    request = request_approval(
        db_session,
        ApprovalRequestCreate(
            document_type="supplier_bill",
            document_id=bill.id,
            action="post",
            requested_by="ops",
        ),
    )

    with pytest.raises(ValueError, match="awaiting approval"):
        post_supplier_bill(db_session, bill.id)

    assert request.status == ApprovalStatus.PENDING


def test_approved_request_allows_supplier_bill_posting(db_session) -> None:
    bill = draft_supplier_bill(db_session)
    request = request_approval(
        db_session,
        ApprovalRequestCreate(document_type="supplier_bill", document_id=bill.id, action="post"),
    )
    approve_request(db_session, request.id, ApprovalDecision(decided_by="manager", decision_notes="Looks good."))

    posted = post_supplier_bill(db_session, bill.id)

    assert posted.journal_entry_id is not None


def test_rejected_request_blocks_until_new_request_is_approved(db_session) -> None:
    bill = draft_supplier_bill(db_session)
    first_request = request_approval(
        db_session,
        ApprovalRequestCreate(document_type="supplier_bill", document_id=bill.id, action="post"),
    )
    reject_request(db_session, first_request.id, ApprovalDecision(decided_by="manager", decision_notes="Need backup."))

    with pytest.raises(ValueError, match="rejected"):
        post_supplier_bill(db_session, bill.id)

    second_request = request_approval(
        db_session,
        ApprovalRequestCreate(document_type="supplier_bill", document_id=bill.id, action="post", reason="Backup added."),
    )
    approve_request(db_session, second_request.id, ApprovalDecision(decided_by="manager"))

    posted = post_supplier_bill(db_session, bill.id)

    assert posted.journal_entry_id is not None
