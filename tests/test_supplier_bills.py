from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from bookkeeping_app.accounting import seed_default_accounts
from bookkeeping_app.database import Base
from bookkeeping_app.models import Account, ContactType, JournalEntry, SupplierBillStatus, SupplierPaymentStatus
from bookkeeping_app.operations import (
    accounts_payable_ageing,
    create_contact,
    create_project,
    create_purchase_order,
    create_supplier_bill,
    create_supplier_payment,
    get_supplier_bill,
    post_supplier_bill,
    project_profitability,
)
from bookkeeping_app.schemas import (
    ContactCreate,
    ProjectCreate,
    PurchaseOrderCreate,
    PurchaseOrderLineCreate,
    SupplierBillCreate,
    SupplierBillLineCreate,
    SupplierPaymentAllocationCreate,
    SupplierPaymentCreate,
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


def vendor(db, name: str = "Cloud Vendor"):
    return create_contact(db, ContactCreate(name=name, type=ContactType.VENDOR))


def test_posted_supplier_bill_creates_balanced_ap_journal(db_session) -> None:
    supplier = vendor(db_session)

    bill = create_supplier_bill(
        db_session,
        SupplierBillCreate(
            status=SupplierBillStatus.POSTED,
            vendor_id=supplier.id,
            bill_date=date(2026, 6, 20),
            due_date=date(2026, 7, 20),
            reference="INV-100",
            lines=[
                SupplierBillLineCreate(
                    description="Automation software",
                    quantity=Decimal("1"),
                    unit_price=Decimal("1000.00"),
                    tax_amount=Decimal("90.00"),
                    expense_account_id=account_id(db_session, "5100"),
                )
            ],
        ),
    )

    entry = db_session.get(JournalEntry, bill.journal_entry_id)
    amounts_by_code = {line.account.code: (line.debit, line.credit) for line in entry.lines}

    assert bill.status == SupplierBillStatus.POSTED
    assert bill.subtotal == Decimal("1000.00")
    assert bill.tax_total == Decimal("90.00")
    assert bill.total == Decimal("1090.00")
    assert amounts_by_code["5100"] == (Decimal("1000.00"), Decimal("0.00"))
    assert amounts_by_code["2210"] == (Decimal("90.00"), Decimal("0.00"))
    assert amounts_by_code["2000"] == (Decimal("0.00"), Decimal("1090.00"))


def test_draft_supplier_bill_can_be_posted_once(db_session) -> None:
    supplier = vendor(db_session)
    bill = create_supplier_bill(
        db_session,
        SupplierBillCreate(
            vendor_id=supplier.id,
            bill_date=date(2026, 6, 20),
            due_date=date(2026, 7, 20),
            lines=[
                SupplierBillLineCreate(
                    description="Professional services",
                    quantity=Decimal("2"),
                    unit_price=Decimal("125.00"),
                    expense_account_id=account_id(db_session, "5200"),
                )
            ],
        ),
    )

    assert bill.journal_entry_id is None
    posted = post_supplier_bill(db_session, bill.id)
    posted_again = post_supplier_bill(db_session, bill.id)

    assert posted.status == SupplierBillStatus.POSTED
    assert posted.journal_entry_id == posted_again.journal_entry_id


def test_supplier_bill_rejects_revenue_account(db_session) -> None:
    supplier = vendor(db_session)

    with pytest.raises(ValueError, match="expense or asset"):
        create_supplier_bill(
            db_session,
            SupplierBillCreate(
                vendor_id=supplier.id,
                bill_date=date(2026, 6, 20),
                due_date=date(2026, 7, 20),
                lines=[
                    SupplierBillLineCreate(
                        description="Wrong account",
                        quantity=Decimal("1"),
                        unit_price=Decimal("100.00"),
                        expense_account_id=account_id(db_session, "4100"),
                    )
                ],
            ),
        )


def test_supplier_bill_vendor_must_match_linked_purchase_order(db_session) -> None:
    first_vendor = vendor(db_session, "First Vendor")
    second_vendor = vendor(db_session, "Second Vendor")
    purchase_order = create_purchase_order(
        db_session,
        PurchaseOrderCreate(
            vendor_id=first_vendor.id,
            issue_date=date(2026, 6, 18),
            lines=[
                PurchaseOrderLineCreate(
                    description="Implementation support",
                    quantity=Decimal("1"),
                    unit_price=Decimal("500.00"),
                    expense_account_id=account_id(db_session, "5200"),
                )
            ],
        ),
    )

    with pytest.raises(ValueError, match="vendor must match"):
        create_supplier_bill(
            db_session,
            SupplierBillCreate(
                vendor_id=second_vendor.id,
                purchase_order_id=purchase_order.id,
                bill_date=date(2026, 6, 20),
                due_date=date(2026, 7, 20),
                lines=[
                    SupplierBillLineCreate(
                        description="Implementation support",
                        quantity=Decimal("1"),
                        unit_price=Decimal("500.00"),
                        expense_account_id=account_id(db_session, "5200"),
                    )
                ],
            ),
        )


def test_posted_supplier_bill_lines_are_immutable(db_session) -> None:
    supplier = vendor(db_session)
    bill = create_supplier_bill(
        db_session,
        SupplierBillCreate(
            status=SupplierBillStatus.POSTED,
            vendor_id=supplier.id,
            bill_date=date(2026, 6, 20),
            due_date=date(2026, 7, 20),
            lines=[
                SupplierBillLineCreate(
                    description="Software",
                    quantity=Decimal("1"),
                    unit_price=Decimal("100.00"),
                    expense_account_id=account_id(db_session, "5100"),
                )
            ],
        ),
    )

    bill.lines[0].unit_price = Decimal("101.00")

    with pytest.raises(ValueError, match="Posted supplier bill lines"):
        db_session.commit()


def test_project_profitability_includes_posted_supplier_bill_costs(db_session) -> None:
    client = create_contact(db_session, ContactCreate(name="Acme AI", type=ContactType.CUSTOMER))
    project = create_project(
        db_session,
        ProjectCreate(
            project_code="ACME-COST-001",
            name="Supplier cost tracking",
            client_id=client.id,
            contract_value=Decimal("2000.00"),
        ),
    )
    supplier = vendor(db_session)
    create_supplier_bill(
        db_session,
        SupplierBillCreate(
            status=SupplierBillStatus.POSTED,
            vendor_id=supplier.id,
            project_id=project.id,
            bill_date=date(2026, 6, 20),
            due_date=date(2026, 7, 20),
            lines=[
                SupplierBillLineCreate(
                    description="Subcontractor support",
                    quantity=Decimal("1"),
                    unit_price=Decimal("600.00"),
                    tax_amount=Decimal("54.00"),
                    expense_account_id=account_id(db_session, "5200"),
                )
            ],
        ),
    )

    report = project_profitability(db_session)

    assert report.rows[0].direct_costs == Decimal("600.00")
    assert report.rows[0].gross_profit == Decimal("-600.00")


def test_posted_supplier_payment_reduces_bill_due_and_posts_bank_journal(db_session) -> None:
    supplier = vendor(db_session)
    bill = create_supplier_bill(
        db_session,
        SupplierBillCreate(
            status=SupplierBillStatus.POSTED,
            vendor_id=supplier.id,
            bill_date=date(2026, 6, 20),
            due_date=date(2026, 7, 20),
            lines=[
                SupplierBillLineCreate(
                    description="Cloud subscription",
                    quantity=Decimal("1"),
                    unit_price=Decimal("300.00"),
                    tax_amount=Decimal("27.00"),
                    expense_account_id=account_id(db_session, "5100"),
                )
            ],
        ),
    )

    payment = create_supplier_payment(
        db_session,
        SupplierPaymentCreate(
            status=SupplierPaymentStatus.POSTED,
            vendor_id=supplier.id,
            payment_date=date(2026, 6, 25),
            amount=Decimal("127.00"),
            bank_account_id=account_id(db_session, "1010"),
            allocations=[SupplierPaymentAllocationCreate(bill_id=bill.id, amount=Decimal("127.00"))],
        ),
    )
    refreshed_bill = get_supplier_bill(db_session, bill.id)
    entry = db_session.get(JournalEntry, payment.journal_entry_id)
    amounts_by_code = {line.account.code: (line.debit, line.credit) for line in entry.lines}

    assert payment.status == SupplierPaymentStatus.POSTED
    assert refreshed_bill.amount_paid == Decimal("127.00")
    assert refreshed_bill.amount_due == Decimal("200.00")
    assert amounts_by_code["2000"] == (Decimal("127.00"), Decimal("0.00"))
    assert amounts_by_code["1010"] == (Decimal("0.00"), Decimal("127.00"))


def test_supplier_payment_cannot_overpay_bill(db_session) -> None:
    supplier = vendor(db_session)
    bill = create_supplier_bill(
        db_session,
        SupplierBillCreate(
            status=SupplierBillStatus.POSTED,
            vendor_id=supplier.id,
            bill_date=date(2026, 6, 20),
            due_date=date(2026, 7, 20),
            lines=[
                SupplierBillLineCreate(
                    description="Small bill",
                    quantity=Decimal("1"),
                    unit_price=Decimal("100.00"),
                    expense_account_id=account_id(db_session, "5100"),
                )
            ],
        ),
    )

    with pytest.raises(ValueError, match="Allocation exceeds amount due"):
        create_supplier_payment(
            db_session,
            SupplierPaymentCreate(
                vendor_id=supplier.id,
                payment_date=date(2026, 6, 25),
                amount=Decimal("101.00"),
                bank_account_id=account_id(db_session, "1010"),
                allocations=[SupplierPaymentAllocationCreate(bill_id=bill.id, amount=Decimal("101.00"))],
            ),
        )


def test_accounts_payable_ageing_reports_unpaid_posted_bills(db_session) -> None:
    supplier = vendor(db_session)
    current_bill = create_supplier_bill(
        db_session,
        SupplierBillCreate(
            status=SupplierBillStatus.POSTED,
            vendor_id=supplier.id,
            bill_date=date(2026, 6, 20),
            due_date=date(2026, 7, 20),
            lines=[
                SupplierBillLineCreate(
                    description="Current bill",
                    quantity=Decimal("1"),
                    unit_price=Decimal("300.00"),
                    expense_account_id=account_id(db_session, "5100"),
                )
            ],
        ),
    )
    create_supplier_bill(
        db_session,
        SupplierBillCreate(
            status=SupplierBillStatus.POSTED,
            vendor_id=supplier.id,
            bill_date=date(2026, 4, 1),
            due_date=date(2026, 4, 15),
            lines=[
                SupplierBillLineCreate(
                    description="Older bill",
                    quantity=Decimal("1"),
                    unit_price=Decimal("500.00"),
                    expense_account_id=account_id(db_session, "5200"),
                )
            ],
        ),
    )
    create_supplier_payment(
        db_session,
        SupplierPaymentCreate(
            vendor_id=supplier.id,
            payment_date=date(2026, 7, 1),
            amount=Decimal("100.00"),
            bank_account_id=account_id(db_session, "1010"),
            allocations=[SupplierPaymentAllocationCreate(bill_id=current_bill.id, amount=Decimal("100.00"))],
        ),
    )

    report = accounts_payable_ageing(db_session, as_of=date(2026, 7, 20))
    row = report.rows[0]

    assert row.vendor_name == supplier.name
    assert row.current == Decimal("200.00")
    assert row.days_over_90 == Decimal("500.00")
    assert row.total == Decimal("700.00")
    assert report.total == Decimal("700.00")
