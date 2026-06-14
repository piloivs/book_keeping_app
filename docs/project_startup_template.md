# Project Startup Template

## Purpose

Build a local-first bookkeeping application that can later be deployed as a web app.

## Current Scope

- Local single-user prototype
- SQLite persistence
- FastAPI backend
- React dashboard
- Double-entry accounting foundation

## Future Scope

- Authentication and user roles
- PostgreSQL deployment
- Invoices, bills, payments, and vendor/customer management
- CSV import/export
- Formal reports: profit and loss, balance sheet, cash flow, and general ledger

## Decisions

- Keep accounting logic in backend services.
- Store runtime database files in `data/warehouse/`.
- Keep raw imports immutable in `data/raw/`.

