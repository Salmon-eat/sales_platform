"""anyone can report an ad, and a blocked account's ads go off the site with it

A board where strangers post needs a way for the people reading it to say "this one is wrong". The
report itself changes nothing: it puts the ad in front of a person on the team.

Revision ID: 0027
Revises: 0026
Create Date: 2026-09-25
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0027"
down_revision: str | None = "0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "listing_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "listing_id",
            sa.Integer(),
            sa.ForeignKey("listings.id", ondelete="CASCADE", name="fk_listing_reports_listing_id_listings"),
            nullable=False,
        ),
        # null: reported by someone who was not signed in
        sa.Column(
            "reporter_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL", name="fk_listing_reports_reporter_id_users"),
        ),
        sa.Column("reason", sa.String(30), nullable=False),
        sa.Column("note", sa.Text()),
        sa.Column("status", sa.String(20), server_default="new", nullable=False),
        sa.Column("ip", sa.String(45)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reviewed_by", sa.Integer()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('new', 'accepted', 'rejected')", name="status"
        ),
    )
    op.create_index("ix_listing_reports_listing", "listing_reports", ["listing_id"])
    op.create_index(
        "ix_listing_reports_waiting",
        "listing_reports",
        ["created_at"],
        postgresql_where=sa.text("status = 'new'"),
    )
    # why an account was switched off, so the team remembers and the person can be told
    op.add_column("users", sa.Column("blocked_reason", sa.String(200)))


def downgrade() -> None:
    op.drop_column("users", "blocked_reason")
    op.drop_table("listing_reports")
