When starting a new data or analytics project, create a tidy project structure with these conventions:

- Put project-specific agent instructions in `AGENTS.md` at the project root.
- Put assignment briefs, rubrics, stakeholder notes, ChatGPT exports, and business/source context in `docs/references/`.
- Put final documentation in `docs/`.
- Put raw data in `data/raw/` and do not edit it manually.
- Put processed or intermediate data in `data/processed/`.
- Put local warehouse files in `data/warehouse/`.
- Put Python scripts and reusable project code in `src/`.
- Put SQL schemas, transformations, quality checks, and analysis queries in `sql/`.
- Put dbt project files, models, tests, macros, and profiles in `dbt/`.
- Put dashboards in `dashboard/`.
- Put exploratory notebooks in `notebooks/`.
- Put presentation outlines, speaker notes, and final decks in `slides/`.
- Put automated tests in `tests/`.
- Put generated review outputs in `outputs/`.
- Put runtime logs in `logs/`.

When creating a new project, also add `docs/project_startup_template.md` and `docs/references/README.md` unless the user asks for a different structure.

For PowerPoint deck creation or substantial slide editing, prefer `python-pptx` when it can produce stable, editable slides and avoid PowerPoint file-opening errors.

## IntelliArtAI Bookkeeping App Direction

Use `docs/references/CODEX_PRIMARY_INSTRUCTIONS.md` as the long-form product and architecture reference for this project.

This app starts as IntelliArtAI's internal bookkeeping and financial operations core, but should be designed as the foundation for a future SME operating framework. Do not treat it as a simple cashbook. The ledger, documents, workflows, permissions, approvals, reports, and AI-assisted modules should eventually connect around trusted business data.

Core accounting rules:

- The general ledger is the trusted system of record.
- All accounting postings must go through backend accounting/posting services; the frontend must not directly create ledger entries.
- Every posted journal entry must balance: total debits must equal total credits.
- Use decimal-safe money fields and avoid floating-point arithmetic for money.
- Posted accounting records should be immutable. Corrections should use reversals, voids, or adjustment entries rather than silent edits or deletes.
- Closed periods should not be modifiable by normal users once period locking exists.
- Reports should be generated from ledger data wherever possible.
- Preserve source-document links for financial transactions.
- Add or update automated tests for core accounting behavior whenever posting logic changes.

AI and automation rules:

- AI may extract, classify, suggest, summarize, and flag anomalies.
- AI must not post accounting entries, modify posted records, delete records, override closed periods, invent financial data, or bypass permissions without human approval.
- AI suggestions and user decisions should be traceable for auditability when those workflows are implemented.

Product and compliance orientation:

- Design toward GAAP/SFRS-aligned bookkeeping for Singapore SMEs, but do not claim automatic GAAP compliance.
- Prioritize accountant-ready records, audit trails, source-document retention, period controls, exportability, and GST-capable transaction structure.
- Build modularly so future finance, sales, procurement, HR, operations, documents, approval, dashboard, and AI-agent modules can share company, user, role, document, workflow, audit, and ledger data.
