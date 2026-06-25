# Developer Handoff Notes

## Quick Start

From the project root:

```powershell
.\start-app.cmd
```

This starts:

- Backend API: `http://127.0.0.1:8000`
- Frontend dashboard: `http://127.0.0.1:5173`

Stop both with Ctrl+C in the same terminal.

## Manual Run Commands

Backend:

```powershell
.venv\Scripts\python.exe -m uvicorn bookkeeping_app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd dashboard
npm.cmd run dev
```

## Verification

Backend tests:

```powershell
.venv\Scripts\python.exe -m pytest -q
```

Frontend build:

```powershell
cd dashboard
npm.cmd run build
```

In this Codex sandbox, Vite/esbuild may need elevated execution because it can fail with an `Access is denied` error while loading `vite.config.ts`.

## Current User Workflows

### Income Or Expense

1. Go to Finance.
2. Choose Expense or Income.
3. Fill date, description, contact, reference, accounts, amount, and optional receipt.
4. Save as Posted to affect ledger and reports, or Draft/Reviewed to keep it in the operational queue.
5. For receipt-backed transactions, click Extract to run optional receipt OCR and review extracted merchant, total, and line items.

Paid sales order deposits also appear in Finance as posted `deposit` records. They are created from the Sales tab rather than entered directly in the transaction form.

### Employee Setup

1. Go to HR & Payroll.
2. Add employee details.
3. Set current monthly salary.
4. Choose CPF profile:
   - SC / 3rd-year PR, 55 and below.
   - Custom rates.
   - Not applicable.

### Purchase Orders

1. Go to Purchasing.
2. Create a vendor in Vendor Master and set Vendor Qualification to Qualified.
3. Select the vendor, issue date, expected delivery date, PO payment terms, and line items.
4. Save as Draft to prepare the PO, or Issued to commit it to a qualified vendor.
5. Existing draft POs can be issued from the Purchase Orders list if the vendor is qualified.

Purchase orders do not post to the ledger yet. They are procurement commitments only until a supplier invoice or bill workflow is added. Vendor contacts can store default payment terms, but the PO-level payment terms are the actual terms from the accepted proposal or quote.

### Client Purchase Orders

1. Go to Sales.
2. Create a customer in Customer Master.
3. Enter the client's PO number, customer, received date, expected delivery date, terms, and revenue line items.
4. Set the upfront deposit if required. The Sales form supports no deposit, 5%, 10%, and custom deposit amounts, plus due date and status.
5. Save as Draft, Received, or Accepted.
6. Existing draft or received client POs can be accepted from the Client Purchase Orders list.

Client purchase orders are stored as sales orders. Deposits marked Paid post one linked deposit operational transaction to debit `1010` Bank Account and credit `2150` Deferred Revenue. Requested or Invoiced deposits remain commercial status only.

Sales invoices are the formal Accounts Receivable workflow. Issued invoices post `Dr 1100 Accounts Receivable`, credit the selected revenue accounts, and credit `2200 GST Output Tax` when line tax is present. Customer receipts post `Dr bank/cash, Cr Accounts Receivable` and must be allocated to issued invoices. Add deposit application and deferred revenue release before treating sales order deposits as earned revenue.

### Payroll

1. Go to HR & Payroll.
2. Select an employee, or use Manual entry.
3. Review salary, CPF subject wage, CPF rates, accounts, and dates.
4. Save as Posted to create the accounting journal entry.
5. Click Payslip to preview and print the itemised pay slip.

### Reports

Reports read posted journal entries only. Draft transactions and draft payroll runs do not affect balances.

Paid sales order deposits affect Cash/Bank and Deferred Revenue on the Balance Sheet. They do not affect Profit & Loss until a future revenue release workflow is added.

### Chart Of Accounts Setup

1. Go to Settings.
2. Use Chart of Accounts Setup to download a template, export the current chart, import CSV changes, or print the chart.
3. Use Add Only to import additional account codes without changing existing codes.
4. Use Setup Replace only during initial setup; it can replace the full chart from CSV and is blocked after accounts are used by transactions, documents, payroll, contacts, or journal lines.

The Dashboard chart is read-only by design.

## API Endpoints

Useful local docs:

```text
http://127.0.0.1:8000/docs
```

Core endpoints:

- `GET /health`
- `GET /accounts`
- `POST /accounts`
- `GET /company-settings`
- `PUT /company-settings`
- `GET /contacts`
- `POST /contacts`
- `GET /employees`
- `POST /employees`
- `GET /purchase-orders`
- `POST /purchase-orders`
- `POST /purchase-orders/{purchase_order_id}/issue`
- `POST /purchase-orders/{purchase_order_id}/cancel`
- `GET /sales-orders`
- `POST /sales-orders`
- `POST /sales-orders/{sales_order_id}/accept`
- `POST /sales-orders/{sales_order_id}/cancel`
- `GET /sales-invoices`
- `POST /sales-invoices`
- `POST /sales-invoices/{invoice_id}/issue`
- `GET /customer-receipts`
- `POST /customer-receipts`
- `GET /transactions`
- `POST /transactions`
- `POST /transactions/{transaction_id}/post`
- `POST /receipts/{receipt_id}/extract`
- `GET /payroll`
- `POST /payroll`
- `POST /payroll/{payroll_id}/post`
- `GET /journal-entries`
- `POST /journal-entries`
- `GET /summary`
- `GET /reports/profit-and-loss`
- `GET /reports/balance-sheet`

## Important Implementation Notes

- The app currently uses SQLAlchemy `create_all`, not Alembic migrations.
- The frontend is organized by business domain: Dashboard, Finance, Sales, Purchasing, HR & Payroll, Reports, and Settings. Keep master records in their domain modules instead of placing operational setup in Settings.
- `apply_local_schema_updates` exists for small SQLite-compatible patches on existing local databases.
- When adding required columns to existing tables, either make them nullable/defaulted or add a local schema update.
- Payroll uses stored payroll values, not live employee values, after a payroll run is created. This is important so old payroll runs remain stable after an employee salary changes.
- Employee salary history is not implemented. Add it before relying on this for long-term payroll history.
- The payroll form can still be used in manual mode if the employee is not in HR & Payroll's Employee Master section.
- Payslip printing is frontend-only print CSS; there is no generated PDF file yet.
- Vendor qualification is stored on contacts. PO issuance is blocked unless the contact is a vendor or both-type contact with `qualified` status.
- Purchase orders currently do not create journal entries. Add PO receiving and supplier invoice processing before treating POs as accounting events.
- Sales orders do not create revenue journal entries by themselves. Issued sales invoices create revenue and Accounts Receivable journal entries. Paid sales order deposits do create posted operational transactions and journal entries against Deferred Revenue. Deposit application to invoices/milestones and deferred revenue release are not implemented yet.
- `post_unposted_paid_sales_order_deposits` runs on startup to backfill paid sales order deposits that do not yet have a linked transaction.
- Receipt extraction uses local Tesseract plus local Ollama by default. Set `TESSERACT_CMD`, `OLLAMA_BASE_URL`, and `OLLAMA_RECEIPT_MODEL` in `.env` if defaults do not match the machine.
- Plain Tesseract extraction is available with `RECEIPT_EXTRACTION_PROVIDER=tesseract`.
- OpenAI extraction is optional. Set `RECEIPT_EXTRACTION_PROVIDER=openai`, `OPENAI_API_KEY`, and optionally `RECEIPT_EXTRACTION_MODEL` in `.env` before backend startup.
- Receipt extraction stores review data in `receipt_extractions` and `receipt_line_items`; it does not mutate the original receipt file or auto-update transaction amounts.

## Suggested Next Work

- Add employee editing.
- Add salary history with effective dates.
- Add payroll adjustments: bonus, allowance, reimbursement, unpaid leave, other deductions.
- Add CPF rule engine by age, citizenship/PR year, Ordinary Wage ceiling, Additional Wage ceiling, and wage bands.
- Add Skills Development Levy and self-help group contributions.
- Add CPF payable payment workflow.
- Add PO receiving, supplier invoice matching, and PO-to-bill posting into Accounts Payable.
- Add sales order fulfillment, deposit application, milestone billing automation, and invoice document export into Accounts Receivable.
- Add printable/exportable PO documents for vendor issuance.
- Add PDF payslip export and document storage.
- Add PDF receipt extraction and a correction/approval workflow for extracted line items.
- Add database migrations before the schema grows much more.
- Split `dashboard/src/main.tsx` into smaller components once the UI stabilizes.
