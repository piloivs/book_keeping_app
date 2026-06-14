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

