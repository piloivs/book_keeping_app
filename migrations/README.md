# Database Migrations

This project uses Alembic for schema migrations.

Common commands from the project root:

```powershell
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m alembic revision --autogenerate -m "describe change"
```

The default database URL comes from `DATABASE_URL` via the app settings. If unset, it uses
`sqlite:///data/warehouse/bookkeeping.sqlite3`.

The initial migration is a baseline for the current SQLAlchemy model schema. The app still runs
`create_all` on startup for local-first convenience, but new schema changes should be captured in
Alembic revisions before they are used by application code.
