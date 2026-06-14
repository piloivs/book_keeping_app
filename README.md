# Bookkeeping App

Local-first bookkeeping prototype built with FastAPI, SQLite, SQLAlchemy, and React.

## What is included

- Double-entry journal entries with debit/credit validation
- Seeded chart of accounts
- Dashboard summary endpoint
- Account and journal entry APIs
- React dashboard with account list, recent activity, and a transaction form
- SQLite by default, with `DATABASE_URL` support for a future PostgreSQL deployment

## Run Locally

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

## Data

The prototype stores SQLite data at `data/warehouse/bookkeeping.sqlite3` by default. Raw data belongs in `data/raw/` and should not be edited manually.

