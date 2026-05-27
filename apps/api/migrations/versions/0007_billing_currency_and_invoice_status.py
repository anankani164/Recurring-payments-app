"""add billing currency, rate source url, invoice status, rate pdf path

Revision ID: 0007_billing_currency_and_invoice_status
Revises: 0006_fix_superadmin_email
Create Date: 2026-05-27
"""
import sqlalchemy as sa
from alembic import op

revision = "0007_billing_currency_and_invoice_status"
down_revision = "0006_fix_superadmin_email"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("billing_currency", sa.String(3), nullable=False, server_default="USD"))
    op.add_column("projects", sa.Column("amount_ghs", sa.Float(), nullable=True))
    op.add_column("projects", sa.Column("rate_source_url", sa.String(500), nullable=True))
    op.add_column("invoices", sa.Column("status", sa.String(20), nullable=False, server_default="pending"))
    op.add_column("invoices", sa.Column("rate_pdf_path", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "billing_currency")
    op.drop_column("projects", "amount_ghs")
    op.drop_column("projects", "rate_source_url")
    op.drop_column("invoices", "status")
    op.drop_column("invoices", "rate_pdf_path")
