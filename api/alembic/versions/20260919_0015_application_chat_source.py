"""applications may come from the site chat window (source = 'chat')

Revision ID: 0015
Revises: 0014
Create Date: 2026-09-19
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE applications DROP CONSTRAINT ck_applications_source")
    op.execute(
        "ALTER TABLE applications ADD CONSTRAINT ck_applications_source "
        "CHECK (source IN ('site', 'bot', 'chat'))"
    )


def downgrade() -> None:
    op.execute("UPDATE applications SET source = 'site' WHERE source = 'chat'")
    op.execute("ALTER TABLE applications DROP CONSTRAINT ck_applications_source")
    op.execute("ALTER TABLE applications ADD CONSTRAINT ck_applications_source CHECK (source IN ('site', 'bot'))")
