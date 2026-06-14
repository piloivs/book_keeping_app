from decimal import Decimal

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .accounting import (
    create_journal_entry,
    list_accounts_with_balances,
    recent_entries,
    seed_default_accounts,
    serialize_entry,
)
from .config import get_settings
from .database import Base, SessionLocal, engine, get_db
from .models import Account, AccountType
from .schemas import AccountCreate, AccountRead, DashboardSummary, JournalEntryCreate, JournalEntryRead

settings = get_settings()

app = FastAPI(title="Bookkeeping App", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_default_accounts(db)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/accounts", response_model=list[AccountRead])
def get_accounts(db: Session = Depends(get_db)) -> list[AccountRead]:
    return [
        AccountRead.model_validate(account).model_copy(update={"balance": balance})
        for account, balance in list_accounts_with_balances(db)
    ]


@app.post("/accounts", response_model=AccountRead, status_code=201)
def post_account(payload: AccountCreate, db: Session = Depends(get_db)) -> AccountRead:
    account = Account(**payload.model_dump())
    db.add(account)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="Account code must be unique.") from exc
    db.refresh(account)
    return AccountRead.model_validate(account).model_copy(update={"balance": Decimal("0.00")})


@app.get("/journal-entries", response_model=list[JournalEntryRead])
def get_journal_entries(limit: int = 25, db: Session = Depends(get_db)) -> list[JournalEntryRead]:
    return recent_entries(db, limit=limit)


@app.post("/journal-entries", response_model=JournalEntryRead, status_code=201)
def post_journal_entry(payload: JournalEntryCreate, db: Session = Depends(get_db)) -> JournalEntryRead:
    try:
        entry = create_journal_entry(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return serialize_entry(entry)


@app.get("/summary", response_model=DashboardSummary)
def get_summary(db: Session = Depends(get_db)) -> DashboardSummary:
    accounts = list_accounts_with_balances(db)

    def total_for(account_type: AccountType, code: str | None = None) -> Decimal:
        return sum(
            balance
            for account, balance in accounts
            if account.type == account_type and (code is None or account.code == code)
        )

    revenue = total_for(AccountType.REVENUE)
    expenses = total_for(AccountType.EXPENSE)
    return DashboardSummary(
        cash_balance=total_for(AccountType.ASSET, "1000"),
        receivables=total_for(AccountType.ASSET, "1100"),
        payables=total_for(AccountType.LIABILITY, "2000"),
        revenue=revenue,
        expenses=expenses,
        net_income=revenue - expenses,
        recent_entries=recent_entries(db, limit=5),
    )
