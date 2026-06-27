from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from bookkeeping_app.accounting import seed_default_accounts
from bookkeeping_app.database import Base
from bookkeeping_app.models import Account, ContactType, SalesInvoiceStatus, TransactionKind, TransactionStatus
from bookkeeping_app.operations import (
    create_contact,
    create_operational_transaction,
    create_project,
    create_sales_invoice,
    project_profitability,
)
from bookkeeping_app.schemas import (
    ContactCreate,
    OperationalTransactionCreate,
    ProjectCreate,
    SalesInvoiceCreate,
    SalesInvoiceLineCreate,
)


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


def test_project_profitability_links_contract_revenue_costs_and_documents(db_session) -> None:
    client = create_contact(db_session, ContactCreate(name="Acme AI", type=ContactType.CUSTOMER))
    project = create_project(
        db_session,
        ProjectCreate(
            project_code="ACME-AUTO-001",
            name="Invoice automation rollout",
            client_id=client.id,
            service_type="ai_automation",
            billing_model="milestone",
            contract_value=Decimal("5000.00"),
            start_date=date(2026, 6, 1),
        ),
    )
    invoice = create_sales_invoice(
        db_session,
        SalesInvoiceCreate(
            status=SalesInvoiceStatus.ISSUED,
            customer_id=client.id,
            project_id=project.id,
            issue_date=date(2026, 6, 15),
            due_date=date(2026, 7, 15),
            lines=[
                SalesInvoiceLineCreate(
                    description="Milestone 1",
                    quantity=Decimal("1"),
                    unit_price=Decimal("2000.00"),
                    tax_amount=Decimal("180.00"),
                    revenue_account_id=account_id(db_session, "4100"),
                )
            ],
        ),
    )
    create_operational_transaction(
        db_session,
        OperationalTransactionCreate(
            kind=TransactionKind.EXPENSE,
            status=TransactionStatus.POSTED,
            transaction_date=date(2026, 6, 16),
            description="Contractor implementation support",
            amount=Decimal("650.00"),
            contact_id=None,
            project_id=project.id,
            debit_account_id=account_id(db_session, "5200"),
            credit_account_id=account_id(db_session, "1010"),
            receipt={
                "filename": "contractor-receipt.txt",
                "content_type": "text/plain",
                "content_base64": "UmVjZWlwdA==",
            },
        ),
    )

    report = project_profitability(db_session)
    row = report.rows[0]

    assert invoice.project_id == project.id
    assert row.project.project_code == "ACME-AUTO-001"
    assert row.contract_value == Decimal("5000.00")
    assert row.invoiced_total == Decimal("2180.00")
    assert row.revenue_recognized == Decimal("2000.00")
    assert row.direct_costs == Decimal("650.00")
    assert row.gross_profit == Decimal("1350.00")
    assert row.gross_margin == Decimal("0.6750")
    assert row.receipts_count == 1
    assert report.gross_profit == Decimal("1350.00")


def test_project_must_match_sales_invoice_customer(db_session) -> None:
    first_client = create_contact(db_session, ContactCreate(name="First Client", type=ContactType.CUSTOMER))
    second_client = create_contact(db_session, ContactCreate(name="Second Client", type=ContactType.CUSTOMER))
    project = create_project(
        db_session,
        ProjectCreate(
            project_code="FIRST-001",
            name="First project",
            client_id=first_client.id,
            contract_value=Decimal("1000.00"),
        ),
    )

    with pytest.raises(ValueError, match="Project client must match"):
        create_sales_invoice(
            db_session,
            SalesInvoiceCreate(
                status=SalesInvoiceStatus.ISSUED,
                customer_id=second_client.id,
                project_id=project.id,
                issue_date=date(2026, 6, 15),
                due_date=date(2026, 7, 15),
                lines=[
                    SalesInvoiceLineCreate(
                        description="Wrong client",
                        quantity=Decimal("1"),
                        unit_price=Decimal("1000.00"),
                        revenue_account_id=account_id(db_session, "4100"),
                    )
                ],
            ),
        )
