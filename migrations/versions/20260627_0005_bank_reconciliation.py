"""Add bank statement reconciliation lines.

Revision ID: 20260627_0005
Revises: 20260627_0004
Create Date: 2026-06-27
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260627_0005"
down_revision: str | None = "20260627_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "bank_statement_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bank_account_id", sa.Integer(), nullable=False),
        sa.Column("statement_date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(length=240), nullable=False),
        sa.Column("reference", sa.String(length=80), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.Enum("UNMATCHED", "RECONCILED", "IGNORED", name="bankstatementlinestatus"), nullable=False),
        sa.Column("journal_entry_id", sa.Integer(), nullable=True),
        sa.Column("reconciled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["bank_account_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["journal_entry_id"], ["journal_entries.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("journal_entry_id"),
    )
    op.create_index(op.f("ix_bank_statement_lines_bank_account_id"), "bank_statement_lines", ["bank_account_id"], unique=False)
    op.create_index(op.f("ix_bank_statement_lines_journal_entry_id"), "bank_statement_lines", ["journal_entry_id"], unique=True)
    op.create_index(op.f("ix_bank_statement_lines_reference"), "bank_statement_lines", ["reference"], unique=False)
    op.create_index(op.f("ix_bank_statement_lines_statement_date"), "bank_statement_lines", ["statement_date"], unique=False)
    op.create_index(op.f("ix_bank_statement_lines_status"), "bank_statement_lines", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_bank_statement_lines_status"), table_name="bank_statement_lines")
    op.drop_index(op.f("ix_bank_statement_lines_statement_date"), table_name="bank_statement_lines")
    op.drop_index(op.f("ix_bank_statement_lines_reference"), table_name="bank_statement_lines")
    op.drop_index(op.f("ix_bank_statement_lines_journal_entry_id"), table_name="bank_statement_lines")
    op.drop_index(op.f("ix_bank_statement_lines_bank_account_id"), table_name="bank_statement_lines")
    op.drop_table("bank_statement_lines")
