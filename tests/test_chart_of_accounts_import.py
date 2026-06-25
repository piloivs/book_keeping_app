from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from bookkeeping_app.accounting import create_journal_entry, default_accounts_csv, import_chart_of_accounts, seed_default_accounts, validate_chart_of_accounts
from bookkeeping_app.database import Base
from bookkeeping_app.models import Account
from bookkeeping_app.schemas import JournalEntryCreate


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    seed_default_accounts(db)
    return db


def account_id(db, code: str) -> int:
    return db.scalar(select(Account.id).where(Account.code == code))


def test_add_only_import_creates_new_accounts_and_skips_existing() -> None:
    db = make_session()
    csv_text = """code,name,type,description,is_active
1010,Main Bank,asset,Existing account should not change,true
6100,Marketing Expense,expense,Campaigns and ads,true
"""

    result = import_chart_of_accounts(db, csv_text, mode="add_only")

    assert result.errors == []
    assert result.created == 1
    assert result.skipped == 1
    existing = db.scalar(select(Account).where(Account.code == "1010"))
    created = db.scalar(select(Account).where(Account.code == "6100"))
    assert existing.name == "Bank Account"
    assert created.name == "Marketing Expense"


def test_setup_replace_replaces_accounts_before_use() -> None:
    db = make_session()
    csv_text = """code,name,type,description,is_active
1000,Operating Cash,asset,Cash on hand,true
1010,Operating Bank,asset,Bank,true
1100,Trade Receivables,asset,A/R,true
2150,Customer Deposits,liability,Deposits,true
2200,GST Output Tax,liability,GST,true
3000,Owner Equity,equity,Equity,true
4000,Service Revenue,revenue,Primary revenue,true
5000,Office Expense,expense,Expense,true
"""

    result = import_chart_of_accounts(db, csv_text, mode="setup_replace")

    assert result.errors == []
    assert result.created == 8
    assert db.scalars(select(Account.code).order_by(Account.code)).all() == ["1000", "1010", "1100", "2150", "2200", "3000", "4000", "5000"]


def test_default_seed_does_not_append_accounts_to_custom_chart() -> None:
    db = make_session()
    csv_text = """code,name,type,description,is_active
1010,Operating Bank,asset,Bank,true
1100,Trade Receivables,asset,A/R,true
2150,Customer Deposits,liability,Deposits,true
2200,GST Output Tax,liability,GST,true
3000,Owner Equity,equity,Equity,true
7000,Custom Expense,expense,Custom chart,true
8000,Custom Revenue,revenue,Custom chart,true
"""

    import_chart_of_accounts(db, csv_text, mode="setup_replace")
    seed_default_accounts(db)

    assert db.scalars(select(Account.code).order_by(Account.code)).all() == ["1010", "1100", "2150", "2200", "3000", "7000", "8000"]


def test_setup_replace_is_blocked_after_ledger_usage() -> None:
    db = make_session()
    create_journal_entry(
        db,
        JournalEntryCreate(
            entry_date=date(2026, 1, 1),
            memo="Opening activity",
            lines=[
                {"account_id": account_id(db, "1010"), "debit": Decimal("100.00")},
                {"account_id": account_id(db, "3000"), "credit": Decimal("100.00")},
            ],
        ),
    )
    csv_text = """code,name,type,description,is_active
1000,Operating Cash,asset,Cash on hand,true
"""

    result = import_chart_of_accounts(db, csv_text, mode="setup_replace")

    assert result.created == 0
    assert result.errors
    assert db.scalar(select(Account).where(Account.code == "1010")) is not None


def test_import_reports_csv_validation_errors() -> None:
    db = make_session()
    csv_text = """code,name,type,description,is_active
1000,,wrong,Invalid row,maybe
"""

    result = import_chart_of_accounts(db, csv_text, mode="add_only")

    assert result.created == 0
    assert len(result.errors) == 3


def test_validation_passes_default_template_with_compliance_scope_note() -> None:
    db = make_session()

    result = validate_chart_of_accounts(db, default_accounts_csv(), mode="setup_replace")

    assert result.can_import is True
    assert result.errors == []
    assert any(issue.code == "compliance_scope" for issue in result.info)


def test_validation_blocks_missing_system_account() -> None:
    db = make_session()
    csv_text = """code,name,type,description,is_active
1000,Cash,asset,Cash on hand,true
4000,Sales Revenue,revenue,Sales,true
5000,Office Expense,expense,Expense,true
"""

    result = validate_chart_of_accounts(db, csv_text, mode="setup_replace")

    assert result.can_import is False
    assert any(issue.code == "missing_system_account" and "1100" in issue.message for issue in result.errors)


def test_validation_warns_on_name_type_mismatch() -> None:
    db = make_session()
    csv_text = """code,name,type,description,is_active
1010,Bank Account,asset,Bank,true
1100,Accounts Receivable,asset,A/R,true
2150,Deferred Revenue,liability,Deposits,true
2200,GST Output Tax,liability,GST,true
3000,Owner Equity,equity,Equity,true
4000,Sales Revenue,asset,Wrong type,true
5000,Office Expense,expense,Expense,true
"""

    result = validate_chart_of_accounts(db, csv_text, mode="setup_replace")

    assert result.can_import is True
    assert any(issue.code == "name_type_mismatch" and "Sales Revenue" in issue.message for issue in result.warnings)
