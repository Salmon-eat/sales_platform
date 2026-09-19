"""listing tags: section-level attributes (for students, documents, languages...) and hiring details

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-18
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPGRADE = [
    # an attribute belongs to a category (tier 3) or to a whole section (tags, tier 2)
    "ALTER TABLE attribute_definitions ADD COLUMN section_id INTEGER",
    """
    ALTER TABLE attribute_definitions ADD CONSTRAINT fk_attribute_definitions_section_id_sections
        FOREIGN KEY (section_id) REFERENCES sections (id) ON DELETE CASCADE
    """,
    "ALTER TABLE attribute_definitions ALTER COLUMN category_id DROP NOT NULL",
    """
    ALTER TABLE attribute_definitions ADD CONSTRAINT ck_attribute_definitions_owner
        CHECK ((category_id IS NULL) <> (section_id IS NULL))
    """,
    """
    CREATE UNIQUE INDEX uq_attribute_definitions_section_key
        ON attribute_definitions (section_id, key) WHERE section_id IS NOT NULL
    """,
    # hiring details
    "ALTER TABLE listings ADD COLUMN vacancies SMALLINT",
    "ALTER TABLE listings ADD CONSTRAINT ck_listings_vacancies CHECK (vacancies IS NULL OR vacancies BETWEEN 1 AND 999)",
    "ALTER TABLE listings ADD COLUMN start_date DATE",
    "ALTER TABLE listings ADD COLUMN is_urgent BOOLEAN DEFAULT false NOT NULL",
    "ALTER TABLE listings ADD COLUMN duration_months SMALLINT",
    """
    ALTER TABLE listings ADD CONSTRAINT ck_listings_duration_months
        CHECK (duration_months IS NULL OR duration_months BETWEEN 1 AND 36)
    """,
]

DOWNGRADE = [
    "ALTER TABLE listings DROP COLUMN duration_months",
    "ALTER TABLE listings DROP COLUMN is_urgent",
    "ALTER TABLE listings DROP COLUMN start_date",
    "ALTER TABLE listings DROP COLUMN vacancies",
    "DELETE FROM attribute_definitions WHERE section_id IS NOT NULL",
    "DROP INDEX uq_attribute_definitions_section_key",
    "ALTER TABLE attribute_definitions DROP CONSTRAINT ck_attribute_definitions_owner",
    "ALTER TABLE attribute_definitions ALTER COLUMN category_id SET NOT NULL",
    "ALTER TABLE attribute_definitions DROP CONSTRAINT fk_attribute_definitions_section_id_sections",
    "ALTER TABLE attribute_definitions DROP COLUMN section_id",
]


def upgrade() -> None:
    for statement in UPGRADE:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE:
        op.execute(statement)
