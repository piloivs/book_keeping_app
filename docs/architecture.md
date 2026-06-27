# IntelliArtAI Operations Core Architecture

## Purpose

This is a local-first bookkeeping and SME operations-core prototype for IntelliArtAI. It is designed for a single local user and stores data in SQLite by default.

The bookkeeping ledger is the trusted financial spine of the app. Business modules such as Sales, Purchasing, HR & Payroll, Documents, Reports, and future AI-assisted workflows should create operational records in their own domains, then post financial effects through backend accounting/posting services.

## Stack

- Backend: FastAPI, SQLAlchemy, Pydantic.
- Database: SQLite at `data/warehouse/bookkeeping.sqlite3`.
- Frontend: React, TypeScript, Vite.
- Tests: pytest for backend accounting, sales, purchasing, controls, and payroll behavior.

## Main Modules

- `src/bookkeeping_app/main.py`: FastAPI app, route definitions, startup initialization.
- `src/bookkeeping_app/models.py`: SQLAlchemy tables and enums.
- `src/bookkeeping_app/schemas.py`: API request and response models.
- `src/bookkeeping_app/accounting.py`: chart of accounts, journal entry creation, balances.
- `src/bookkeeping_app/operations.py`: business operations for contacts, employees, transactions, payroll, reports.
- `dashboard/src/main.tsx`: React app and all current dashboard views.
- `dashboard/src/lib/api.ts`: frontend API client and TypeScript data types.

## Startup Flow

When the backend starts:

1. Alembic migrations should be applied with `.venv\Scripts\python.exe -m alembic upgrade head` before startup after pulling schema changes.
2. `Base.metadata.create_all(bind=engine)` creates missing SQLite tables for local-first convenience.
3. `apply_local_schema_updates(db)` applies small local SQLite schema patches that `create_all` cannot apply to existing tables.
4. `seed_default_accounts(db)` inserts missing default accounts.
5. `seed_company_settings(db)` inserts default company settings if needed.
6. `post_unposted_paid_sales_order_deposits(db)` backfills paid sales order deposits that were saved before a deposit transaction was created.

The local `start-app.cmd` wrapper launches `start-app.ps1`, which starts both backend and frontend dev servers.

## Data Model

Core bookkeeping:

- `Account`: chart of accounts.
- `JournalEntry`: balanced accounting entry header.
- `JournalLine`: debit and credit lines.
- `OperationalTransaction`: expense, income, or paid deposit capture that can post into a journal entry.
- `Project`: IntelliArtAI client engagement record with service type, billing model, contract value, and lifecycle status.
- `Receipt`: local receipt metadata, with files stored under `data/raw/receipts/`.
- `ReceiptExtraction`: AI-extracted receipt header fields, status, confidence, raw text, and provider metadata.
- `ReceiptLineItem`: extracted receipt line descriptions, quantities, prices, amounts, and confidence.
- `PurchaseOrder`: purchasing commitment issued to a vendor, including the PO-specific payment terms from the accepted proposal or quote. It does not post to the ledger by itself.
- `PurchaseOrderLine`: item or service lines with quantity, unit price, tax amount, and expense account.
- `SalesOrder`: inbound client purchase order captured from a customer, including the client's PO reference, internal sales order number, terms, deposit requirements, and acceptance status. Paid deposits post to the ledger through a linked operational deposit transaction.
- `SalesOrderLine`: customer order lines with quantity, unit price, tax amount, and revenue account.
- `SalesInvoice`: formal customer invoice with issue date, due date, status, customer, optional linked sales order, journal entry, and payment status.
- `SalesInvoiceLine`: invoice line items with quantity, unit price, tax amount, and revenue account.
- `CustomerReceipt`: customer payment receipt posted to bank/cash and Accounts Receivable.
- `CustomerReceiptAllocation`: allocation of a customer receipt to one or more sales invoices.
- `SupplierBill`: vendor invoice or bill posted to Accounts Payable.
- `SupplierBillLine`: bill line items with quantity, unit price, tax amount, and expense or asset account.
- `SupplierPayment`: vendor payment posted against Accounts Payable.
- `SupplierPaymentAllocation`: allocation of a supplier payment to one or more posted supplier bills.
- `BankStatementLine`: external bank statement evidence reconciled to existing journal entries.
- `ApprovalRequest`: generic workflow request for controlled document actions.
- `AuditEvent`: append-only control event record for important workflow actions.

Company and contacts:

- `CompanySettings`: company name, registration number, fiscal year start, base currency.
- `Contact`: customer/vendor records for transactions, including vendor qualification status and optional default payment terms.

HR and payroll:

- `Employee`: employee master record with current monthly salary and CPF profile.
- `PayrollRun`: salary run for a pay period. It can optionally link to an `Employee`.

Reports:

- Profit and Loss uses revenue and expense account balances.
- Balance Sheet uses asset, liability, equity balances plus retained earnings from current P&L.
- Project Profitability uses project-linked source records that post through the ledger.
- A/P ageing uses posted supplier bills and posted supplier payment allocations.
- Bank Reconciliation compares statement evidence to posted journal entries for selected bank/cash accounts.

## Default Accounts

Defined in `src/bookkeeping_app/accounting.py`.

- `1000` Cash
- `1010` Bank Account
- `1100` Accounts Receivable
- `2000` Accounts Payable
- `2100` CPF Payable
- `2150` Deferred Revenue
- `2200` GST Output Tax
- `2210` GST Input Tax
- `3000` Owner Equity
- `3900` Retained Earnings
- `4000` Sales Revenue
- `4100` Consulting Revenue
- `5000` Office Supplies
- `5100` Software Expense
- `5200` Professional Fees
- `5300` Salaries and Wages
- `5310` Employer CPF Expense

## Posting Logic

Operational transaction posting creates a two-line journal entry:

- Expense: debit expense account, credit cash/bank or accounts payable.
- Income: debit cash/bank or receivable account, credit revenue account.
- Deposit: debit cash/bank or receivable account, credit liability account.

Payroll posting creates a balanced journal entry:

- Debit `5300` Salaries and Wages for gross salary.
- Debit `5310` Employer CPF Expense for employer CPF.
- Credit `1010` Bank Account for net salary paid.
- Credit `2100` CPF Payable for employee CPF plus employer CPF.

Zero-value CPF lines are omitted so payroll with no CPF still posts cleanly.

Purchase orders are non-posting procurement records. A PO can be drafted for a vendor contact, but issuing requires the vendor qualification status to be `qualified`. The current implementation records the purchasing commitment only; supplier bills and supplier payments create the Accounts Payable accounting entries.

Supplier bills are Accounts Payable source records. Draft bills do not post. Posted bills create a balanced journal entry that debits selected line cost/asset accounts, debits `2210` GST Input Tax when tax is present, and credits `2000` Accounts Payable for the bill total. Posted supplier bill accounting fields and lines are immutable through the ORM guard.

Supplier payments settle posted supplier bills. Draft payments do not post. Posted payments debit `2000` Accounts Payable and credit the selected bank/cash asset account. Allocations are validated against posted bills for the same vendor and cannot exceed unpaid bill balances.

Sales orders are client PO records. They can be created for customer or both-type contacts, accepted from draft/received status, and cancelled while still open. Deposit fields record whether an upfront 5%, 10%, or custom deposit is required, due, requested, invoiced, paid, or applied. Deposits marked Paid create one linked posted operational deposit transaction that debits `1010` Bank Account and credits `2150` Deferred Revenue. Invoice creation, deposit application, and earned revenue recognition should later create the remaining accounting entries from a sales order.

Sales invoices are formal Accounts Receivable records. Draft invoices do not post. Issued invoices create a balanced journal entry that debits `1100` Accounts Receivable, credits the invoice line revenue accounts, and credits `2200` GST Output Tax when invoice line tax is present. Customer receipts post `Dr bank/cash, Cr Accounts Receivable` and must be allocated to issued invoices. Invoice status updates to partially paid or paid based on posted receipt allocations.

Bank reconciliation does not post to the ledger. Statement lines are evidence records and can be reconciled only to an existing journal entry whose signed movement on the same bank/cash account matches the statement line amount.

Approval requests are generic records keyed by document type, document id, and action. The current posting guard applies to supplier bills and supplier payments after a request exists: pending and rejected latest requests block posting, while an approved latest request allows it.

Audit events are append-only records for control evidence. Current coverage includes approval requests and decisions, supplier bill/payment posting, and bank reconciliation/unreconciliation.

Backup export is a read-only ZIP created from SQLAlchemy table metadata. It includes a manifest and JSON snapshots of current database tables for backup, review, and handoff. Direct restore/import is not implemented.

## CPF Handling

The app is not a full CPF compliance engine. It stores editable CPF rates and defaults to the common 2026 full-rate case for Singapore Citizens or third-year-and-above Singapore Permanent Residents age 55 and below:

- Employee CPF: 20%
- Employer CPF: 17%

CPF subject wage defaults to the lower of gross salary and `8000.00`.

Current rounding behavior:

- Employee CPF is rounded down to the nearest dollar.
- Total CPF is rounded to the nearest dollar.
- Employer CPF is total CPF minus employee CPF.

CPF can vary by age, citizenship or PR year, wage band, Ordinary Wage ceiling, Additional Wage ceiling, and other contribution rules. Future work should add a proper CPF rule engine before relying on automated compliance decisions.

## Frontend Views

- Dashboard: read-only operating overview, summary cards, A/R and A/P ageing, approval queue, operational queue, read-only chart of accounts, and recent journal entries.
- Finance: income and expense capture, operational transaction posting, receipt extraction, and bank reconciliation.
- Sales: customer master records, sales invoice creation/issue, customer receipt posting, client purchase order intake, line items, deposit terms/payment status, acceptance/cancellation, and client history.
- Projects: client engagement records and project profitability.
- Purchasing: vendor master records, vendor qualification, purchase order entry, supplier bills, supplier payments, approval requests, and AP posting.
- HR & Payroll: employee master records, salary run capture, employee prefill, CPF preview, payroll posting, and payslip printing.
- Reports: Profit and Loss, Balance Sheet, and Audit Trail.
- Settings: company settings, chart-of-accounts setup, and backup export.

Chart-of-accounts setup is intentionally in Settings rather than Dashboard. The dashboard view should remain observation-first. Add-only and setup-replace CSV imports are guarded by confirmation, imports are validated before posting changes, and setup replacement is blocked after accounts are referenced by transactions, documents, payroll, contacts, or journal lines.

## Receipt Extraction

Receipts remain stored as original local files under `data/raw/receipts/`. Extraction results are stored separately so the original document is not modified.

The extraction endpoint is:

- `POST /receipts/{receipt_id}/extract`

By default, the backend runs local Tesseract OCR and local Ollama structured parsing using `RECEIPT_EXTRACTION_PROVIDER=tesseract_ollama`. Tesseract extracts visible text, then Ollama converts that OCR text into schema-shaped receipt JSON.

Plain Tesseract extraction is available with `RECEIPT_EXTRACTION_PROVIDER=tesseract`. In that mode, local heuristics parse merchant, date, currency, subtotal, tax, total, and line items.

OpenAI extraction is still available by setting `RECEIPT_EXTRACTION_PROVIDER=openai` and `OPENAI_API_KEY`. In that mode, the backend sends image receipts to the configured `RECEIPT_EXTRACTION_MODEL` using the OpenAI Responses API with structured JSON output.

If the configured provider is unavailable, the app records a `not_configured` extraction status with a setup message. Unsupported files or provider errors are recorded as `failed`.

Current limitations:

- Image uploads are supported. PDFs are not processed yet.
- Extracted values are review data only; they do not automatically update transaction amounts.
- There is no correction workflow yet.

## Payslip Printing

Payroll rows expose a `Payslip` action. The modal renders an itemised pay slip and uses print CSS so the browser prints only the payslip area.

The payslip currently includes:

- Employer name.
- Registration number if present.
- Employee name.
- Pay date.
- Salary period.
- Gross/basic salary.
- Employee CPF deduction.
- Net salary paid.
- Employer CPF contribution.
- Total CPF payable.

## Known Limitations

- No user login or role-based permissions.
- Alembic migrations exist, while a small local SQLite schema updater remains for local-first compatibility patches.
- Employee records store current salary only; salary history is not implemented.
- CPF calculation is simplified and editable.
- No bank CSV import, suggested reconciliation matching, CPF export, configurable approval policies, or formal financial statements.
- Receipt upload stores files locally but does not provide UI preview/download yet.
- Receipt extraction does not yet support PDFs or user corrections.
- Purchase orders do not yet support receiving, three-way supplier invoice matching, or PO document export.
- Sales orders do not yet support fulfillment, deposit application, milestone automation, or document export.
- Sales order deposits marked Paid post to Deferred Revenue, but there is not yet a workflow to apply deposits to invoices or release deferred revenue into earned revenue.
