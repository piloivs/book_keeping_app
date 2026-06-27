from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from bookkeeping_app.accounting import create_journal_entry, reverse_journal_entry, seed_default_accounts
from bookkeeping_app.database import Base
from bookkeeping_app.models import Account, JournalLine
from bookkeeping_app.schemas import JournalEntryCreate


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


def test_journal_entry_must_balance() -> None:
    with pytest.raises(ValidationError):
        JournalEntryCreate(
            entry_date=date(2026, 6, 14),
            memo="Unbalanced entry",
            lines=[
                {"account_id": 1, "debit": Decimal("10.00")},
                {"account_id": 2, "credit": Decimal("9.99")},
            ],
        )


def test_journal_line_cannot_have_both_debit_and_credit() -> None:
    with pytest.raises(ValidationError):
        JournalEntryCreate(
            entry_date=date(2026, 6, 14),
            memo="Invalid line",
            lines=[
                {"account_id": 1, "debit": Decimal("10.00"), "credit": Decimal("10.00")},
                {"account_id": 2, "credit": Decimal("10.00")},
            ],
        )


def test_posted_journal_entry_cannot_be_silently_edited(db_session) -> None:
    entry = create_journal_entry(
        db_session,
        JournalEntryCreate(
            entry_date=date(2026, 6, 14),
            memo="Owner contribution",
            lines=[
                {"account_id": account_id(db_session, "1010"), "debit": Decimal("500.00")},
                {"account_id": account_id(db_session, "3000"), "credit": Decimal("500.00")},
            ],
        ),
    )

    entry.memo = "Edited memo"

    with pytest.raises(ValueError, match="immutable"):
        db_session.commit()


def test_posted_journal_line_cannot_be_silently_edited(db_session) -> None:
    entry = create_journal_entry(
        db_session,
        JournalEntryCreate(
            entry_date=date(2026, 6, 14),
            memo="Owner contribution",
            lines=[
                {"account_id": account_id(db_session, "1010"), "debit": Decimal("500.00")},
                {"account_id": account_id(db_session, "3000"), "credit": Decimal("500.00")},
            ],
        ),
    )
    line = db_session.scalars(select(JournalLine).where(JournalLine.journal_entry_id == entry.id)).first()
    line.debit = Decimal("600.00")

    with pytest.raises(ValueError, match="immutable"):
        db_session.commit()


def test_posted_journal_entry_can_be_reversed(db_session) -> None:
    entry = create_journal_entry(
        db_session,
        JournalEntryCreate(
            entry_date=date(2026, 6, 14),
            memo="Owner contribution",
            lines=[
                {"account_id": account_id(db_session, "1010"), "debit": Decimal("500.00")},
                {"account_id": account_id(db_session, "3000"), "credit": Decimal("500.00")},
            ],
        ),
    )

    reversal = reverse_journal_entry(db_session, entry.id, reversal_date=date(2026, 6, 15))
    lines = db_session.scalars(select(JournalLine).where(JournalLine.journal_entry_id == reversal.id)).all()

    assert reversal.reference == f"REV-{entry.id}"
    assert sum(line.debit for line in lines) == Decimal("500.00")
    assert sum(line.credit for line in lines) == Decimal("500.00")
    assert any(line.credit == Decimal("500.00") and line.account_id == account_id(db_session, "1010") for line in lines)
    assert any(line.debit == Decimal("500.00") and line.account_id == account_id(db_session, "3000") for line in lines)
