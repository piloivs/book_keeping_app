# Bookkeeping App

Local-first bookkeeping prototype built with FastAPI, SQLite, SQLAlchemy, and React.

## What is included

- Double-entry journal entries with debit/credit validation
- Seeded chart of accounts
- Dashboard summary endpoint
- Account and journal entry APIs
- Receipt upload with optional AI extraction for merchant, totals, and line items
- Vendor qualification and purchase order entry/issuance
- React dashboard with account list, recent activity, transaction, payroll, reports, and settings views
- SQLite by default, with `DATABASE_URL` support for a future PostgreSQL deployment

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

## Documentation

- User manual: `docs/user_manual.md`
- Architecture notes: `docs/architecture.md`
- Developer handoff notes: `docs/developer_handoff.md`
