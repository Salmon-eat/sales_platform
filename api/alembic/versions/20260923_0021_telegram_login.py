"""sign in with Telegram: the account remembers which Telegram user it belongs to

Revision ID: 0021
Revises: 0020
Create Date: 2026-09-23
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("telegram_id", sa.BigInteger()))
    op.add_column("users", sa.Column("telegram_username", sa.String(64)))
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_telegram_id", table_name="users")
    op.drop_column("users", "telegram_username")
    op.drop_column("users", "telegram_id")
