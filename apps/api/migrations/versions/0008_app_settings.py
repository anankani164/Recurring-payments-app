"""add app_settings table with default scheduler_time

Revision ID: 0008_app_settings
Revises: 0007_billing_invoice_status
Create Date: 2026-05-28
"""
import sqlalchemy as sa
from alembic import op

revision = "0008_app_settings"
down_revision = "0007_billing_invoice_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("key", sa.String(100), nullable=False, unique=True),
        sa.Column("value", sa.String(500), nullable=False),
    )
    op.execute("INSERT INTO app_settings (key, value) VALUES ('scheduler_time', '08:00')")


def downgrade() -> None:
    op.drop_table("app_settings")
