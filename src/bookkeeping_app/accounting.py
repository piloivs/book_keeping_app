from decimal import Decimal

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from .models import Account, AccountType, JournalEntry, JournalLine
from .schemas import JournalEntryCreate, JournalEntryRead, JournalLineRead


DEFAULT_ACCOUNTS = [
    ("1000", "Cash", AccountType.ASSET, "Primary cash account"),
    ("1010", "Bank Account", AccountType.ASSET, "Primary operating bank account"),
    ("1100", "Accounts Receivable", AccountType.ASSET, "Customer balances due"),
    ("2000", "Accounts Payable", AccountType.LIABILITY, "Vendor balances owed"),
    ("2100", "CPF Payable", AccountType.LIABILITY, "CPF contributions payable to CPF Board"),
    ("3000", "Owner Equity", AccountType.EQUITY, "Owner investment and retained earnings"),
    ("3900", "Retained Earnings", AccountType.EQUITY, "Accumulated prior-year earnings"),
    ("4000", "Sales Revenue", AccountType.REVENUE, "Income from sales"),
    ("4100", "Consulting Revenue", AccountType.REVENUE, "Consulting and project income"),
    ("5000", "Office Supplies", AccountType.EXPENSE, "Office supplies and consumables"),
    ("5100", "Software Expense", AccountType.EXPENSE, "Software subscriptions and tools"),
    ("5200", "Professional Fees", AccountType.EXPENSE, "Corporate secretary, accounting, and legal fees"),
    ("5300", "Salaries and Wages", AccountType.EXPENSE, "Gross staff salaries and wages"),
    ("5310", "Employer CPF Expense", AccountType.EXPENSE, "Employer CPF contributions"),
]


def seed_default_accounts(db: Session) -> None:
    existing_codes = set(db.scalars(select(Account.code)).all())
    for code, name, account_type, description in DEFAULT_ACCOUNTS:
        if code not in existing_codes:
            db.add(Account(code=code, name=name, type=account_type, description=description))
    db.commit()


def account_balance_expression() -> object:
    debit_total = func.coalesce(func.sum(JournalLine.debit), 0)
    credit_total = func.coalesce(func.sum(JournalLine.credit), 0)
    return debit_total - credit_total


def normal_balance(account: Account, raw_balance: Decimal) -> Decimal:
    if account.type in {AccountType.LIABILITY, AccountType.EQUITY, AccountType.REVENUE}:
        return raw_balance * Decimal("-1")
    return raw_balance


def list_accounts_with_balances(db: Session) -> list[tuple[Account, Decimal]]:
    balance_expr = account_balance_expression()
    rows = db.execute(
        select(Account, balance_expr)
        .outerjoin(JournalLine, JournalLine.account_id == Account.id)
        .group_by(Account.id)
        .order_by(Account.code)
    ).all()
    return [(account, normal_balance(account, Decimal(balance or 0))) for account, balance in rows]


def create_journal_entry(db: Session, payload: JournalEntryCreate, *, commit: bool = True) -> JournalEntry:
    account_ids = {line.account_id for line in payload.lines}
    found_ids = set(db.scalars(select(Account.id).where(Account.id.in_(account_ids))).all())
    missing_ids = account_ids - found_ids
    if missing_ids:
        raise ValueError(f"Unknown account ids: {sorted(missing_ids)}")

    entry = JournalEntry(
        entry_date=payload.entry_date,
        memo=payload.memo,
        reference=payload.reference,
        lines=[
            JournalLine(
                account_id=line.account_id,
                debit=line.debit,
                credit=line.credit,
                description=line.description,
            )
            for line in payload.lines
        ],
    )
    db.add(entry)
    if commit:
        db.commit()
    else:
        db.flush()
    db.refresh(entry)
    return entry


def entry_query() -> Select[tuple[JournalEntry]]:
    return select(JournalEntry).options(selectinload(JournalEntry.lines).selectinload(JournalLine.account))


def serialize_entry(entry: JournalEntry) -> JournalEntryRead:
    return JournalEntryRead(
        id=entry.id,
        entry_date=entry.entry_date,
        memo=entry.memo,
        reference=entry.reference,
        created_at=entry.created_at,
        lines=[
            JournalLineRead(
                id=line.id,
                account_id=line.account_id,
                account_code=line.account.code,
                account_name=line.account.name,
                debit=line.debit,
                credit=line.credit,
                description=line.description,
            )
            for line in entry.lines
        ],
    )


def recent_entries(db: Session, limit: int = 10) -> list[JournalEntryRead]:
    entries = db.scalars(entry_query().order_by(JournalEntry.entry_date.desc(), JournalEntry.id.desc()).limit(limit)).all()
    return [serialize_entry(entry) for entry in entries]
