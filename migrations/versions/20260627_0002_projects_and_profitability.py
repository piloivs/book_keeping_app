"""Add projects and project links.

Revision ID: 20260627_0002
Revises: 20260627_0001
Create Date: 2026-06-27
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260627_0002"
down_revision: str | None = "20260627_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.Enum("PLANNED", "ACTIVE", "ON_HOLD", "COMPLETED", "CANCELLED", name="projectstatus"), nullable=False),
        sa.Column("service_type", sa.Enum("AI_AUTOMATION", "CONSULTING", "IMPLEMENTATION", "SUPPORT", "TRAINING", "OTHER", name="servicetype"), nullable=False),
        sa.Column("billing_model", sa.Enum("FIXED_FEE", "MILESTONE", "RETAINER", "TIME_AND_MATERIALS", "SUBSCRIPTION", "OTHER", name="billingmodel"), nullable=False),
        sa.Column("contract_value", sa.Numeric(12, 2), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["contacts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_projects_client_id"), "projects", ["client_id"], unique=False)
    op.create_index(op.f("ix_projects_name"), "projects", ["name"], unique=False)
    op.create_index(op.f("ix_projects_project_code"), "projects", ["project_code"], unique=True)
    op.create_index(op.f("ix_projects_status"), "projects", ["status"], unique=False)
    op.create_index(op.f("ix_projects_service_type"), "projects", ["service_type"], unique=False)
    op.create_index(op.f("ix_projects_billing_model"), "projects", ["billing_model"], unique=False)
    op.add_column("operational_transactions", sa.Column("project_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_operational_transactions_project_id"), "operational_transactions", ["project_id"], unique=False)
    op.add_column("sales_orders", sa.Column("project_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_sales_orders_project_id"), "sales_orders", ["project_id"], unique=False)
    op.add_column("sales_invoices", sa.Column("project_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_sales_invoices_project_id"), "sales_invoices", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_sales_invoices_project_id"), table_name="sales_invoices")
    op.drop_column("sales_invoices", "project_id")
    op.drop_index(op.f("ix_sales_orders_project_id"), table_name="sales_orders")
    op.drop_column("sales_orders", "project_id")
    op.drop_index(op.f("ix_operational_transactions_project_id"), table_name="operational_transactions")
    op.drop_column("operational_transactions", "project_id")
    op.drop_index(op.f("ix_projects_billing_model"), table_name="projects")
    op.drop_index(op.f("ix_projects_service_type"), table_name="projects")
    op.drop_index(op.f("ix_projects_status"), table_name="projects")
    op.drop_index(op.f("ix_projects_project_code"), table_name="projects")
    op.drop_index(op.f("ix_projects_name"), table_name="projects")
    op.drop_index(op.f("ix_projects_client_id"), table_name="projects")
    op.drop_table("projects")
