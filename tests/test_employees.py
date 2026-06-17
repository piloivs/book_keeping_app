from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from bookkeeping_app.accounting import seed_default_accounts
from bookkeeping_app.database import Base
from bookkeeping_app.models import Account, EmployeeStatus, PayrollStatus
from bookkeeping_app.operations import create_employee, create_payroll_run
from bookkeeping_app.schemas import EmployeeCreate, PayrollRunCreate


def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    seed_default_accounts(db)
    return db


def account_id(db, code: str) -> int:
    return db.scalar(select(Account.id).where(Account.code == code))


def test_employee_can_prefill_linked_payroll_run() -> None:
    db = db_session()
    try:
        employee = create_employee(
            db,
            EmployeeCreate(
                staff_id="IA-001",
                name="Test Employee",
                status=EmployeeStatus.ACTIVE,
                monthly_salary=Decimal("3200.00"),
            ),
        )

        payroll = create_payroll_run(
            db,
            PayrollRunCreate(
                status=PayrollStatus.DRAFT,
                employee_id=employee.id,
                employee_name=employee.name,
                period_start=date(2026, 6, 1),
                period_end=date(2026, 6, 30),
                pay_date=date(2026, 6, 30),
                gross_salary=employee.monthly_salary,
                employee_cpf_rate=employee.employee_cpf_rate,
                employer_cpf_rate=employee.employer_cpf_rate,
                salary_account_id=account_id(db, "5300"),
                employer_cpf_account_id=account_id(db, "5310"),
                cash_account_id=account_id(db, "1010"),
                cpf_payable_account_id=account_id(db, "2100"),
            ),
        )

        assert payroll.employee_id == employee.id
        assert payroll.employee.name == "Test Employee"
        assert payroll.employee_cpf == Decimal("640.00")
        assert payroll.employer_cpf == Decimal("544.00")
        assert payroll.net_pay == Decimal("2560.00")
    finally:
        db.close()
