"""ad links are closed (moved to history) instead of switched on/off: remember when

Revision ID: 0014
Revises: 0013
Create Date: 2026-09-18
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tracked_links", sa.Column("closed_at", sa.DateTime(timezone=True)))
    op.execute("UPDATE tracked_links SET closed_at = updated_at WHERE NOT is_active")


def downgrade() -> None:
    op.drop_column("tracked_links", "closed_at")
