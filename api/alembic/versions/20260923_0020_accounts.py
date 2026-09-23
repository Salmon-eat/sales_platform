"""visitor accounts: phone in the profile, favourites kept in the account

Sign-in itself needs no new tables: the visitor is a `users` row with role 'user' and the session lives
in `user_sessions`, like the team's. The login code sits in Redis, never in the database.

Revision ID: 0020
Revises: 0019
Create Date: 2026-09-23
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("phone", sa.String(20)))
    # the visitor asked us to delete the account: the row stays for the statistics, emptied
    op.add_column("users", sa.Column("deleted_at", sa.DateTime(timezone=True)))

    op.create_table(
        "favorites",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_favorites_user_id_users"),
            nullable=False,
        ),
        sa.Column("listing_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "listing_id", name="uq_favorites_user_id_listing_id"),
    )
    op.create_index("ix_favorites_user_id", "favorites", ["user_id"])


def downgrade() -> None:
    op.drop_table("favorites")
    op.drop_column("users", "deleted_at")
    op.drop_column("users", "phone")
