"""Add approval requests.

Revision ID: 20260627_0006
Revises: 20260627_0005
Create Date: 2026-06-27
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260627_0006"
down_revision: str | None = "20260627_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "approval_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_type", sa.String(length=80), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("status", sa.Enum("PENDING", "APPROVED", "REJECTED", name="approvalstatus"), nullable=False),
        sa.Column("requested_by", sa.String(length=120), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("decided_by", sa.String(length=120), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("decision_notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_approval_requests_action"), "approval_requests", ["action"], unique=False)
    op.create_index(op.f("ix_approval_requests_document_id"), "approval_requests", ["document_id"], unique=False)
    op.create_index(op.f("ix_approval_requests_document_type"), "approval_requests", ["document_type"], unique=False)
    op.create_index(op.f("ix_approval_requests_status"), "approval_requests", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_approval_requests_status"), table_name="approval_requests")
    op.drop_index(op.f("ix_approval_requests_document_type"), table_name="approval_requests")
    op.drop_index(op.f("ix_approval_requests_document_id"), table_name="approval_requests")
    op.drop_index(op.f("ix_approval_requests_action"), table_name="approval_requests")
    op.drop_table("approval_requests")
