"""paid extras: raising an ad, colouring it, putting it on top

Money needs a record that outlives the thing it paid for, so an order keeps what was bought, for how
much and when, even after the ad is gone. Nothing is switched on until an order is paid.

Revision ID: 0030
Revises: 0029
Create Date: 2026-09-25
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0030"
down_revision: str | None = "0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL", name="fk_orders_user_id_users"),
        ),
        # what it was for; the row survives the ad being deleted, so no cascade here
        sa.Column("listing_id", sa.Integer()),
        sa.Column("company_id", sa.Integer()),
        sa.Column("product", sa.String(30), nullable=False),
        sa.Column("days", sa.SmallInteger(), server_default="0", nullable=False),
        # in cents, so nothing is ever a float
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), server_default="EUR", nullable=False),
        sa.Column("status", sa.String(20), server_default="new", nullable=False),
        # card | manual (a transfer the team confirmed by hand)
        sa.Column("provider", sa.String(20), server_default="card", nullable=False),
        sa.Column("provider_ref", sa.String(200)),
        sa.Column("note", sa.String(200)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True)),
        sa.Column("applied_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('new', 'paid', 'failed', 'refunded', 'cancelled')", name="status"
        ),
        sa.CheckConstraint("amount >= 0", name="amount"),
    )
    op.create_index("ix_orders_user", "orders", ["user_id", "created_at"])
    op.create_index("ix_orders_status", "orders", ["status"])

    # the ad is shown with a colour until this moment (the "top" block already uses promoted_until)
    op.add_column("listings", sa.Column("highlighted_until", sa.DateTime(timezone=True)))
    # a firm paid to sit at the top of the directory
    op.add_column("companies", sa.Column("promoted_until", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("companies", "promoted_until")
    op.drop_column("listings", "highlighted_until")
    op.drop_table("orders")
