"""Add supplier bills and AP posting source links.

Revision ID: 20260627_0003
Revises: 20260627_0002
Create Date: 2026-06-27
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260627_0003"
down_revision: str | None = "20260627_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO accounts (code, name, type, description, is_active)
        SELECT '2210', 'GST Input Tax', 'ASSET', 'Recoverable GST paid on supplier bills', 1
        WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE code = '2210')
        """
    )
    op.create_table(
        "supplier_bills",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bill_number", sa.String(length=40), nullable=False),
        sa.Column("status", sa.Enum("DRAFT", "POSTED", "VOIDED", name="supplierbillstatus"), nullable=False),
        sa.Column("vendor_id", sa.Integer(), nullable=False),
        sa.Column("purchase_order_id", sa.Integer(), nullable=True),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("bill_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("payment_terms", sa.String(length=120), nullable=True),
        sa.Column("reference", sa.String(length=80), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("journal_entry_id", sa.Integer(), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["journal_entry_id"], ["journal_entries.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["purchase_order_id"], ["purchase_orders.id"]),
        sa.ForeignKeyConstraint(["vendor_id"], ["contacts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("journal_entry_id"),
    )
    op.create_index(op.f("ix_supplier_bills_bill_date"), "supplier_bills", ["bill_date"], unique=False)
    op.create_index(op.f("ix_supplier_bills_bill_number"), "supplier_bills", ["bill_number"], unique=True)
    op.create_index(op.f("ix_supplier_bills_due_date"), "supplier_bills", ["due_date"], unique=False)
    op.create_index(op.f("ix_supplier_bills_project_id"), "supplier_bills", ["project_id"], unique=False)
    op.create_index(op.f("ix_supplier_bills_purchase_order_id"), "supplier_bills", ["purchase_order_id"], unique=False)
    op.create_index(op.f("ix_supplier_bills_reference"), "supplier_bills", ["reference"], unique=False)
    op.create_index(op.f("ix_supplier_bills_status"), "supplier_bills", ["status"], unique=False)
    op.create_index(op.f("ix_supplier_bills_vendor_id"), "supplier_bills", ["vendor_id"], unique=False)
    op.create_table(
        "supplier_bill_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bill_id", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=240), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("tax_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("expense_account_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["bill_id"], ["supplier_bills.id"]),
        sa.ForeignKeyConstraint(["expense_account_id"], ["accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_supplier_bill_lines_bill_id"), "supplier_bill_lines", ["bill_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_supplier_bill_lines_bill_id"), table_name="supplier_bill_lines")
    op.drop_table("supplier_bill_lines")
    op.drop_index(op.f("ix_supplier_bills_vendor_id"), table_name="supplier_bills")
    op.drop_index(op.f("ix_supplier_bills_status"), table_name="supplier_bills")
    op.drop_index(op.f("ix_supplier_bills_reference"), table_name="supplier_bills")
    op.drop_index(op.f("ix_supplier_bills_purchase_order_id"), table_name="supplier_bills")
    op.drop_index(op.f("ix_supplier_bills_project_id"), table_name="supplier_bills")
    op.drop_index(op.f("ix_supplier_bills_due_date"), table_name="supplier_bills")
    op.drop_index(op.f("ix_supplier_bills_bill_number"), table_name="supplier_bills")
    op.drop_index(op.f("ix_supplier_bills_bill_date"), table_name="supplier_bills")
    op.drop_table("supplier_bills")
