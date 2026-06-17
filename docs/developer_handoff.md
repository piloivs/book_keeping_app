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

1. Go to Transactions.
2. Choose Expense or Income.
3. Fill date, description, contact, reference, accounts, amount, and optional receipt.
4. Save as Posted to affect ledger and reports, or Draft/Reviewed to keep it in the operational queue.
5. For receipt-backed transactions, click Extract to run optional receipt OCR and review extracted merchant, total, and line items.

### Employee Setup

1. Go to Employees.
2. Add employee details.
3. Set current monthly salary.
4. Choose CPF profile:
   - SC / 3rd-year PR, 55 and below.
   - Custom rates.
   - Not applicable.

### Purchase Orders

1. Go to Contacts.
2. Create a vendor or both-type contact and set Vendor Qualification to Qualified.
3. Go to Purchasing.
4. Select the vendor, issue date, expected delivery date, PO payment terms, and line items.
5. Save as Draft to prepare the PO, or Issued to commit it to a qualified vendor.
6. Existing draft POs can be issued from the Purchase Orders list if the vendor is qualified.

Purchase orders do not post to the ledger yet. They are procurement commitments only until a supplier invoice or bill workflow is added. Vendor contacts can store default payment terms, but the PO-level payment terms are the actual terms from the accepted proposal or quote.

### Payroll

1. Go to Payroll.
2. Select an employee, or use Manual entry.
3. Review salary, CPF subject wage, CPF rates, accounts, and dates.
4. Save as Posted to create the accounting journal entry.
5. Click Payslip to preview and print the itemised pay slip.

### Reports

Reports read posted journal entries only. Draft transactions and draft payroll runs do not affect balances.

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
- `apply_local_schema_updates` exists for small SQLite-compatible patches on existing local databases.
- When adding required columns to existing tables, either make them nullable/defaulted or add a local schema update.
- Payroll uses stored payroll values, not live employee values, after a payroll run is created. This is important so old payroll runs remain stable after an employee salary changes.
- Employee salary history is not implemented. Add it before relying on this for long-term payroll history.
- The payroll form can still be used in manual mode if the employee is not in the Employees tab.
- Payslip printing is frontend-only print CSS; there is no generated PDF file yet.
- Vendor qualification is stored on contacts. PO issuance is blocked unless the contact is a vendor or both-type contact with `qualified` status.
- Purchase orders currently do not create journal entries. Add PO receiving and supplier invoice processing before treating POs as accounting events.
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
- Add printable/exportable PO documents for vendor issuance.
- Add PDF payslip export and document storage.
- Add PDF receipt extraction and a correction/approval workflow for extracted line items.
- Add database migrations before the schema grows much more.
- Split `dashboard/src/main.tsx` into smaller components once the UI stabilizes.
