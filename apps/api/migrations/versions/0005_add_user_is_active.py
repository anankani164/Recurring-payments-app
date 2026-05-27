"""add user is_active

Revision ID: 0005_add_user_is_active
Revises: 0004_add_username_and_superadmin
Create Date: 2026-05-27
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_add_user_is_active"
down_revision = "0004_add_username_and_superadmin"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.alter_column("users", "is_active", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "is_active")
