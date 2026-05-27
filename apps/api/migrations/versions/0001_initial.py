"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-27
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "clients",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "fx_rates",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("rate_date", sa.Date(), nullable=False),
        sa.Column("code", sa.String(length=10), nullable=False),
        sa.Column("cash_buying", sa.Float(), nullable=False),
        sa.Column("cash_selling", sa.Float(), nullable=False),
        sa.Column("tts_buying", sa.Float(), nullable=False),
        sa.Column("tts_selling", sa.Float(), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("rate_date", "code", name="uq_fx_rates_date_code"),
    )
    op.create_table(
        "job_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("job_name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("amount_usd", sa.Float(), nullable=False),
        sa.Column("recurrence", sa.String(length=50), nullable=False),
        sa.Column("rate_type", sa.String(length=50), nullable=False),
        sa.Column("next_invoice_date", sa.Date(), nullable=False),
    )
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("amount_usd", sa.Float(), nullable=False),
        sa.Column("fx_rate", sa.Float(), nullable=False),
        sa.Column("amount_ghs", sa.Float(), nullable=False),
        sa.Column("rate_type", sa.String(length=50), nullable=False),
        sa.Column("source_rate_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("project_id", "invoice_date", name="uq_project_invoice_date"),
    )


def downgrade() -> None:
    op.drop_table("invoices")
    op.drop_table("projects")
    op.drop_table("job_logs")
    op.drop_table("fx_rates")
    op.drop_table("clients")
