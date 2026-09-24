"""each person decides how they hear about a waiting message

Both ways are on for a new account, and either can be switched off in the account. Somebody who signed
in with Telegram gets it there; everybody else by email.

Revision ID: 0025
Revises: 0024
Create Date: 2026-09-24
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0025"
down_revision: str | None = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("notify_email", sa.Boolean(), server_default="true", nullable=False))
    op.add_column(
        "users", sa.Column("notify_telegram", sa.Boolean(), server_default="true", nullable=False)
    )


def downgrade() -> None:
    op.drop_column("users", "notify_telegram")
    op.drop_column("users", "notify_email")
