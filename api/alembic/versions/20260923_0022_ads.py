"""listings become classifieds: a price, photos, an owner and the moderation trail

- price / price_period / price_kind / currency: the number people look at first outside the jobs section
- owner_id: the visitor who posted it (null = posted by the team, as before)
- moderation: who checked it, when, and why it was refused
- listing_photos: up to ten per listing, kept on the server with their thumbnails

Revision ID: 0022
Revises: 0021
Create Date: 2026-09-23
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0022"
down_revision: str | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("listings", sa.Column("price", sa.Integer()))
    op.add_column("listings", sa.Column("price_period", sa.String(10)))
    op.add_column(
        "listings",
        sa.Column("price_kind", sa.String(12), server_default="fixed", nullable=False),
    )
    op.add_column("listings", sa.Column("currency", sa.String(3), server_default="EUR", nullable=False))
    op.add_column(
        "listings",
        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL", name="fk_listings_owner_id_users"),
        ),
    )
    op.add_column("listings", sa.Column("moderated_by", sa.Integer()))
    op.add_column("listings", sa.Column("moderated_at", sa.DateTime(timezone=True)))
    op.add_column("listings", sa.Column("reject_reason", sa.String(40)))
    op.add_column("listings", sa.Column("reject_note", sa.Text()))
    op.add_column("listings", sa.Column("bumped_at", sa.DateTime(timezone=True)))
    op.add_column("listings", sa.Column("promoted_until", sa.DateTime(timezone=True)))
    op.create_index("ix_listings_owner_id", "listings", ["owner_id"])


    op.create_table(
        "listing_photos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "listing_id",
            sa.Integer(),
            sa.ForeignKey("listings.id", ondelete="CASCADE", name="fk_listing_photos_listing_id_listings"),
            nullable=False,
        ),
        sa.Column("path", sa.String(200), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("sort", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_listing_photos_listing_id", "listing_photos", ["listing_id"])


def downgrade() -> None:
    op.drop_table("listing_photos")
    op.drop_index("ix_listings_owner_id", table_name="listings")
    for column in (
        "promoted_until", "bumped_at", "reject_note", "reject_reason", "moderated_at", "moderated_by",
        "owner_id", "currency", "price_kind", "price_period", "price",
    ):
        op.drop_column("listings", column)
