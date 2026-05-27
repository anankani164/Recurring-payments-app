"""fix superadmin email

Revision ID: 0006_fix_superadmin_email
Revises: 0005_add_user_is_active
Create Date: 2026-05-27
"""

from alembic import op

revision = "0006_fix_superadmin_email"
down_revision = "0005_add_user_is_active"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE users SET email = 'superadmin@example.com' WHERE username = 'superadmin' AND email = 'superadmin@local'")


def downgrade() -> None:
    op.execute("UPDATE users SET email = 'superadmin@local' WHERE username = 'superadmin' AND email = 'superadmin@example.com'")
