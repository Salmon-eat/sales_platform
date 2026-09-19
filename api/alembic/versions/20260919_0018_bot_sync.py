"""Telegram bot sync: the bot's applications and conversations in the admin, replies from the admin to Telegram

- applications.bot_app_id: the application number in the bot; applications.bot: what the bot knows about it
  (questionnaire card, Telegram nickname, topic link, the bot's own status and manager)
- application_messages: 'note' authors (the team's notes in the topic), bot_message_id, delivery, author_name,
  content_type (photo, voice... without text)
- bot_outgoing: replies and status changes written in the admin, picked up by the bot in order

Revision ID: 0018
Revises: 0017
Create Date: 2026-09-19
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# the name the naming convention gave it in 0016
AUTHOR_CHECK = "ck_application_messages_ck_application_messages_author"


def upgrade() -> None:
    op.add_column("applications", sa.Column("bot_app_id", sa.Integer()))
    op.add_column("applications", sa.Column("bot", JSONB(), server_default="{}", nullable=False))
    op.create_index("ix_applications_bot_app_id", "applications", ["bot_app_id"], unique=True)

    op.execute(f"ALTER TABLE application_messages DROP CONSTRAINT {AUTHOR_CHECK}")
    op.execute(
        f"ALTER TABLE application_messages ADD CONSTRAINT {AUTHOR_CHECK} "
        "CHECK (author IN ('visitor', 'staff', 'note'))"
    )
    op.add_column("application_messages", sa.Column("bot_message_id", sa.Integer()))
    op.add_column("application_messages", sa.Column("delivery", sa.String(10)))
    op.add_column("application_messages", sa.Column("author_name", sa.String(120)))
    op.add_column("application_messages", sa.Column("content_type", sa.String(20)))
    op.create_index(
        "ix_application_messages_bot_message_id", "application_messages", ["bot_message_id"], unique=True
    )

    op.create_table(
        "bot_outgoing",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "application_id",
            sa.Integer(),
            sa.ForeignKey("applications.id", ondelete="CASCADE", name="fk_bot_outgoing_application_id_applications"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column(
            "message_id",
            sa.Integer(),
            sa.ForeignKey(
                "application_messages.id", ondelete="CASCADE", name="fk_bot_outgoing_message_id_application_messages"
            ),
        ),
        sa.Column("status", sa.String(20)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("kind IN ('message', 'status')", name="ck_bot_outgoing_kind"),
    )


def downgrade() -> None:
    op.drop_table("bot_outgoing")
    op.drop_index("ix_application_messages_bot_message_id", table_name="application_messages")
    for column in ("content_type", "author_name", "delivery", "bot_message_id"):
        op.drop_column("application_messages", column)
    op.execute("DELETE FROM application_messages WHERE author = 'note'")
    op.execute(f"ALTER TABLE application_messages DROP CONSTRAINT {AUTHOR_CHECK}")
    op.execute(
        f"ALTER TABLE application_messages ADD CONSTRAINT {AUTHOR_CHECK} "
        "CHECK (author IN ('visitor', 'staff'))"
    )
    op.drop_index("ix_applications_bot_app_id", table_name="applications")
    op.drop_column("applications", "bot")
    op.drop_column("applications", "bot_app_id")
