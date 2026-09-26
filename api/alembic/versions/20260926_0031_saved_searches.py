"""a saved search tells its owner when something new turns up

Somebody looking for a flat under 900 € in Valencia should not have to come back every day. They save
the search once and hear about the new ones.

`last_seen_id` is the highest ad id they have already been told about; everything above it is new.

Revision ID: 0031
Revises: 0030
Create Date: 2026-09-26
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0031"
down_revision: str | None = "0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "saved_searches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_saved_searches_user_id_users"),
            nullable=False,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("lang", sa.String(2), nullable=False, server_default="es"),
        # what was searched for: the section, the category and the town by their slugs…
        sa.Column("section_key", sa.String(50)),
        sa.Column("category_slug", sa.String(120)),
        sa.Column("location_slug", sa.String(120)),
        # …and everything else exactly as it stood in the address bar
        sa.Column("params", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.Column("notify", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("last_seen_id", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_notified_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_saved_searches_user", "saved_searches", ["user_id", "created_at"])
    op.create_index(
        "ix_saved_searches_watching",
        "saved_searches",
        ["id"],
        postgresql_where=sa.text("notify"),
    )


def downgrade() -> None:
    op.drop_table("saved_searches")
