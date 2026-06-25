import csv
from decimal import Decimal
from io import StringIO

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from .models import (
    Account,
    AccountType,
    Contact,
    CustomerReceipt,
    JournalEntry,
    JournalLine,
    OperationalTransaction,
    PayrollRun,
    PurchaseOrderLine,
    SalesInvoiceLine,
    SalesOrderLine,
)
from .schemas import (
    ChartOfAccountsImportResult,
    ChartOfAccountsValidationIssue,
    ChartOfAccountsValidationResult,
    JournalEntryCreate,
    JournalEntryRead,
    JournalLineRead,
)


DEFAULT_ACCOUNTS = [
    ("1000", "Cash", AccountType.ASSET, "Primary cash account"),
    ("1010", "Bank Account", AccountType.ASSET, "Primary operating bank account"),
    ("1100", "Accounts Receivable", AccountType.ASSET, "Customer balances due"),
    ("2000", "Accounts Payable", AccountType.LIABILITY, "Vendor balances owed"),
    ("2100", "CPF Payable", AccountType.LIABILITY, "CPF contributions payable to CPF Board"),
    ("2150", "Deferred Revenue", AccountType.LIABILITY, "Customer deposits and advance payments"),
    ("2200", "GST Output Tax", AccountType.LIABILITY, "GST collected on customer invoices"),
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

COA_CSV_HEADERS = ["code", "name", "type", "description", "is_active"]

SYSTEM_ACCOUNT_REQUIREMENTS = {
    "1010": (AccountType.ASSET, "Bank Account", "sales deposits and cash receipt posting"),
    "1100": (AccountType.ASSET, "Accounts Receivable", "sales invoices, customer receipts, and A/R ageing"),
    "2150": (AccountType.LIABILITY, "Deferred Revenue", "paid sales order deposits"),
    "2200": (AccountType.LIABILITY, "GST Output Tax", "issued sales invoices with tax"),
}

EXPECTED_CODE_PREFIXES = {
    AccountType.ASSET: ("1",),
    AccountType.LIABILITY: ("2",),
    AccountType.EQUITY: ("3",),
    AccountType.REVENUE: ("4",),
    AccountType.EXPENSE: ("5", "6", "7", "8", "9"),
}


def accounts_to_csv(accounts: list[Account]) -> str:
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=COA_CSV_HEADERS, lineterminator="\n")
    writer.writeheader()
    for account in accounts:
        writer.writerow(
            {
                "code": account.code,
                "name": account.name,
                "type": account.type.value,
                "description": account.description or "",
                "is_active": "true" if account.is_active else "false",
            }
        )
    return output.getvalue()


def default_accounts_csv() -> str:
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=COA_CSV_HEADERS, lineterminator="\n")
    writer.writeheader()
    for code, name, account_type, description in DEFAULT_ACCOUNTS:
        writer.writerow(
            {
                "code": code,
                "name": name,
                "type": account_type.value,
                "description": description,
                "is_active": "true",
            }
        )
    return output.getvalue()


def account_references_exist(db: Session) -> bool:
    checks = [
        select(func.count()).select_from(JournalLine),
        select(func.count()).select_from(OperationalTransaction),
        select(func.count()).select_from(PayrollRun),
        select(func.count()).select_from(PurchaseOrderLine),
        select(func.count()).select_from(SalesOrderLine),
        select(func.count()).select_from(SalesInvoiceLine),
        select(func.count()).select_from(CustomerReceipt),
        select(func.count()).select_from(Contact).where(Contact.default_expense_account_id.is_not(None)),
    ]
    return any(db.scalar(check) for check in checks)


def _parse_bool(value: str | None, *, row_number: int) -> bool:
    if value is None or value.strip() == "":
        return True
    normalized = value.strip().lower()
    if normalized in {"true", "t", "yes", "y", "1", "active"}:
        return True
    if normalized in {"false", "f", "no", "n", "0", "inactive"}:
        return False
    raise ValueError(f"Row {row_number}: is_active must be true or false.")


def _parse_accounts_csv(csv_text: str) -> tuple[list[dict[str, object]], list[str]]:
    reader = csv.DictReader(StringIO(csv_text.lstrip("\ufeff")))
    if reader.fieldnames is None:
        return [], ["CSV must include a header row."]

    normalized_headers = {header.strip().lower() for header in reader.fieldnames if header}
    required = {"code", "name", "type"}
    missing = sorted(required - normalized_headers)
    if missing:
        return [], [f"CSV is missing required columns: {', '.join(missing)}."]

    rows: list[dict[str, object]] = []
    errors: list[str] = []
    seen_codes: set[str] = set()
    for row_number, row in enumerate(reader, start=2):
        normalized = {(key or "").strip().lower(): (value or "").strip() for key, value in row.items()}
        if not any(normalized.values()):
            continue

        code = normalized.get("code", "")
        name = normalized.get("name", "")
        account_type_value = normalized.get("type", "").lower()
        description = normalized.get("description") or None
        if not code:
            errors.append(f"Row {row_number}: code is required.")
        elif len(code) > 20:
            errors.append(f"Row {row_number}: code must be 20 characters or fewer.")
        elif code in seen_codes:
            errors.append(f"Row {row_number}: duplicate code {code}.")
        else:
            seen_codes.add(code)

        if not name:
            errors.append(f"Row {row_number}: name is required.")
        elif len(name) > 120:
            errors.append(f"Row {row_number}: name must be 120 characters or fewer.")

        try:
            account_type = AccountType(account_type_value)
        except ValueError:
            errors.append(f"Row {row_number}: type must be asset, liability, equity, revenue, or expense.")
            account_type = AccountType.EXPENSE

        try:
            is_active = _parse_bool(normalized.get("is_active"), row_number=row_number)
        except ValueError as exc:
            errors.append(str(exc))
            is_active = True

        rows.append(
            {
                "code": code,
                "name": name,
                "type": account_type,
                "description": description,
                "is_active": is_active,
            }
        )
    return rows, errors


def _issue(code: str, message: str) -> ChartOfAccountsValidationIssue:
    return ChartOfAccountsValidationIssue(code=code, message=message)


def _account_from_row(row: dict[str, object]) -> Account:
    return Account(
        code=str(row["code"]),
        name=str(row["name"]),
        type=row["type"],  # type: ignore[arg-type]
        description=row["description"],  # type: ignore[arg-type]
        is_active=bool(row["is_active"]),
    )


def _project_accounts_after_import(db: Session, rows: list[dict[str, object]], *, mode: str) -> list[Account]:
    if mode == "setup_replace":
        return [_account_from_row(row) for row in rows]

    existing = list(db.scalars(select(Account)).all())
    existing_codes = {account.code for account in existing}
    projected = [account for account in existing]
    projected.extend(_account_from_row(row) for row in rows if str(row["code"]) not in existing_codes)
    return projected


def _referenced_account_ids(db: Session) -> set[int]:
    ids: set[int] = set()
    scalar_queries = [
        select(JournalLine.account_id),
        select(OperationalTransaction.debit_account_id),
        select(OperationalTransaction.credit_account_id),
        select(PayrollRun.salary_account_id),
        select(PayrollRun.employer_cpf_account_id),
        select(PayrollRun.cash_account_id),
        select(PayrollRun.cpf_payable_account_id),
        select(PurchaseOrderLine.expense_account_id),
        select(SalesOrderLine.revenue_account_id),
        select(SalesInvoiceLine.revenue_account_id),
        select(CustomerReceipt.bank_account_id),
        select(Contact.default_expense_account_id).where(Contact.default_expense_account_id.is_not(None)),
    ]
    for query in scalar_queries:
        ids.update(value for value in db.scalars(query).all() if value is not None)
    return ids


def validate_chart_of_accounts(db: Session, csv_text: str, *, mode: str) -> ChartOfAccountsValidationResult:
    rows, parse_errors = _parse_accounts_csv(csv_text)
    result = ChartOfAccountsValidationResult(mode=mode, can_import=False, account_count=len(rows))
    result.errors.extend(_issue("csv_format", error) for error in parse_errors)
    if parse_errors:
        return result

    if not rows:
        result.errors.append(_issue("empty_chart", "CSV must contain at least one account."))
        return result

    if mode == "setup_replace" and account_references_exist(db):
        result.errors.append(
            _issue(
                "setup_replace_locked",
                "Setup replacement is only available before accounts are used by transactions, documents, payroll, contacts, or journal lines.",
            )
        )

    projected_accounts = _project_accounts_after_import(db, rows, mode=mode)
    projected_by_code = {account.code: account for account in projected_accounts}
    active_accounts = [account for account in projected_accounts if account.is_active]
    active_types = {account.type for account in active_accounts}

    if not active_accounts:
        result.errors.append(_issue("no_active_accounts", "At least one account must be active."))

    for account_type in AccountType:
        if account_type not in active_types:
            result.warnings.append(_issue("missing_account_type", f"No active {account_type.value} accounts found."))

    for code, (expected_type, label, workflow) in SYSTEM_ACCOUNT_REQUIREMENTS.items():
        account = projected_by_code.get(code)
        if account is None:
            result.errors.append(_issue("missing_system_account", f"Missing {code} {label}; required for {workflow}."))
            continue
        if account.type != expected_type:
            result.errors.append(_issue("system_account_type", f"{code} {label} must be a {expected_type.value} account."))
        if not account.is_active:
            result.errors.append(_issue("inactive_system_account", f"{code} {label} must remain active for {workflow}."))

    referenced_ids = _referenced_account_ids(db)
    if referenced_ids:
        current_accounts = {account.id: account for account in db.scalars(select(Account).where(Account.id.in_(referenced_ids))).all()}
        for account in current_accounts.values():
            if not account.is_active:
                result.errors.append(_issue("inactive_referenced_account", f"{account.code} {account.name} is referenced and cannot be inactive."))

    for account in projected_accounts:
        expected_prefixes = EXPECTED_CODE_PREFIXES.get(account.type, ())
        if account.code and expected_prefixes and not account.code.startswith(expected_prefixes):
            result.warnings.append(
                _issue(
                    "code_range",
                    f"{account.code} {account.name} is typed as {account.type.value}, but its code is outside the usual range.",
                )
            )

        name = account.name.lower()
        sounds_like_revenue = any(term in name for term in ["sales", "revenue", "income"]) and "deferred revenue" not in name and "cost of sales" not in name
        if sounds_like_revenue and account.type != AccountType.REVENUE:
            result.warnings.append(_issue("name_type_mismatch", f"{account.code} {account.name} sounds like revenue but is typed as {account.type.value}."))
        if any(term in name for term in ["expense", "cost", "fee", "salary", "wages"]) and account.type != AccountType.EXPENSE:
            result.warnings.append(_issue("name_type_mismatch", f"{account.code} {account.name} sounds like an expense but is typed as {account.type.value}."))
        if any(term in name for term in ["cash", "bank", "receivable"]) and account.type != AccountType.ASSET:
            result.warnings.append(_issue("name_type_mismatch", f"{account.code} {account.name} sounds like an asset but is typed as {account.type.value}."))
        if any(term in name for term in ["payable", "deferred", "gst output", "cpf payable"]) and account.type != AccountType.LIABILITY:
            result.warnings.append(_issue("name_type_mismatch", f"{account.code} {account.name} sounds like a liability but is typed as {account.type.value}."))
        if "equity" in name and account.type != AccountType.EQUITY:
            result.warnings.append(_issue("name_type_mismatch", f"{account.code} {account.name} sounds like equity but is typed as {account.type.value}."))

    result.info.append(_issue("app_compatibility", "Validation checks app-required account codes, import safety, account type coverage, and common account naming risks."))
    result.info.append(_issue("compliance_scope", "This is an app-compatibility and bookkeeping-structure check, not a GAAP/SFRS compliance certification."))
    result.can_import = not result.errors
    return result


def import_chart_of_accounts(db: Session, csv_text: str, *, mode: str) -> ChartOfAccountsImportResult:
    validation = validate_chart_of_accounts(db, csv_text, mode=mode)
    if validation.errors:
        return ChartOfAccountsImportResult(
            mode=mode,
            created=0,
            updated=0,
            skipped=0,
            errors=[issue.message for issue in validation.errors],
        )

    rows, _errors = _parse_accounts_csv(csv_text)
    existing_by_code = {account.code: account for account in db.scalars(select(Account)).all()}
    created = 0
    updated = 0
    skipped = 0

    if mode == "setup_replace":
        db.query(Account).delete()
        db.flush()
        existing_by_code = {}

    for row in rows:
        existing = existing_by_code.get(str(row["code"]))
        if existing is None:
            db.add(Account(**row))
            created += 1
            continue

        if mode == "add_only":
            skipped += 1
            continue

        existing.name = str(row["name"])
        existing.type = row["type"]  # type: ignore[assignment]
        existing.description = row["description"]  # type: ignore[assignment]
        existing.is_active = bool(row["is_active"])
        updated += 1

    db.commit()
    return ChartOfAccountsImportResult(mode=mode, created=created, updated=updated, skipped=skipped)


def seed_default_accounts(db: Session) -> None:
    if db.scalar(select(func.count()).select_from(Account)):
        return

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
