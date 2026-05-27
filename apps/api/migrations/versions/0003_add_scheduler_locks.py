"""add scheduler locks

Revision ID: 0003_add_scheduler_locks
Revises: 0002_add_users
Create Date: 2026-05-27
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_add_scheduler_locks"
down_revision = "0002_add_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scheduler_locks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("owner_id", sa.String(length=100), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_scheduler_locks_name", "scheduler_locks", ["name"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_scheduler_locks_name", table_name="scheduler_locks")
    op.drop_table("scheduler_locks")
