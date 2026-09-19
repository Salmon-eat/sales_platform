"""agency services are not listings: sections.kind (listings | services)

The "servicios" section (documents, training) becomes a catalog of permanent agency services with
their own pages. Listings that were created in it are closed, and its list pages leave seo_pages.

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-18
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPGRADE = [
    "ALTER TABLE sections ADD COLUMN kind VARCHAR(20) DEFAULT 'listings' NOT NULL",
    "ALTER TABLE sections ADD CONSTRAINT ck_sections_kind CHECK (kind IN ('listings', 'services'))",
    "UPDATE sections SET kind = 'services' WHERE key = 'servicios'",
    """
    UPDATE listings SET status = 'closed', closed_at = coalesce(closed_at, now())
    WHERE status <> 'closed' AND section_id IN (SELECT id FROM sections WHERE kind = 'services')
    """,
    "DELETE FROM seo_pages WHERE section_key IN (SELECT key FROM sections WHERE kind = 'services')",
]

DOWNGRADE = [
    "ALTER TABLE sections DROP CONSTRAINT ck_sections_kind",
    "ALTER TABLE sections DROP COLUMN kind",
]


def upgrade() -> None:
    for statement in UPGRADE:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE:
        op.execute(statement)
