from decimal import Decimal

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy.orm import Session

from .accounting import (
    accounts_to_csv,
    create_journal_entry,
    default_accounts_csv,
    import_chart_of_accounts,
    list_accounts_with_balances,
    recent_entries,
    seed_default_accounts,
    serialize_entry,
    validate_chart_of_accounts,
)
from .config import get_settings
from .database import Base, SessionLocal, engine, get_db
from .models import Account, AccountType
from .operations import (
    accounts_receivable_ageing,
    balance_sheet,
    apply_local_schema_updates,
    accept_sales_order,
    cancel_purchase_order,
    cancel_sales_order,
    client_history,
    create_customer_receipt,
    create_contact,
    create_employee,
    create_operational_transaction,
    create_payroll_run,
    create_purchase_order,
    create_sales_invoice,
    create_sales_order,
    extract_receipt_details,
    get_company_settings,
    list_contacts,
    list_employees,
    list_operational_transactions,
    list_payroll_runs,
    list_purchase_orders,
    list_customer_receipts,
    list_sales_invoices,
    list_sales_orders,
    post_payroll_run,
    post_unposted_paid_sales_order_deposits,
    post_operational_transaction,
    issue_purchase_order,
    issue_sales_invoice,
    link_sales_invoice_to_sales_order,
    profit_and_loss,
    seed_company_settings,
    update_company_settings,
)
from .schemas import (
    AccountCreate,
    AccountRead,
    AccountsReceivableAgeingReport,
    BalanceSheetReport,
    ChartOfAccountsImport,
    ChartOfAccountsImportResult,
    ChartOfAccountsValidationResult,
    ClientHistoryReport,
    CompanySettingsRead,
    CompanySettingsUpdate,
    ContactCreate,
    ContactRead,
    CustomerReceiptCreate,
    CustomerReceiptRead,
    DashboardSummary,
    EmployeeCreate,
    EmployeeRead,
    JournalEntryCreate,
    JournalEntryRead,
    OperationalTransactionCreate,
    OperationalTransactionRead,
    PayrollRunCreate,
    PayrollRunRead,
    ProfitAndLossReport,
    PurchaseOrderCreate,
    PurchaseOrderRead,
    ReceiptExtractionRead,
    SalesInvoiceCreate,
    SalesInvoiceLinkSalesOrder,
    SalesInvoiceRead,
    SalesOrderCreate,
    SalesOrderRead,
)

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
        apply_local_schema_updates(db)
        seed_default_accounts(db)
        seed_company_settings(db)
        post_unposted_paid_sales_order_deposits(db)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/accounts", response_model=list[AccountRead])
def get_accounts(db: Session = Depends(get_db)) -> list[AccountRead]:
    return [
        AccountRead.model_validate(account).model_copy(update={"balance": balance})
        for account, balance in list_accounts_with_balances(db)
    ]


@app.get("/accounts/template.csv")
def get_accounts_template() -> Response:
    return Response(
        content=default_accounts_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="chart-of-accounts-template.csv"'},
    )


@app.get("/accounts/export.csv")
def get_accounts_export(db: Session = Depends(get_db)) -> Response:
    accounts = [account for account, _balance in list_accounts_with_balances(db)]
    return Response(
        content=accounts_to_csv(accounts),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="chart-of-accounts.csv"'},
    )


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


@app.post("/accounts/import", response_model=ChartOfAccountsImportResult)
def post_accounts_import(payload: ChartOfAccountsImport, db: Session = Depends(get_db)) -> ChartOfAccountsImportResult:
    result = import_chart_of_accounts(db, payload.csv_text, mode=payload.mode)
    if result.errors:
        raise HTTPException(status_code=400, detail=result.errors)
    return result


@app.post("/accounts/validate", response_model=ChartOfAccountsValidationResult)
def post_accounts_validate(payload: ChartOfAccountsImport, db: Session = Depends(get_db)) -> ChartOfAccountsValidationResult:
    return validate_chart_of_accounts(db, payload.csv_text, mode=payload.mode)


@app.get("/company-settings", response_model=CompanySettingsRead)
def get_settings_endpoint(db: Session = Depends(get_db)) -> CompanySettingsRead:
    return get_company_settings(db)


@app.put("/company-settings", response_model=CompanySettingsRead)
def put_settings_endpoint(payload: CompanySettingsUpdate, db: Session = Depends(get_db)) -> CompanySettingsRead:
    return update_company_settings(db, payload)


@app.get("/contacts", response_model=list[ContactRead])
def get_contacts(db: Session = Depends(get_db)) -> list[ContactRead]:
    return list_contacts(db)


@app.post("/contacts", response_model=ContactRead, status_code=201)
def post_contact(payload: ContactCreate, db: Session = Depends(get_db)) -> ContactRead:
    return create_contact(db, payload)


@app.get("/employees", response_model=list[EmployeeRead])
def get_employees(db: Session = Depends(get_db)) -> list[EmployeeRead]:
    return list_employees(db)


@app.post("/employees", response_model=EmployeeRead, status_code=201)
def post_employee(payload: EmployeeCreate, db: Session = Depends(get_db)) -> EmployeeRead:
    try:
        return create_employee(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/transactions", response_model=list[OperationalTransactionRead])
def get_transactions(limit: int = 50, db: Session = Depends(get_db)) -> list[OperationalTransactionRead]:
    return list_operational_transactions(db, limit=limit)


@app.post("/transactions", response_model=OperationalTransactionRead, status_code=201)
def post_transaction(payload: OperationalTransactionCreate, db: Session = Depends(get_db)) -> OperationalTransactionRead:
    try:
        return create_operational_transaction(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/transactions/{transaction_id}/post", response_model=OperationalTransactionRead)
def post_transaction_to_ledger(transaction_id: int, db: Session = Depends(get_db)) -> OperationalTransactionRead:
    try:
        return post_operational_transaction(db, transaction_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/receipts/{receipt_id}/extract", response_model=ReceiptExtractionRead)
def post_receipt_extraction(receipt_id: int, db: Session = Depends(get_db)) -> ReceiptExtractionRead:
    try:
        return extract_receipt_details(db, receipt_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/payroll", response_model=list[PayrollRunRead])
def get_payroll(limit: int = 50, db: Session = Depends(get_db)) -> list[PayrollRunRead]:
    return list_payroll_runs(db, limit=limit)


@app.post("/payroll", response_model=PayrollRunRead, status_code=201)
def post_payroll(payload: PayrollRunCreate, db: Session = Depends(get_db)) -> PayrollRunRead:
    try:
        return create_payroll_run(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/payroll/{payroll_id}/post", response_model=PayrollRunRead)
def post_payroll_to_ledger(payroll_id: int, db: Session = Depends(get_db)) -> PayrollRunRead:
    try:
        return post_payroll_run(db, payroll_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/purchase-orders", response_model=list[PurchaseOrderRead])
def get_purchase_orders(limit: int = 50, db: Session = Depends(get_db)) -> list[PurchaseOrderRead]:
    return list_purchase_orders(db, limit=limit)


@app.post("/purchase-orders", response_model=PurchaseOrderRead, status_code=201)
def post_purchase_order(payload: PurchaseOrderCreate, db: Session = Depends(get_db)) -> PurchaseOrderRead:
    try:
        return create_purchase_order(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/purchase-orders/{purchase_order_id}/issue", response_model=PurchaseOrderRead)
def post_purchase_order_issue(purchase_order_id: int, db: Session = Depends(get_db)) -> PurchaseOrderRead:
    try:
        return issue_purchase_order(db, purchase_order_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/purchase-orders/{purchase_order_id}/cancel", response_model=PurchaseOrderRead)
def post_purchase_order_cancel(purchase_order_id: int, db: Session = Depends(get_db)) -> PurchaseOrderRead:
    try:
        return cancel_purchase_order(db, purchase_order_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/sales-orders", response_model=list[SalesOrderRead])
def get_sales_orders(limit: int = 50, db: Session = Depends(get_db)) -> list[SalesOrderRead]:
    return list_sales_orders(db, limit=limit)


@app.post("/sales-orders", response_model=SalesOrderRead, status_code=201)
def post_sales_order(payload: SalesOrderCreate, db: Session = Depends(get_db)) -> SalesOrderRead:
    try:
        return create_sales_order(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/sales-orders/{sales_order_id}/accept", response_model=SalesOrderRead)
def post_sales_order_accept(sales_order_id: int, db: Session = Depends(get_db)) -> SalesOrderRead:
    try:
        return accept_sales_order(db, sales_order_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/sales-orders/{sales_order_id}/cancel", response_model=SalesOrderRead)
def post_sales_order_cancel(sales_order_id: int, db: Session = Depends(get_db)) -> SalesOrderRead:
    try:
        return cancel_sales_order(db, sales_order_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/sales-invoices", response_model=list[SalesInvoiceRead])
def get_sales_invoices(limit: int = 50, db: Session = Depends(get_db)) -> list[SalesInvoiceRead]:
    return list_sales_invoices(db, limit=limit)


@app.post("/sales-invoices", response_model=SalesInvoiceRead, status_code=201)
def post_sales_invoice(payload: SalesInvoiceCreate, db: Session = Depends(get_db)) -> SalesInvoiceRead:
    try:
        return create_sales_invoice(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/sales-invoices/{invoice_id}/issue", response_model=SalesInvoiceRead)
def post_sales_invoice_issue(invoice_id: int, db: Session = Depends(get_db)) -> SalesInvoiceRead:
    try:
        return issue_sales_invoice(db, invoice_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/sales-invoices/{invoice_id}/link-sales-order", response_model=SalesInvoiceRead)
def post_sales_invoice_link_sales_order(
    invoice_id: int,
    payload: SalesInvoiceLinkSalesOrder,
    db: Session = Depends(get_db),
) -> SalesInvoiceRead:
    try:
        return link_sales_invoice_to_sales_order(db, invoice_id, payload.sales_order_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/customer-receipts", response_model=list[CustomerReceiptRead])
def get_customer_receipts(limit: int = 50, db: Session = Depends(get_db)) -> list[CustomerReceiptRead]:
    return list_customer_receipts(db, limit=limit)


@app.post("/customer-receipts", response_model=CustomerReceiptRead, status_code=201)
def post_customer_receipt(payload: CustomerReceiptCreate, db: Session = Depends(get_db)) -> CustomerReceiptRead:
    try:
        return create_customer_receipt(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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


@app.get("/reports/profit-and-loss", response_model=ProfitAndLossReport)
def get_profit_and_loss(db: Session = Depends(get_db)) -> ProfitAndLossReport:
    return profit_and_loss(db)


@app.get("/reports/balance-sheet", response_model=BalanceSheetReport)
def get_balance_sheet(db: Session = Depends(get_db)) -> BalanceSheetReport:
    return balance_sheet(db)


@app.get("/reports/client-history", response_model=ClientHistoryReport)
def get_client_history(db: Session = Depends(get_db)) -> ClientHistoryReport:
    return client_history(db)


@app.get("/reports/accounts-receivable-ageing", response_model=AccountsReceivableAgeingReport)
def get_accounts_receivable_ageing(db: Session = Depends(get_db)) -> AccountsReceivableAgeingReport:
    return accounts_receivable_ageing(db)
