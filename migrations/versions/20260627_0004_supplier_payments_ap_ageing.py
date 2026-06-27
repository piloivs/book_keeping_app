"""Add supplier payments.

Revision ID: 20260627_0004
Revises: 20260627_0003
Create Date: 2026-06-27
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260627_0004"
down_revision: str | None = "20260627_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "supplier_payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("payment_number", sa.String(length=40), nullable=False),
        sa.Column("status", sa.Enum("DRAFT", "POSTED", "VOIDED", name="supplierpaymentstatus"), nullable=False),
        sa.Column("vendor_id", sa.Integer(), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("bank_account_id", sa.Integer(), nullable=False),
        sa.Column("reference", sa.String(length=80), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("journal_entry_id", sa.Integer(), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["bank_account_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["journal_entry_id"], ["journal_entries.id"]),
        sa.ForeignKeyConstraint(["vendor_id"], ["contacts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("journal_entry_id"),
    )
    op.create_index(op.f("ix_supplier_payments_payment_number"), "supplier_payments", ["payment_number"], unique=True)
    op.create_index(op.f("ix_supplier_payments_status"), "supplier_payments", ["status"], unique=False)
    op.create_index(op.f("ix_supplier_payments_vendor_id"), "supplier_payments", ["vendor_id"], unique=False)
    op.create_index(op.f("ix_supplier_payments_payment_date"), "supplier_payments", ["payment_date"], unique=False)
    op.create_index(op.f("ix_supplier_payments_reference"), "supplier_payments", ["reference"], unique=False)
    op.create_table(
        "supplier_payment_allocations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("payment_id", sa.Integer(), nullable=False),
        sa.Column("bill_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.ForeignKeyConstraint(["bill_id"], ["supplier_bills.id"]),
        sa.ForeignKeyConstraint(["payment_id"], ["supplier_payments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_supplier_payment_allocations_payment_id"), "supplier_payment_allocations", ["payment_id"], unique=False)
    op.create_index(op.f("ix_supplier_payment_allocations_bill_id"), "supplier_payment_allocations", ["bill_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_supplier_payment_allocations_bill_id"), table_name="supplier_payment_allocations")
    op.drop_index(op.f("ix_supplier_payment_allocations_payment_id"), table_name="supplier_payment_allocations")
    op.drop_table("supplier_payment_allocations")
    op.drop_index(op.f("ix_supplier_payments_reference"), table_name="supplier_payments")
    op.drop_index(op.f("ix_supplier_payments_payment_date"), table_name="supplier_payments")
    op.drop_index(op.f("ix_supplier_payments_vendor_id"), table_name="supplier_payments")
    op.drop_index(op.f("ix_supplier_payments_status"), table_name="supplier_payments")
    op.drop_index(op.f("ix_supplier_payments_payment_number"), table_name="supplier_payments")
    op.drop_table("supplier_payments")
