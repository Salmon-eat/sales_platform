"""own site analytics (anonymous events) and ad links for bloggers/channels

Revision ID: 0013
Revises: 0012
Create Date: 2026-09-18
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analytics_events",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("visitor", sa.String(32), nullable=False),
        sa.Column("session", sa.String(32), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("path", sa.String(300), server_default="", nullable=False),
        sa.Column("lang", sa.String(2)),
        sa.Column("device", sa.String(10), server_default="desktop", nullable=False),
        sa.Column("source", sa.String(40), server_default="direct", nullable=False),
        sa.Column("campaign", sa.String(60)),
        sa.Column("listing_id", sa.Integer()),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column("props", postgresql.JSONB(), server_default="{}", nullable=False),
    )
    op.create_index("ix_analytics_events_created_at", "analytics_events", ["created_at"])
    op.create_index("ix_analytics_events_type_created", "analytics_events", ["type", "created_at"])
    op.create_index("ix_analytics_events_session", "analytics_events", ["session"])

    op.create_table(
        "tracked_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(60), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("target_path", sa.String(300), nullable=False),
        sa.Column("cost", sa.Numeric(10, 2)),
        sa.Column("notes", sa.Text()),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL", name="fk_tracked_links_created_by_id_users"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("code", name="uq_tracked_links_code"),
    )


def downgrade() -> None:
    op.drop_table("tracked_links")
    op.drop_table("analytics_events")
