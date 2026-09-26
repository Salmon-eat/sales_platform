"""articles: what people search for before they search for an ad

"How to exchange a driving licence in Spain" brings the person who will later look for a job as a
driver. One article is written in one language, by hand — the same rule as everywhere else here.

Revision ID: 0032
Revises: 0031
Create Date: 2026-09-26
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0032"
down_revision: str | None = "0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "posts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(160), nullable=False),
        sa.Column("lang", sa.String(2), nullable=False, server_default="es"),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("excerpt", sa.String(300), nullable=False, server_default=""),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("cover", sa.String(200)),
        sa.Column("status", sa.String(20), server_default="draft", nullable=False),
        sa.Column(
            "author_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL", name="fk_posts_author_id_users"),
        ),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("lang", "slug", name="uq_posts_lang_slug"),
        sa.CheckConstraint("status IN ('draft', 'published')", name="status"),
    )
    op.create_index("ix_posts_published", "posts", ["lang", "published_at"])


def downgrade() -> None:
    op.drop_table("posts")
