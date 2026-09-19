"""site chat: a conversation in the orange window; the phone becomes optional for it

- applications.phone nullable (a chat message may come without a phone: the reply goes to the window)
- applications.chat_token: the visitor's browser keeps it to read and continue the conversation
- application_messages: the conversation (visitor / staff), read_at marks what staff has seen

Revision ID: 0016
Revises: 0015
Create Date: 2026-09-19
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("applications", "phone", existing_type=sa.String(20), nullable=True)
    op.add_column("applications", sa.Column("chat_token", sa.String(64)))
    op.create_index("ix_applications_chat_token", "applications", ["chat_token"], unique=True)
    op.create_table(
        "application_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "application_id",
            sa.Integer(),
            sa.ForeignKey(
                "applications.id", ondelete="CASCADE", name="fk_application_messages_application_id_applications"
            ),
            nullable=False,
        ),
        sa.Column("author", sa.String(10), nullable=False),
        sa.Column(
            "author_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL", name="fk_application_messages_author_id_users"),
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("author IN ('visitor', 'staff')", name="ck_application_messages_author"),
    )
    op.create_index("ix_application_messages_application_id", "application_messages", ["application_id"])


def downgrade() -> None:
    op.drop_table("application_messages")
    op.drop_index("ix_applications_chat_token", table_name="applications")
    op.drop_column("applications", "chat_token")
    op.execute("UPDATE applications SET phone = '' WHERE phone IS NULL")
    op.alter_column("applications", "phone", existing_type=sa.String(20), nullable=False)
