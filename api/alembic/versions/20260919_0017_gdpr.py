"""GDPR: applications can be anonymised (on request or after the retention period)

Revision ID: 0017
Revises: 0016
Create Date: 2026-09-19
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("applications", sa.Column("anonymized_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("applications", "anonymized_at")
