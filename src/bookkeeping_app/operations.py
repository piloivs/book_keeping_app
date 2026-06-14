import base64
import binascii
import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .accounting import create_journal_entry, list_accounts_with_balances
from .models import (
    Account,
    AccountType,
    CompanySettings,
    Contact,
    Receipt,
    TransactionKind,
    TransactionStatus,
    OperationalTransaction,
)
from .schemas import (
    AccountRead,
    BalanceSheetReport,
    CompanySettingsUpdate,
    ContactCreate,
    JournalEntryCreate,
    OperationalTransactionCreate,
    ProfitAndLossReport,
    ReceiptPayload,
)

RECEIPT_DIR = Path("data/raw/receipts")


def seed_company_settings(db: Session) -> None:
    if db.scalar(select(CompanySettings).limit(1)):
        return
    db.add(
        CompanySettings(
            company_name="IntelliArtAI",
            fiscal_year_start_month=1,
            base_currency="SGD",
        )
    )
    db.commit()


def get_company_settings(db: Session) -> CompanySettings:
    settings = db.scalar(select(CompanySettings).order_by(CompanySettings.id).limit(1))
    if settings is None:
        seed_company_settings(db)
        settings = db.scalar(select(CompanySettings).order_by(CompanySettings.id).limit(1))
    if settings is None:
        raise RuntimeError("Unable to initialize company settings.")
    return settings


def update_company_settings(db: Session, payload: CompanySettingsUpdate) -> CompanySettings:
    settings = get_company_settings(db)
    for key, value in payload.model_dump().items():
        setattr(settings, key, value)
    db.commit()
    db.refresh(settings)
    return settings


def create_contact(db: Session, payload: ContactCreate) -> Contact:
    contact = Contact(**payload.model_dump())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


def list_contacts(db: Session) -> list[Contact]:
    return list(db.scalars(select(Contact).order_by(Contact.name)).all())


def _safe_filename(filename: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9._-]+", "_", filename).strip("._")
    return clean or "receipt"


def save_receipt(payload: ReceiptPayload) -> Receipt:
    try:
        content = base64.b64decode(payload.content_base64, validate=True)
    except binascii.Error as exc:
        raise ValueError("Receipt content must be valid base64.") from exc
    if not content:
        raise ValueError("Receipt file cannot be empty.")
    if len(content) > 10 * 1024 * 1024:
        raise ValueError("Receipt file cannot exceed 10 MB.")

    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid4().hex}_{_safe_filename(payload.filename)}"
    stored_path = RECEIPT_DIR / stored_name
    stored_path.write_bytes(content)
    return Receipt(
        original_filename=payload.filename,
        stored_path=stored_path.as_posix(),
        content_type=payload.content_type,
        size_bytes=len(content),
    )


def _get_account(db: Session, account_id: int) -> Account:
    account = db.get(Account, account_id)
    if account is None:
        raise ValueError(f"Unknown account id: {account_id}")
    return account


def _validate_operational_accounts(kind: TransactionKind, debit_account: Account, credit_account: Account) -> None:
    if kind == TransactionKind.EXPENSE:
        if debit_account.type != AccountType.EXPENSE:
            raise ValueError("Expense transactions must debit an expense account.")
        if credit_account.type not in {AccountType.ASSET, AccountType.LIABILITY}:
            raise ValueError("Expense transactions must credit cash/bank or accounts payable.")
    if kind == TransactionKind.INCOME:
        if debit_account.type != AccountType.ASSET:
            raise ValueError("Income transactions must debit cash/bank or accounts receivable.")
        if credit_account.type != AccountType.REVENUE:
            raise ValueError("Income transactions must credit a revenue account.")


def create_operational_transaction(db: Session, payload: OperationalTransactionCreate) -> OperationalTransaction:
    debit_account = _get_account(db, payload.debit_account_id)
    credit_account = _get_account(db, payload.credit_account_id)
    _validate_operational_accounts(payload.kind, debit_account, credit_account)

    if payload.contact_id is not None and db.get(Contact, payload.contact_id) is None:
        raise ValueError(f"Unknown contact id: {payload.contact_id}")

    receipt = save_receipt(payload.receipt) if payload.receipt else None
    transaction = OperationalTransaction(
        kind=payload.kind,
        status=payload.status,
        transaction_date=payload.transaction_date,
        description=payload.description,
        reference=payload.reference,
        amount=payload.amount,
        contact_id=payload.contact_id,
        debit_account_id=payload.debit_account_id,
        credit_account_id=payload.credit_account_id,
        receipt=receipt,
    )
    db.add(transaction)
    db.flush()

    if transaction.status == TransactionStatus.POSTED:
        _post_operational_transaction(db, transaction)

    db.commit()
    return get_operational_transaction(db, transaction.id)


def _post_operational_transaction(db: Session, transaction: OperationalTransaction) -> None:
    entry = create_journal_entry(
        db,
        JournalEntryCreate(
            entry_date=transaction.transaction_date,
            memo=transaction.description,
            reference=transaction.reference,
            lines=[
                {
                    "account_id": transaction.debit_account_id,
                    "debit": transaction.amount,
                    "description": transaction.description,
                },
                {
                    "account_id": transaction.credit_account_id,
                    "credit": transaction.amount,
                    "description": transaction.description,
                },
            ],
        ),
        commit=False,
    )
    transaction.journal_entry_id = entry.id
    transaction.status = TransactionStatus.POSTED
    transaction.posted_at = datetime.now(UTC)


def post_operational_transaction(db: Session, transaction_id: int) -> OperationalTransaction:
    transaction = db.get(OperationalTransaction, transaction_id)
    if transaction is None:
        raise ValueError(f"Unknown transaction id: {transaction_id}")
    if transaction.status == TransactionStatus.POSTED:
        return get_operational_transaction(db, transaction.id)
    _post_operational_transaction(db, transaction)
    db.commit()
    return get_operational_transaction(db, transaction.id)


def get_operational_transaction(db: Session, transaction_id: int) -> OperationalTransaction:
    transaction = db.scalar(
        transaction_query().where(OperationalTransaction.id == transaction_id)
    )
    if transaction is None:
        raise ValueError(f"Unknown transaction id: {transaction_id}")
    return transaction


def transaction_query():
    return select(OperationalTransaction).options(
        selectinload(OperationalTransaction.contact),
        selectinload(OperationalTransaction.debit_account),
        selectinload(OperationalTransaction.credit_account),
        selectinload(OperationalTransaction.receipt),
    )


def list_operational_transactions(db: Session, limit: int = 50) -> list[OperationalTransaction]:
    return list(
        db.scalars(
            transaction_query().order_by(
                OperationalTransaction.transaction_date.desc(),
                OperationalTransaction.id.desc(),
            ).limit(limit)
        ).all()
    )


def account_read(account: Account, balance) -> AccountRead:
    return AccountRead.model_validate(account).model_copy(update={"balance": balance})


def profit_and_loss(db: Session) -> ProfitAndLossReport:
    accounts = list_accounts_with_balances(db)
    revenue_accounts = [(account, balance) for account, balance in accounts if account.type == AccountType.REVENUE]
    expense_accounts = [(account, balance) for account, balance in accounts if account.type == AccountType.EXPENSE]
    revenue = sum(balance for _, balance in revenue_accounts)
    expenses = sum(balance for _, balance in expense_accounts)
    return ProfitAndLossReport(
        revenue=revenue,
        expenses=expenses,
        net_income=revenue - expenses,
        revenue_accounts=[account_read(account, balance) for account, balance in revenue_accounts],
        expense_accounts=[account_read(account, balance) for account, balance in expense_accounts],
    )


def balance_sheet(db: Session) -> BalanceSheetReport:
    accounts = list_accounts_with_balances(db)
    pnl = profit_and_loss(db)
    asset_accounts = [(account, balance) for account, balance in accounts if account.type == AccountType.ASSET]
    liability_accounts = [(account, balance) for account, balance in accounts if account.type == AccountType.LIABILITY]
    equity_accounts = [(account, balance) for account, balance in accounts if account.type == AccountType.EQUITY]
    assets = sum(balance for _, balance in asset_accounts)
    liabilities = sum(balance for _, balance in liability_accounts)
    equity = sum(balance for _, balance in equity_accounts)
    retained_earnings = pnl.net_income
    return BalanceSheetReport(
        assets=assets,
        liabilities=liabilities,
        equity=equity,
        retained_earnings=retained_earnings,
        total_liabilities_and_equity=liabilities + equity + retained_earnings,
        asset_accounts=[account_read(account, balance) for account, balance in asset_accounts],
        liability_accounts=[account_read(account, balance) for account, balance in liability_accounts],
        equity_accounts=[account_read(account, balance) for account, balance in equity_accounts],
    )
