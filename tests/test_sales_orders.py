from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from bookkeeping_app.accounting import seed_default_accounts
from bookkeeping_app.database import Base
from bookkeeping_app.models import Account, ContactType, DepositStatus, JournalLine, SalesOrderStatus, TransactionKind
from bookkeeping_app.operations import accept_sales_order, create_contact, create_sales_order, post_unposted_paid_sales_order_deposits
from bookkeeping_app.schemas import ContactCreate, SalesOrderCreate, SalesOrderLineCreate


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


def customer(db, contact_type: ContactType = ContactType.CUSTOMER):
    return create_contact(
        db,
        ContactCreate(
            name=f"{contact_type.value.title()} Contact",
            type=contact_type,
            payment_terms="Net 14",
        ),
    )


def sales_order_payload(db, customer_id: int, status: SalesOrderStatus = SalesOrderStatus.RECEIVED) -> SalesOrderCreate:
    return SalesOrderCreate(
        client_po_number="CLIENT-PO-1007",
        status=status,
        customer_id=customer_id,
        received_date=date(2026, 6, 19),
        expected_delivery_date=date(2026, 6, 26),
        currency="sgd",
        payment_terms="Net 14",
        lines=[
            SalesOrderLineCreate(
                description="AI workflow implementation",
                quantity=Decimal("1"),
                unit_price=Decimal("2400.00"),
                tax_amount=Decimal("216.00"),
                revenue_account_id=account_id(db, "4100"),
            )
        ],
    )


def test_client_purchase_order_can_be_received_from_customer(db_session) -> None:
    client = customer(db_session)

    sales_order = create_sales_order(db_session, sales_order_payload(db_session, client.id))

    assert sales_order.status == SalesOrderStatus.RECEIVED
    assert sales_order.order_number.startswith("SO-202606-")
    assert sales_order.client_po_number == "CLIENT-PO-1007"
    assert sales_order.customer.name == "Customer Contact"
    assert sales_order.subtotal == Decimal("2400.00")
    assert sales_order.tax_total == Decimal("216.00")
    assert sales_order.total == Decimal("2616.00")
    assert sales_order.deposit_required is False
    assert sales_order.deposit_amount == Decimal("0.00")


def test_sales_order_can_be_booked_without_customer_po(db_session) -> None:
    client = customer(db_session)
    payload = sales_order_payload(db_session, client.id)
    payload.client_po_number = None

    sales_order = create_sales_order(db_session, payload)

    assert sales_order.order_number.startswith("SO-202606-")
    assert sales_order.client_po_number == f"NO-PO-{sales_order.order_number}"


def test_required_deposit_defaults_to_ten_percent_of_order_total(db_session) -> None:
    client = customer(db_session)
    payload = sales_order_payload(db_session, client.id)
    payload.deposit_required = True

    sales_order = create_sales_order(db_session, payload)

    assert sales_order.deposit_required is True
    assert sales_order.deposit_rate == Decimal("0.1000")
    assert sales_order.deposit_amount == Decimal("261.60")
    assert sales_order.deposit_status.value == "requested"


def test_custom_deposit_amount_can_be_stored(db_session) -> None:
    client = customer(db_session)
    payload = sales_order_payload(db_session, client.id)
    payload.deposit_required = True
    payload.deposit_rate = Decimal("0.0500")
    payload.deposit_amount = Decimal("150.00")

    sales_order = create_sales_order(db_session, payload)

    assert sales_order.deposit_rate == Decimal("0.0500")
    assert sales_order.deposit_amount == Decimal("150.00")


def test_paid_deposit_posts_transaction_to_deferred_revenue(db_session) -> None:
    client = customer(db_session)
    payload = sales_order_payload(db_session, client.id)
    payload.deposit_required = True
    payload.deposit_rate = Decimal("0.0500")
    payload.deposit_status = DepositStatus.PAID

    sales_order = create_sales_order(db_session, payload)

    assert sales_order.deposit_transaction_id is not None
    transaction = sales_order.deposit_transaction
    assert transaction is not None
    assert transaction.kind == TransactionKind.DEPOSIT
    assert transaction.amount == Decimal("130.80")
    assert transaction.journal_entry_id is not None

    lines = db_session.scalars(select(JournalLine).where(JournalLine.journal_entry_id == transaction.journal_entry_id)).all()
    bank_line = next(line for line in lines if line.account_id == account_id(db_session, "1010"))
    deferred_line = next(line for line in lines if line.account_id == account_id(db_session, "2150"))
    assert bank_line.debit == Decimal("130.80")
    assert deferred_line.credit == Decimal("130.80")


def test_paid_deposit_backfill_posts_existing_paid_order_once(db_session) -> None:
    client = customer(db_session)
    payload = sales_order_payload(db_session, client.id)
    payload.deposit_required = True
    payload.deposit_status = DepositStatus.PAID
    sales_order = create_sales_order(db_session, payload)
    original_transaction_id = sales_order.deposit_transaction_id
    sales_order.deposit_transaction_id = None
    db_session.commit()

    posted_count = post_unposted_paid_sales_order_deposits(db_session)
    second_count = post_unposted_paid_sales_order_deposits(db_session)
    refreshed = db_session.get(type(sales_order), sales_order.id)

    assert posted_count == 1
    assert second_count == 0
    assert refreshed.deposit_transaction_id is not None
    assert refreshed.deposit_transaction_id != original_transaction_id


def test_deposit_amount_cannot_exceed_order_total(db_session) -> None:
    client = customer(db_session)
    payload = sales_order_payload(db_session, client.id)
    payload.deposit_required = True
    payload.deposit_amount = Decimal("3000.00")

    with pytest.raises(ValueError, match="cannot exceed"):
        create_sales_order(db_session, payload)


def test_vendor_contact_cannot_submit_client_purchase_order(db_session) -> None:
    vendor = customer(db_session, ContactType.VENDOR)

    with pytest.raises(ValueError, match="customer contacts"):
        create_sales_order(db_session, sales_order_payload(db_session, vendor.id))


def test_received_client_purchase_order_can_be_accepted(db_session) -> None:
    client = customer(db_session)
    sales_order = create_sales_order(db_session, sales_order_payload(db_session, client.id))

    accepted = accept_sales_order(db_session, sales_order.id)

    assert accepted.status == SalesOrderStatus.ACCEPTED
    assert accepted.accepted_at is not None


def test_sales_order_line_requires_revenue_account(db_session) -> None:
    client = customer(db_session)
    payload = sales_order_payload(db_session, client.id)
    payload.lines[0].revenue_account_id = account_id(db_session, "5200")

    with pytest.raises(ValueError, match="revenue accounts"):
        create_sales_order(db_session, payload)
