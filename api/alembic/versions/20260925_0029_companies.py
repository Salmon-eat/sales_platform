"""a directory of firms: who they are, what they do, how to reach them

A company is not an ad. An ad goes away in thirty days; a firm stays, collects reviews and is the thing
people look for when they want "a builder in Valencia" rather than one particular job.

The page is checked by a person before it appears, like every ad, and the team can mark a firm as
verified once they have seen its papers.

Revision ID: 0029
Revises: 0028
Create Date: 2026-09-25
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0029"
down_revision: str | None = "0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE", name="fk_companies_owner_id_users"),
            nullable=False,
            unique=True,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(140), nullable=False, unique=True),
        sa.Column("lang", sa.String(2), nullable=False, server_default="es"),
        sa.Column("about", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "city_id",
            sa.Integer(),
            sa.ForeignKey("locations.id", ondelete="SET NULL", name="fk_companies_city_id_locations"),
        ),
        sa.Column("address", sa.String(200)),
        sa.Column("hours", sa.String(200)),
        # what the firm does: ids from the taxonomy, so the catalogue filters like the rest of the site
        sa.Column(
            "category_ids",
            postgresql.ARRAY(sa.Integer()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("phone", sa.String(20)),
        sa.Column("whatsapp", sa.String(20)),
        sa.Column("telegram", sa.String(64)),
        sa.Column("email", sa.String(320)),
        sa.Column("site", sa.String(200)),
        sa.Column("logo", sa.String(200)),
        sa.Column("status", sa.String(20), server_default="draft", nullable=False),
        sa.Column("reject_reason", sa.String(40)),
        sa.Column("reject_note", sa.Text()),
        # the team has seen the firm's papers
        sa.Column("is_verified", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("moderated_by", sa.Integer()),
        sa.Column("moderated_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft', 'pending', 'active', 'rejected', 'hidden')", name="status"
        ),
    )
    op.create_index("ix_companies_status", "companies", ["status"])
    op.create_index(
        "ix_companies_categories", "companies", ["category_ids"], postgresql_using="gin"
    )


def downgrade() -> None:
    op.drop_table("companies")
