from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from bookkeeping_app.accounting import seed_default_accounts
from bookkeeping_app.database import Base
from bookkeeping_app.models import Account, ContactType, PurchaseOrderStatus, VendorQualificationStatus
from bookkeeping_app.operations import create_contact, create_purchase_order, issue_purchase_order
from bookkeeping_app.schemas import ContactCreate, PurchaseOrderCreate, PurchaseOrderLineCreate


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


def vendor(db, status: VendorQualificationStatus):
    return create_contact(
        db,
        ContactCreate(
            name=f"{status.value.title()} Vendor",
            type=ContactType.VENDOR,
            vendor_qualification_status=status,
            payment_terms="Net 30",
            default_expense_account_id=account_id(db, "5200"),
        ),
    )


def po_payload(db, vendor_id: int, status: PurchaseOrderStatus = PurchaseOrderStatus.DRAFT) -> PurchaseOrderCreate:
    return PurchaseOrderCreate(
        status=status,
        vendor_id=vendor_id,
        issue_date=date(2026, 6, 17),
        expected_delivery_date=date(2026, 6, 24),
        currency="sgd",
        payment_terms="50% upfront, balance on delivery",
        lines=[
            PurchaseOrderLineCreate(
                description="Corporate secretarial service",
                quantity=Decimal("2"),
                unit_price=Decimal("125.00"),
                tax_amount=Decimal("22.50"),
                expense_account_id=account_id(db, "5200"),
            )
        ],
    )


def test_draft_purchase_order_can_be_created_for_pending_vendor(db_session) -> None:
    pending_vendor = vendor(db_session, VendorQualificationStatus.PENDING)

    purchase_order = create_purchase_order(db_session, po_payload(db_session, pending_vendor.id))

    assert purchase_order.status == PurchaseOrderStatus.DRAFT
    assert purchase_order.po_number.startswith("PO-202606-")
    assert purchase_order.vendor.name == "Pending Vendor"
    assert purchase_order.subtotal == Decimal("250.00")
    assert purchase_order.tax_total == Decimal("22.50")
    assert purchase_order.total == Decimal("272.50")
    assert purchase_order.payment_terms == "50% upfront, balance on delivery"


def test_unqualified_vendor_cannot_receive_issued_purchase_order(db_session) -> None:
    pending_vendor = vendor(db_session, VendorQualificationStatus.PENDING)

    with pytest.raises(ValueError, match="qualified vendors"):
        create_purchase_order(db_session, po_payload(db_session, pending_vendor.id, PurchaseOrderStatus.ISSUED))


def test_draft_purchase_order_can_be_issued_to_qualified_vendor(db_session) -> None:
    qualified_vendor = vendor(db_session, VendorQualificationStatus.QUALIFIED)
    purchase_order = create_purchase_order(db_session, po_payload(db_session, qualified_vendor.id))

    issued = issue_purchase_order(db_session, purchase_order.id)

    assert issued.status == PurchaseOrderStatus.ISSUED
    assert issued.issued_at is not None


def test_purchase_order_line_requires_expense_account(db_session) -> None:
    qualified_vendor = vendor(db_session, VendorQualificationStatus.QUALIFIED)
    payload = po_payload(db_session, qualified_vendor.id)
    payload.lines[0].expense_account_id = account_id(db_session, "1010")

    with pytest.raises(ValueError, match="expense accounts"):
        create_purchase_order(db_session, payload)
