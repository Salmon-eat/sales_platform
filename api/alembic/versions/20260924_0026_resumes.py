"""a candidate keeps one CV in their account and applies with it in a click

The file itself lives in the database next to the row, like the CV attached to an application: it is
personal data, so it must never end up in the folder the web server hands out to anyone who asks.

Revision ID: 0026
Revises: 0025
Create Date: 2026-09-24
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0026"
down_revision: str | None = "0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "resumes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_resumes_user_id_users"),
            nullable=False,
            unique=True,
        ),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("about", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "city_id",
            sa.Integer(),
            sa.ForeignKey("locations.id", ondelete="SET NULL", name="fk_resumes_city_id_locations"),
        ),
        sa.Column("relocate", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("experience_years", sa.SmallInteger()),
        # {"es": "b1", "en": "a2"} — the four languages of the site plus the level
        sa.Column(
            "languages", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        # ["b", "c", "ce", "code95", "adr", "forklift"]
        sa.Column(
            "licences", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False
        ),
        sa.Column("has_car", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("work_permit", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("schedule", postgresql.ARRAY(sa.Text()), server_default="{}", nullable=False),
        sa.Column("salary_min", sa.Integer()),
        sa.Column("salary_period", sa.String(10)),
        # the candidate can hide the CV without deleting it
        sa.Column("is_public", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("file_name", sa.String(200)),
        sa.Column("file_type", sa.String(100)),
        sa.Column("file_size", sa.Integer()),
        sa.Column("file_data", sa.LargeBinary()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("resumes")
