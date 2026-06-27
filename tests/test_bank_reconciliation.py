from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from bookkeeping_app.accounting import create_journal_entry, seed_default_accounts
from bookkeeping_app.database import Base
from bookkeeping_app.models import Account, BankStatementLineStatus
from bookkeeping_app.operations import (
    bank_reconciliation_summary,
    create_bank_statement_line,
    reconcile_bank_statement_line,
    unreconcile_bank_statement_line,
)
from bookkeeping_app.schemas import BankStatementLineCreate, JournalEntryCreate


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


def test_bank_statement_line_reconciles_to_matching_bank_journal_entry(db_session) -> None:
    entry = create_journal_entry(
        db_session,
        JournalEntryCreate(
            entry_date=date(2026, 6, 25),
            memo="Customer receipt",
            reference="BANK-001",
            lines=[
                {"account_id": account_id(db_session, "1010"), "debit": Decimal("250.00")},
                {"account_id": account_id(db_session, "1100"), "credit": Decimal("250.00")},
            ],
        ),
    )
    line = create_bank_statement_line(
        db_session,
        BankStatementLineCreate(
            bank_account_id=account_id(db_session, "1010"),
            statement_date=date(2026, 6, 25),
            description="Incoming transfer",
            reference="BANK-001",
            amount=Decimal("250.00"),
        ),
    )

    reconciled = reconcile_bank_statement_line(db_session, line.id, entry.id)

    assert reconciled.status == BankStatementLineStatus.RECONCILED
    assert reconciled.journal_entry_id == entry.id
    assert reconciled.reconciled_at is not None


def test_bank_reconciliation_rejects_mismatched_bank_amount(db_session) -> None:
    entry = create_journal_entry(
        db_session,
        JournalEntryCreate(
            entry_date=date(2026, 6, 25),
            memo="Supplier payment",
            reference="BANK-002",
            lines=[
                {"account_id": account_id(db_session, "2000"), "debit": Decimal("125.00")},
                {"account_id": account_id(db_session, "1010"), "credit": Decimal("125.00")},
            ],
        ),
    )
    line = create_bank_statement_line(
        db_session,
        BankStatementLineCreate(
            bank_account_id=account_id(db_session, "1010"),
            statement_date=date(2026, 6, 25),
            description="Outgoing transfer",
            reference="BANK-002",
            amount=Decimal("-124.00"),
        ),
    )

    with pytest.raises(ValueError, match="must match"):
        reconcile_bank_statement_line(db_session, line.id, entry.id)


def test_bank_reconciliation_summary_tracks_unmatched_and_reconciled_totals(db_session) -> None:
    entry = create_journal_entry(
        db_session,
        JournalEntryCreate(
            entry_date=date(2026, 6, 25),
            memo="Supplier payment",
            reference="BANK-003",
            lines=[
                {"account_id": account_id(db_session, "2000"), "debit": Decimal("75.00")},
                {"account_id": account_id(db_session, "1010"), "credit": Decimal("75.00")},
            ],
        ),
    )
    first_line = create_bank_statement_line(
        db_session,
        BankStatementLineCreate(
            bank_account_id=account_id(db_session, "1010"),
            statement_date=date(2026, 6, 25),
            description="Outgoing transfer",
            reference="BANK-003",
            amount=Decimal("-75.00"),
        ),
    )
    create_bank_statement_line(
        db_session,
        BankStatementLineCreate(
            bank_account_id=account_id(db_session, "1010"),
            statement_date=date(2026, 6, 26),
            description="Unmatched fee",
            amount=Decimal("-5.00"),
        ),
    )

    reconcile_bank_statement_line(db_session, first_line.id, entry.id)
    summary = bank_reconciliation_summary(db_session, bank_account_id=account_id(db_session, "1010"))

    assert summary.statement_total == Decimal("-80.00")
    assert summary.reconciled_total == Decimal("-75.00")
    assert summary.unreconciled_total == Decimal("-5.00")
    assert summary.unmatched_count == 1
    assert summary.reconciled_count == 1


def test_bank_statement_line_can_be_unreconciled(db_session) -> None:
    entry = create_journal_entry(
        db_session,
        JournalEntryCreate(
            entry_date=date(2026, 6, 25),
            memo="Customer receipt",
            lines=[
                {"account_id": account_id(db_session, "1010"), "debit": Decimal("50.00")},
                {"account_id": account_id(db_session, "1100"), "credit": Decimal("50.00")},
            ],
        ),
    )
    line = create_bank_statement_line(
        db_session,
        BankStatementLineCreate(
            bank_account_id=account_id(db_session, "1010"),
            statement_date=date(2026, 6, 25),
            description="Incoming transfer",
            amount=Decimal("50.00"),
        ),
    )
    reconcile_bank_statement_line(db_session, line.id, entry.id)

    unreconciled = unreconcile_bank_statement_line(db_session, line.id)

    assert unreconciled.status == BankStatementLineStatus.UNMATCHED
    assert unreconciled.journal_entry_id is None
    assert unreconciled.reconciled_at is None
