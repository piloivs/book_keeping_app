from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from bookkeeping_app.accounting import seed_default_accounts
from bookkeeping_app.database import Base
from bookkeeping_app.models import Account, ContactType, JournalLine, SalesInvoiceStatus, SalesOrderStatus
from bookkeeping_app.operations import (
    accounts_receivable_ageing,
    client_history,
    create_contact,
    create_customer_receipt,
    create_sales_order,
    create_sales_invoice,
    issue_sales_invoice,
    link_sales_invoice_to_sales_order,
)
from bookkeeping_app.schemas import (
    ContactCreate,
    CustomerReceiptAllocationCreate,
    CustomerReceiptCreate,
    SalesInvoiceCreate,
    SalesInvoiceLineCreate,
    SalesOrderCreate,
    SalesOrderLineCreate,
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


def customer(db):
    return create_contact(
        db,
        ContactCreate(
            name="Acme Projects",
            type=ContactType.CUSTOMER,
            payment_terms="Net 30",
        ),
    )


def invoice_payload(db, customer_id: int, status: SalesInvoiceStatus = SalesInvoiceStatus.DRAFT) -> SalesInvoiceCreate:
    return SalesInvoiceCreate(
        status=status,
        customer_id=customer_id,
        issue_date=date(2026, 6, 1),
        due_date=date(2026, 7, 1),
        currency="sgd",
        payment_terms="Net 30",
        lines=[
            SalesInvoiceLineCreate(
                description="AI workflow implementation",
                quantity=Decimal("1"),
                unit_price=Decimal("1000.00"),
                tax_amount=Decimal("90.00"),
                revenue_account_id=account_id(db, "4100"),
            )
        ],
    )


def test_issued_sales_invoice_posts_ar_revenue_and_gst(db_session) -> None:
    client = customer(db_session)

    invoice = create_sales_invoice(db_session, invoice_payload(db_session, client.id, SalesInvoiceStatus.ISSUED))

    assert invoice.status == SalesInvoiceStatus.ISSUED
    assert invoice.invoice_number.startswith("INV-202606-")
    assert invoice.total == Decimal("1090.00")
    assert invoice.amount_due == Decimal("1090.00")
    assert invoice.journal_entry_id is not None
    lines = db_session.scalars(select(JournalLine).where(JournalLine.journal_entry_id == invoice.journal_entry_id)).all()
    ar_line = next(line for line in lines if line.account_id == account_id(db_session, "1100"))
    revenue_line = next(line for line in lines if line.account_id == account_id(db_session, "4100"))
    gst_line = next(line for line in lines if line.account_id == account_id(db_session, "2200"))
    assert ar_line.debit == Decimal("1090.00")
    assert revenue_line.credit == Decimal("1000.00")
    assert gst_line.credit == Decimal("90.00")


def test_issued_sales_invoice_line_cannot_be_silently_edited(db_session) -> None:
    client = customer(db_session)
    invoice = create_sales_invoice(db_session, invoice_payload(db_session, client.id, SalesInvoiceStatus.ISSUED))

    invoice.lines[0].unit_price = Decimal("1200.00")

    with pytest.raises(ValueError, match="Posted sales invoice lines"):
        db_session.commit()


def test_draft_sales_invoice_can_be_issued_once(db_session) -> None:
    client = customer(db_session)
    invoice = create_sales_invoice(db_session, invoice_payload(db_session, client.id))

    issued = issue_sales_invoice(db_session, invoice.id)
    issued_again = issue_sales_invoice(db_session, invoice.id)

    assert issued.status == SalesInvoiceStatus.ISSUED
    assert issued.journal_entry_id == issued_again.journal_entry_id


def test_customer_receipt_posts_bank_and_reduces_invoice_amount_due(db_session) -> None:
    client = customer(db_session)
    invoice = create_sales_invoice(db_session, invoice_payload(db_session, client.id, SalesInvoiceStatus.ISSUED))

    receipt = create_customer_receipt(
        db_session,
        CustomerReceiptCreate(
            customer_id=client.id,
            receipt_date=date(2026, 6, 15),
            amount=Decimal("500.00"),
            bank_account_id=account_id(db_session, "1010"),
            reference="BANK-001",
            allocations=[
                CustomerReceiptAllocationCreate(
                    invoice_id=invoice.id,
                    amount=Decimal("500.00"),
                )
            ],
        ),
    )
    refreshed_invoice = receipt.allocations[0].invoice

    assert receipt.receipt_number == "INV-202606-0001-R20260615-01"
    assert receipt.journal_entry_id is not None
    assert refreshed_invoice.status == SalesInvoiceStatus.PARTIALLY_PAID
    assert refreshed_invoice.amount_paid == Decimal("500.00")
    assert refreshed_invoice.amount_due == Decimal("590.00")

    lines = db_session.scalars(select(JournalLine).where(JournalLine.journal_entry_id == receipt.journal_entry_id)).all()
    bank_line = next(line for line in lines if line.account_id == account_id(db_session, "1010"))
    ar_line = next(line for line in lines if line.account_id == account_id(db_session, "1100"))
    assert bank_line.debit == Decimal("500.00")
    assert ar_line.credit == Decimal("500.00")


def test_posted_customer_receipt_allocation_cannot_be_silently_edited(db_session) -> None:
    client = customer(db_session)
    invoice = create_sales_invoice(db_session, invoice_payload(db_session, client.id, SalesInvoiceStatus.ISSUED))
    receipt = create_customer_receipt(
        db_session,
        CustomerReceiptCreate(
            customer_id=client.id,
            receipt_date=date(2026, 6, 15),
            amount=Decimal("500.00"),
            bank_account_id=account_id(db_session, "1010"),
            allocations=[CustomerReceiptAllocationCreate(invoice_id=invoice.id, amount=Decimal("500.00"))],
        ),
    )

    receipt.allocations[0].amount = Decimal("499.00")

    with pytest.raises(ValueError, match="Posted receipt allocations"):
        db_session.commit()


def test_customer_receipt_number_serializes_by_invoice_and_date(db_session) -> None:
    client = customer(db_session)
    invoice = create_sales_invoice(db_session, invoice_payload(db_session, client.id, SalesInvoiceStatus.ISSUED))

    first = create_customer_receipt(
        db_session,
        CustomerReceiptCreate(
            customer_id=client.id,
            receipt_date=date(2026, 6, 15),
            amount=Decimal("100.00"),
            bank_account_id=account_id(db_session, "1010"),
            allocations=[CustomerReceiptAllocationCreate(invoice_id=invoice.id, amount=Decimal("100.00"))],
        ),
    )
    second = create_customer_receipt(
        db_session,
        CustomerReceiptCreate(
            customer_id=client.id,
            receipt_date=date(2026, 6, 15),
            amount=Decimal("100.00"),
            bank_account_id=account_id(db_session, "1010"),
            allocations=[CustomerReceiptAllocationCreate(invoice_id=invoice.id, amount=Decimal("100.00"))],
        ),
    )

    assert first.receipt_number == "INV-202606-0001-R20260615-01"
    assert second.receipt_number == "INV-202606-0001-R20260615-02"


def test_receipt_number_sequence_counts_legacy_numbers_for_same_invoice_and_date(db_session) -> None:
    client = customer(db_session)
    invoice = create_sales_invoice(db_session, invoice_payload(db_session, client.id, SalesInvoiceStatus.ISSUED))
    legacy = create_customer_receipt(
        db_session,
        CustomerReceiptCreate(
            receipt_number="REC-202606-0001",
            customer_id=client.id,
            receipt_date=date(2026, 6, 15),
            amount=Decimal("100.00"),
            bank_account_id=account_id(db_session, "1010"),
            allocations=[CustomerReceiptAllocationCreate(invoice_id=invoice.id, amount=Decimal("100.00"))],
        ),
    )

    next_receipt = create_customer_receipt(
        db_session,
        CustomerReceiptCreate(
            customer_id=client.id,
            receipt_date=date(2026, 6, 15),
            amount=Decimal("100.00"),
            bank_account_id=account_id(db_session, "1010"),
            allocations=[CustomerReceiptAllocationCreate(invoice_id=invoice.id, amount=Decimal("100.00"))],
        ),
    )

    assert legacy.receipt_number == "REC-202606-0001"
    assert next_receipt.receipt_number == "INV-202606-0001-R20260615-02"


def test_receipt_cannot_overpay_invoice(db_session) -> None:
    client = customer(db_session)
    invoice = create_sales_invoice(db_session, invoice_payload(db_session, client.id, SalesInvoiceStatus.ISSUED))

    with pytest.raises(ValueError, match="exceeds amount due"):
        create_customer_receipt(
            db_session,
            CustomerReceiptCreate(
                customer_id=client.id,
                receipt_date=date(2026, 6, 15),
                amount=Decimal("1200.00"),
                bank_account_id=account_id(db_session, "1010"),
                allocations=[
                    CustomerReceiptAllocationCreate(
                        invoice_id=invoice.id,
                        amount=Decimal("1200.00"),
                    )
                ],
            ),
        )


def test_ar_ageing_uses_invoice_due_date(db_session) -> None:
    client = customer(db_session)
    create_sales_invoice(
        db_session,
        SalesInvoiceCreate(
            status=SalesInvoiceStatus.ISSUED,
            customer_id=client.id,
            issue_date=date(2026, 2, 1),
            due_date=date(2026, 3, 1),
            lines=[
                SalesInvoiceLineCreate(
                    description="Older invoice",
                    quantity=Decimal("1"),
                    unit_price=Decimal("800.00"),
                    revenue_account_id=account_id(db_session, "4100"),
                )
            ],
        ),
    )

    report = accounts_receivable_ageing(db_session, as_of=date(2026, 6, 21))

    assert report.days_over_90 == Decimal("800.00")
    assert report.rows[0].customer_name == "Acme Projects"


def test_partial_invoice_and_payment_leave_sales_order_unbilled_balance(db_session) -> None:
    client = customer(db_session)
    order = create_sales_order(
        db_session,
        SalesOrderCreate(
            customer_id=client.id,
            received_date=date(2026, 6, 21),
            lines=[
                SalesOrderLineCreate(
                    description="Client service",
                    quantity=Decimal("1"),
                    unit_price=Decimal("3000.00"),
                    revenue_account_id=account_id(db_session, "4100"),
                )
            ],
        ),
    )
    invoice = create_sales_invoice(
        db_session,
        SalesInvoiceCreate(
            status=SalesInvoiceStatus.ISSUED,
            customer_id=client.id,
            issue_date=date(2026, 6, 21),
            due_date=date(2026, 6, 21),
            lines=[
                SalesInvoiceLineCreate(
                    description="Client service",
                    quantity=Decimal("1"),
                    unit_price=Decimal("1000.00"),
                    revenue_account_id=account_id(db_session, "4100"),
                )
            ],
        ),
    )
    create_customer_receipt(
        db_session,
        CustomerReceiptCreate(
            customer_id=client.id,
            receipt_date=date(2026, 6, 21),
            amount=Decimal("1000.00"),
            bank_account_id=account_id(db_session, "1010"),
            allocations=[CustomerReceiptAllocationCreate(invoice_id=invoice.id, amount=Decimal("1000.00"))],
        ),
    )

    refreshed_order = db_session.get(type(order), order.id)

    assert invoice.sales_order_id == order.id
    assert refreshed_order.status == SalesOrderStatus.PARTIALLY_INVOICED
    assert refreshed_order.total == Decimal("3000.00")
    assert refreshed_order.invoiced_total == Decimal("1000.00")
    assert refreshed_order.paid_total == Decimal("1000.00")
    assert refreshed_order.unbilled_total == Decimal("2000.00")


def test_existing_unlinked_invoice_can_be_linked_to_sales_order(db_session) -> None:
    client = customer(db_session)
    order = create_sales_order(
        db_session,
        SalesOrderCreate(
            customer_id=client.id,
            received_date=date(2026, 6, 21),
            lines=[
                SalesOrderLineCreate(
                    description="Client service",
                    quantity=Decimal("1"),
                    unit_price=Decimal("3000.00"),
                    revenue_account_id=account_id(db_session, "4100"),
                )
            ],
        ),
    )
    linked_invoice = create_sales_invoice(
        db_session,
        SalesInvoiceCreate(
            status=SalesInvoiceStatus.ISSUED,
            customer_id=client.id,
            sales_order_id=order.id,
            issue_date=date(2026, 6, 21),
            due_date=date(2026, 6, 21),
            lines=[
                SalesInvoiceLineCreate(
                    description="Linked invoice",
                    quantity=Decimal("1"),
                    unit_price=Decimal("1000.00"),
                    revenue_account_id=account_id(db_session, "4100"),
                )
            ],
        ),
    )
    unlinked_invoice = create_sales_invoice(
        db_session,
        SalesInvoiceCreate(
            status=SalesInvoiceStatus.ISSUED,
            customer_id=client.id,
            issue_date=date(2026, 6, 21),
            due_date=date(2026, 6, 21),
            lines=[
                SalesInvoiceLineCreate(
                    description="Unlinked invoice",
                    quantity=Decimal("1"),
                    unit_price=Decimal("1000.00"),
                    revenue_account_id=account_id(db_session, "4100"),
                )
            ],
        ),
    )
    unlinked_invoice.sales_order_id = None
    db_session.commit()
    create_customer_receipt(
        db_session,
        CustomerReceiptCreate(
            customer_id=client.id,
            receipt_date=date(2026, 6, 21),
            amount=Decimal("1000.00"),
            bank_account_id=account_id(db_session, "1010"),
            allocations=[CustomerReceiptAllocationCreate(invoice_id=unlinked_invoice.id, amount=Decimal("1000.00"))],
        ),
    )
    before_link = db_session.get(type(order), order.id)
    assert linked_invoice.sales_order_id == order.id
    assert before_link.unbilled_total == Decimal("2000.00")

    linked = link_sales_invoice_to_sales_order(db_session, unlinked_invoice.id, order.id)
    refreshed_order = db_session.get(type(order), order.id)

    assert linked.sales_order_id == order.id
    assert refreshed_order.invoiced_total == Decimal("2000.00")
    assert refreshed_order.paid_total == Decimal("1000.00")
    assert refreshed_order.unbilled_total == Decimal("1000.00")


def test_client_history_rolls_up_orders_invoices_receipts_and_balances(db_session) -> None:
    client = customer(db_session)
    order = create_sales_order(
        db_session,
        SalesOrderCreate(
            customer_id=client.id,
            received_date=date(2026, 6, 21),
            lines=[
                SalesOrderLineCreate(
                    description="Client service",
                    quantity=Decimal("1"),
                    unit_price=Decimal("3000.00"),
                    revenue_account_id=account_id(db_session, "4100"),
                )
            ],
        ),
    )
    invoice = create_sales_invoice(
        db_session,
        SalesInvoiceCreate(
            status=SalesInvoiceStatus.ISSUED,
            customer_id=client.id,
            sales_order_id=order.id,
            issue_date=date(2026, 6, 21),
            due_date=date(2026, 6, 21),
            lines=[
                SalesInvoiceLineCreate(
                    description="Client service",
                    quantity=Decimal("1"),
                    unit_price=Decimal("1000.00"),
                    revenue_account_id=account_id(db_session, "4100"),
                )
            ],
        ),
    )
    create_customer_receipt(
        db_session,
        CustomerReceiptCreate(
            customer_id=client.id,
            receipt_date=date(2026, 6, 21),
            amount=Decimal("1000.00"),
            bank_account_id=account_id(db_session, "1010"),
            allocations=[CustomerReceiptAllocationCreate(invoice_id=invoice.id, amount=Decimal("1000.00"))],
        ),
    )

    report = client_history(db_session)
    entry = report.clients[0]

    assert report.ordered_total == Decimal("3000.00")
    assert report.invoiced_total == Decimal("1000.00")
    assert report.paid_total == Decimal("1000.00")
    assert report.receivable_total == Decimal("0.00")
    assert report.unbilled_total == Decimal("2000.00")
    assert entry.customer.name == "Acme Projects"
    assert entry.sales_orders[0].order_number == order.order_number
    assert entry.sales_invoices[0].invoice_number == invoice.invoice_number
    assert entry.customer_receipts[0].amount == Decimal("1000.00")
