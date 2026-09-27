"""attributes: plain numbers (a car's year, its kilometres) with a unit

"int" is one number per ad, filtered "from–to"; int_range stays for things that are ranges themselves.
The unit ("km", "CV") is shown after the value and in the filter, in the visitor's language.

Revision ID: 0036
Revises: 0035
Create Date: 2026-09-27
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0036"
down_revision: str | None = "0035"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _types(*types: str) -> None:
    # raw SQL on purpose: the naming convention would rename a constraint created through op.*
    listed = ", ".join(f"'{t}'" for t in types)
    op.execute("ALTER TABLE attribute_definitions DROP CONSTRAINT ck_attribute_definitions_type")
    op.execute(
        "ALTER TABLE attribute_definitions ADD CONSTRAINT ck_attribute_definitions_type "
        f"CHECK (type IN ({listed}))"
    )


def upgrade() -> None:
    op.add_column("attribute_definitions", sa.Column("unit", JSONB))
    _types("bool", "enum", "multi_enum", "int_range", "int")


def downgrade() -> None:
    op.execute("DELETE FROM attribute_definitions WHERE type = 'int'")
    _types("bool", "enum", "multi_enum", "int_range")
    op.drop_column("attribute_definitions", "unit")
