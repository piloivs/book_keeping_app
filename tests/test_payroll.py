from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from bookkeeping_app.accounting import seed_default_accounts
from bookkeeping_app.database import Base
from bookkeeping_app.models import Account, JournalEntry, PayrollStatus
from bookkeeping_app.operations import create_payroll_run
from bookkeeping_app.schemas import PayrollRunCreate


def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    seed_default_accounts(db)
    return db


def account_id(db, code: str) -> int:
    return db.scalar(select(Account.id).where(Account.code == code))


def test_posted_payroll_creates_balanced_salary_and_cpf_entry() -> None:
    db = db_session()
    try:
        payroll = create_payroll_run(
            db,
            PayrollRunCreate(
                status=PayrollStatus.POSTED,
                employee_name="Asha Tan",
                period_start=date(2026, 6, 1),
                period_end=date(2026, 6, 30),
                pay_date=date(2026, 6, 30),
                gross_salary=Decimal("5000.00"),
                salary_account_id=account_id(db, "5300"),
                employer_cpf_account_id=account_id(db, "5310"),
                cash_account_id=account_id(db, "1010"),
                cpf_payable_account_id=account_id(db, "2100"),
            ),
        )

        assert payroll.status == PayrollStatus.POSTED
        assert payroll.employee_cpf == Decimal("1000.00")
        assert payroll.employer_cpf == Decimal("850.00")
        assert payroll.net_pay == Decimal("4000.00")
        assert payroll.journal_entry_id is not None

        entry = db.scalar(select(JournalEntry).where(JournalEntry.id == payroll.journal_entry_id))
        assert entry is not None
        assert sum(line.debit for line in entry.lines) == Decimal("5850.00")
        assert sum(line.credit for line in entry.lines) == Decimal("5850.00")
    finally:
        db.close()
