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
.venv\Scripts\python.exe -m alembic upgrade head
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

### Bank Reconciliation

1. Go to Finance.
2. Add bank statement lines for the selected bank/cash account.
3. Select a candidate journal entry whose signed movement on that same bank account matches the statement line.
4. Click Reconcile to link the statement line to the existing ledger entry.
5. Use Unreconcile if the link was made in error.

Bank reconciliation does not create accounting entries. It links external bank statement evidence to existing posted journal entries and rejects mismatched bank-account movement.

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

Purchase orders do not post to the ledger. They are procurement commitments until a supplier bill is received and posted. Vendor contacts can store default payment terms, but the PO-level payment terms are the actual terms from the accepted proposal or quote.

### Supplier Bills

1. Go to Purchasing.
2. Select a vendor and optionally link a purchase order and project.
3. Enter the supplier bill dates, supplier reference, payment terms, and cost lines.
4. Save as Draft to review later, or Posted to create the Accounts Payable journal immediately.
5. Existing draft supplier bills can be posted from the Supplier Bills list.

Posted supplier bills create `Dr selected cost/asset accounts`, `Dr 2210 GST Input Tax` when tax is present, and `Cr 2000 Accounts Payable` for the bill total. If linked to a project, the supplier bill subtotal is included in project direct costs. Recoverable GST is not treated as project cost.

### Supplier Payments

1. Go to Purchasing.
2. Select a vendor with open posted supplier bills.
3. Choose payment date, bank account, reference, and bill allocations.
4. Save as Draft for later review, or Posted to reduce Accounts Payable immediately.
5. Existing draft supplier payments can be posted from the Supplier Payments list.

Posted supplier payments create `Dr 2000 Accounts Payable` and `Cr selected bank/cash asset account`. Allocations cannot exceed the unpaid amount on posted supplier bills.

### Approval Requests

1. Draft supplier bills and supplier payments can be submitted for approval from Purchasing.
2. Pending requests appear in the Dashboard approval queue.
3. Approve or reject the request from the queue.
4. Once a document is in the approval workflow, posting is blocked while the latest request is pending or rejected.
5. If rejected, submit a new request and approve it before posting.

This is the first approval-control slice. It is intentionally generic (`document_type`, `document_id`, `action`) so later approval policies can cover invoices, payroll, journals, bank reconciliation overrides, and period-sensitive actions.

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

Dashboard A/P ageing reads posted supplier bills and posted supplier payment allocations. Draft supplier bills and draft supplier payments do not affect ageing or ledger balances.

The Reports tab also includes an Audit Trail panel. Current audit events cover approval requests/decisions, supplier bill/payment postings, and bank reconciliation/reversal actions.

### Chart Of Accounts Setup

1. Go to Settings.
2. Use Chart of Accounts Setup to download a template, export the current chart, import CSV changes, or print the chart.
3. Use Add Only to import additional account codes without changing existing codes.
4. Use Setup Replace only during initial setup; it can replace the full chart from CSV and is blocked after accounts are used by transactions, documents, payroll, contacts, or journal lines.

The Dashboard chart is read-only by design.

### Backup Export

1. Go to Settings.
2. Click Backup Export.
3. The app downloads a timestamped ZIP containing `manifest.json`, `README.txt`, and JSON snapshots of all database tables.

The export is read-only and does not mutate records. It is intended for backup, accountant review, and handoff; direct re-import is not implemented.

## API Endpoints

Useful local docs:

```text
http://127.0.0.1:8000/docs
```

Core endpoints:

- `GET /health`
- `GET /accounts`
- `POST /accounts`
- `GET /exports/backup.zip`
- `GET /company-settings`
- `PUT /company-settings`
- `GET /contacts`
- `POST /contacts`
- `GET /projects`
- `POST /projects`
- `GET /employees`
- `POST /employees`
- `GET /purchase-orders`
- `POST /purchase-orders`
- `POST /purchase-orders/{purchase_order_id}/issue`
- `POST /purchase-orders/{purchase_order_id}/cancel`
- `GET /supplier-bills`
- `POST /supplier-bills`
- `POST /supplier-bills/{bill_id}/post`
- `GET /supplier-payments`
- `POST /supplier-payments`
- `POST /supplier-payments/{payment_id}/post`
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
- `GET /bank-statement-lines`
- `POST /bank-statement-lines`
- `POST /bank-statement-lines/{line_id}/reconcile`
- `POST /bank-statement-lines/{line_id}/unreconcile`
- `GET /approval-requests`
- `POST /approval-requests`
- `POST /approval-requests/{request_id}/approve`
- `POST /approval-requests/{request_id}/reject`
- `GET /audit-events`
- `GET /payroll`
- `POST /payroll`
- `POST /payroll/{payroll_id}/post`
- `GET /journal-entries`
- `POST /journal-entries`
- `POST /journal-entries/{entry_id}/reverse`
- `GET /summary`
- `GET /reports/profit-and-loss`
- `GET /reports/balance-sheet`
- `GET /reports/project-profitability`
- `GET /reports/accounts-payable-ageing`
- `GET /reports/bank-reconciliation`

## Important Implementation Notes

- Alembic is now configured under `migrations/`. Run `.venv\Scripts\python.exe -m alembic upgrade head` before backend startup when applying schema changes.
- The app still uses SQLAlchemy `create_all` on startup for local-first convenience, but new schema work should be captured in Alembic revisions.
- Posted journal entries and lines are protected by a SQLAlchemy `before_flush` guard. Do not update or delete posted ledger rows directly; create a reversal or adjustment entry.
- `reverse_journal_entry` creates a new balanced journal entry with debit and credit lines swapped from the original.
- Posting services have a narrow internal allowance for the one flush that attaches a newly created journal entry to its source record. Avoid reusing that allowance outside posting code.
- Posted operational transactions, posted payroll accounting fields, issued sales invoice lines, posted customer receipt allocations, posted supplier bill accounting fields/lines, and posted supplier payment accounting fields/allocations are protected from silent edits.
- Projects are engagement records linked to customer contacts. `project_id` can be attached to sales orders, sales invoices, deposits, income, and expense transactions.
- Supplier bills are source records for Accounts Payable. Posting creates balanced journal entries through backend accounting services; the frontend never writes ledger entries directly.
- Supplier payments are source records for AP settlement. Posting creates balanced journal entries through backend accounting services and payment allocations are validated against unpaid bill balances.
- Bank statement lines are reconciliation evidence, not accounting records. Reconciliation links a statement line to one journal entry only when the journal entry has an equal signed movement on the selected bank/cash account.
- Approval requests are generic workflow records. The current guard applies to supplier bill and supplier payment posting once a request exists for that document/action.
- Audit events are append-only control evidence for workflow events. They currently store entity type/id, action, actor, summary, JSON details, and timestamp.
- Backup export uses SQLAlchemy table metadata to produce JSON snapshots for every current table in a ZIP bundle.
- Supplier bill tax uses `2210 GST Input Tax`. The default chart includes that account, and migration `20260627_0003` inserts it for existing local charts when absent.
- Project profitability reports contract value, issued invoice totals, invoice subtotal revenue, posted direct expense transactions, posted supplier bill subtotals, gross profit, margin, and receipt-backed cost count.
- The current project profitability report is source-record backed, with revenue/costs tied to records that post through the ledger. Add journal-line project dimensions later if manual journals need project attribution.
- The frontend is organized by business domain: Dashboard, Finance, Sales, Purchasing, HR & Payroll, Reports, and Settings. Keep master records in their domain modules instead of placing operational setup in Settings.
- `apply_local_schema_updates` exists for small SQLite-compatible patches on existing local databases.
- When adding required columns to existing tables, either make them nullable/defaulted or add a local schema update.
- Payroll uses stored payroll values, not live employee values, after a payroll run is created. This is important so old payroll runs remain stable after an employee salary changes.
- Employee salary history is not implemented. Add it before relying on this for long-term payroll history.
- The payroll form can still be used in manual mode if the employee is not in HR & Payroll's Employee Master section.
- Payslip printing is frontend-only print CSS; there is no generated PDF file yet.
- Vendor qualification is stored on contacts. PO issuance is blocked unless the contact is a vendor or both-type contact with `qualified` status.
- Purchase orders currently do not create journal entries. Supplier bills are the first Accounts Payable source document workflow; add receiving and three-way matching before treating PO fulfilment as controlled.
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
- Add PO receiving and supplier invoice matching.
- Add CSV import and suggested matching for bank reconciliation.
- Add approval policies, thresholds, roles, and required approver rules.
- Broaden audit coverage to all create/update/void/reversal workflows and include before/after field diffs where useful.
- Add restore/import tooling and signed export checksums after the backup format stabilizes.
- Add sales order fulfillment, deposit application, milestone billing automation, and invoice document export into Accounts Receivable.
- Add formal void/reversal workflows for sales invoices, customer receipts, payroll runs, and operational transactions.
- Add accounting periods and period-lock checks before broadening posting workflows.
- Add document-link tables so contracts, invoices, receipts, and delivery evidence can attach to projects beyond receipt-backed operational transactions.
- Add printable/exportable PO documents for vendor issuance.
- Add PDF payslip export and document storage.
- Add PDF receipt extraction and a correction/approval workflow for extracted line items.
- Replace remaining local schema patch hooks with explicit Alembic migrations as the schema stabilizes.
- Split `dashboard/src/main.tsx` into smaller components once the UI stabilizes.
