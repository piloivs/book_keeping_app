# IntelliArtAI Operations Core

Local-first bookkeeping and SME operations-core prototype built with FastAPI, SQLite, SQLAlchemy, and React.

The general ledger is the trusted financial record underneath the app. Sales, purchasing, HR/payroll, documents, reports, and future AI-assisted workflows should connect through this bookkeeping core rather than bypass it.

## What is included

- Double-entry journal entries with debit/credit validation
- Seeded chart of accounts
- Dashboard summary endpoint
- Account and journal entry APIs
- Receipt upload with optional AI extraction for merchant, totals, and line items
- Client purchase order intake, sales order tracking, and upfront deposits posted to deferred revenue when paid
- Sales invoices that post to Accounts Receivable, revenue, and GST Output Tax when issued
- Customer receipts allocated to invoices and posted to Bank/Cash and Accounts Receivable
- Vendor qualification and purchase order entry/issuance
- Payroll runs with CPF withholding, employer CPF, and printable payslips
- Employee master records for payroll prefill
- React dashboard organized around business modules: Dashboard, Finance, Sales, Purchasing, HR & Payroll, Reports, and Settings
- SQLite by default, with `DATABASE_URL` support for a future PostgreSQL deployment

## Current Module Layout

- Dashboard: read-only operating overview, cash/receivables/payables, A/R ageing, operational queue, read-only chart of accounts, and recent journal entries.
- Finance: income and expense capture, posted operational transactions, and receipt extraction.
- Sales: customer master records, sales invoices, customer receipts, client purchase orders, and client history.
- Purchasing: vendor master records, vendor qualification, and purchase orders.
- HR & Payroll: employee master records, payroll runs, CPF preview, posting, and payslip printing.
- Reports: Profit & Loss and Balance Sheet.
- Settings: company settings and controlled chart-of-accounts setup.

## Run Locally

Start everything with one command:

```powershell
.\start-app.cmd
```

This starts the backend at `http://127.0.0.1:8000` and the frontend at `http://127.0.0.1:5173`. Press Ctrl+C in that terminal to stop both servers.

If you need to install dependencies first, use the manual setup below.

Backend:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m uvicorn bookkeeping_app.main:app --reload
```

Frontend:

```powershell
cd dashboard
npm.cmd install
npm.cmd run dev
```

The frontend expects the API at `http://127.0.0.1:8000`. To change it, create `dashboard/.env.local`:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Receipt extraction uses local Tesseract OCR plus Ollama structured parsing by default. If `tesseract` is not on PATH, add the executable path to `.env` before starting the backend:

```text
RECEIPT_EXTRACTION_PROVIDER=tesseract_ollama
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_RECEIPT_MODEL=qwen3:8b
```

Plain Tesseract extraction is available with `RECEIPT_EXTRACTION_PROVIDER=tesseract`. OpenAI extraction is still available as an optional cloud parser by setting `RECEIPT_EXTRACTION_PROVIDER=openai` and `OPENAI_API_KEY`.

## Data

The prototype stores SQLite data at `data/warehouse/bookkeeping.sqlite3` by default. Raw data belongs in `data/raw/` and should not be edited manually.

## Current Accounting Behavior

- Posted income and expense transactions create balanced journal entries.
- Posted payroll creates salary, CPF payable, and bank journal lines.
- Vendor purchase orders are procurement commitments only and do not post to the ledger yet.
- Client sales orders are operational order records. If a deposit is marked Paid, the app posts it as `Dr 1010 Bank Account / Cr 2150 Deferred Revenue`.
- Issued sales invoices post `Dr 1100 Accounts Receivable`, `Cr revenue`, and `Cr 2200 GST Output Tax` when tax is present.
- Posted customer receipts debit bank/cash and credit Accounts Receivable, with allocations updating invoice paid/partially paid status.
- Sales order deposits are not released into revenue yet. Deposit application to invoices, milestone billing automation, and deferred revenue release are future work.
- Chart-of-accounts setup lives in Settings, not on the dashboard. Add-only and setup-replace CSV imports require confirmation, and setup replacement is blocked after accounts are used by transactions, documents, payroll, contacts, or journal lines.

## Documentation

- User manual: `docs/user_manual.md`
- Architecture notes: `docs/architecture.md`
- Developer handoff notes: `docs/developer_handoff.md`
