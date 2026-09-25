"""people who dealt with each other can say how it went

Only somebody who actually wrote to a seller about one of their ads may review them: a rating left by
a stranger who never got in touch is not worth reading.

Revision ID: 0028
Revises: 0027
Create Date: 2026-09-25
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0028"
down_revision: str | None = "0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "seller_reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "seller_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_seller_reviews_seller_id_users"),
            nullable=False,
        ),
        sa.Column(
            "author_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_seller_reviews_author_id_users"),
            nullable=False,
        ),
        sa.Column(
            "listing_id",
            sa.Integer(),
            sa.ForeignKey("listings.id", ondelete="SET NULL", name="fk_seller_reviews_listing_id_listings"),
        ),
        sa.Column("rating", sa.SmallInteger(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False, server_default=""),
        # the seller's answer, so one side of a story is never the only one
        sa.Column("reply", sa.Text()),
        sa.Column("replied_at", sa.DateTime(timezone=True)),
        sa.Column("is_hidden", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("seller_id", "author_id", name="uq_seller_reviews_seller_author"),
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name="rating"),
        sa.CheckConstraint("seller_id <> author_id", name="not_self"),
    )
    op.create_index("ix_seller_reviews_seller", "seller_reviews", ["seller_id", "created_at"])


def downgrade() -> None:
    op.drop_table("seller_reviews")
