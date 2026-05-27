"""add username to users and seed superadmin

Revision ID: 0004_add_username_and_superadmin
Revises: 0003_add_scheduler_locks
Create Date: 2026-05-27
"""

from alembic import op
import sqlalchemy as sa
from passlib.context import CryptContext


revision = "0004_add_username_and_superadmin"
down_revision = "0003_add_scheduler_locks"
branch_labels = None
depends_on = None

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(length=100), nullable=True))
    op.execute("UPDATE users SET username = email WHERE username IS NULL")
    op.alter_column("users", "username", nullable=False)
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    password_hash = pwd_context.hash("Nankani1")
    op.execute(
        sa.text(
            """
            INSERT INTO users (email, username, password_hash, role, created_at)
            SELECT :email, :username, :password_hash, :role, CURRENT_TIMESTAMP
            WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = :username)
            """
        ).bindparams(
            email="superadmin@local",
            username="superadmin",
            password_hash=password_hash,
            role="superadmin",
        )
    )


def downgrade() -> None:
    op.execute("DELETE FROM users WHERE username = 'superadmin'")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_column("users", "username")
