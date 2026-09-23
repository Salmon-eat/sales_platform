"""questions to the candidate per listing; CV files attached to applications

- listings.questions: [{"key": "licence_c"}, {"key": "custom1", "text": {"uk": "...", ...}}]
- application_files: the candidate's CV (PDF, Word, image), up to 5 MB, readable only by staff

Revision ID: 0019
Revises: 0018
Create Date: 2026-09-19
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("listings", sa.Column("questions", JSONB(), server_default="[]", nullable=False))
    op.create_table(
        "application_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "application_id",
            sa.Integer(),
            sa.ForeignKey(
                "applications.id", ondelete="CASCADE", name="fk_application_files_application_id_applications"
            ),
            nullable=False,
        ),
        sa.Column("filename", sa.String(200), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_application_files_application_id", "application_files", ["application_id"])


def downgrade() -> None:
    op.drop_table("application_files")
    op.drop_column("listings", "questions")
