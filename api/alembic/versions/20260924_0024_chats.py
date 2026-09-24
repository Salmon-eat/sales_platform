"""buyer and seller talk to each other about one ad

One conversation per (ad, buyer): whoever writes first starts it, the owner of the ad answers from
their own area. Messages carry when they were read and when the other side was told about them by
email, so nobody gets a letter for a message they already saw.

Revision ID: 0024
Revises: 0023
Create Date: 2026-09-24
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "listing_id",
            sa.Integer(),
            sa.ForeignKey("listings.id", ondelete="CASCADE", name="fk_conversations_listing_id_listings"),
            nullable=False,
        ),
        sa.Column(
            "buyer_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_conversations_buyer_id_users"),
            nullable=False,
        ),
        sa.Column(
            "seller_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_conversations_seller_id_users"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_message_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("buyer_unread", sa.Integer(), server_default="0", nullable=False),
        sa.Column("seller_unread", sa.Integer(), server_default="0", nullable=False),
        # either side can put a conversation away without deleting what was said
        sa.Column("buyer_hidden", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("seller_hidden", sa.Boolean(), server_default="false", nullable=False),
        sa.UniqueConstraint("listing_id", "buyer_id", name="uq_conversations_listing_buyer"),
    )
    op.create_index("ix_conversations_buyer", "conversations", ["buyer_id", "last_message_at"])
    op.create_index("ix_conversations_seller", "conversations", ["seller_id", "last_message_at"])

    op.create_table(
        "conversation_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.Integer(),
            sa.ForeignKey(
                "conversations.id", ondelete="CASCADE", name="fk_conversation_messages_conversation"
            ),
            nullable=False,
        ),
        sa.Column(
            "sender_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL", name="fk_conversation_messages_sender_id_users"),
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        # when the other side was emailed about it; null = not told yet
        sa.Column("notified_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_conversation_messages_thread", "conversation_messages", ["conversation_id", "id"]
    )
    # the worker looks for messages nobody has read and nobody has been told about
    op.create_index(
        "ix_conversation_messages_pending",
        "conversation_messages",
        ["created_at"],
        postgresql_where=sa.text("read_at IS NULL AND notified_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_table("conversation_messages")
    op.drop_table("conversations")
