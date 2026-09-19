"""search performance: trigram threshold for the indexed %> operator, index for spain_wide OR radius

Found with the stage-3 load test (10k listings): word_similarity() as a function forced a seq scan,
and `ST_DWithin(...) OR location_scope = 'spain_wide'` could not use a BitmapOr without this index.

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-17
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPGRADE = [
    # `trgm_text %> q` (= word_similarity(q, trgm_text) > threshold) uses the GIN trigram index
    """
    DO $$ BEGIN
        EXECUTE format('ALTER DATABASE %I SET pg_trgm.word_similarity_threshold = 0.5', current_database());
    END $$
    """,
    "CREATE INDEX ix_listings_active_location_scope ON listings (location_scope) WHERE status = 'active'",
]

DOWNGRADE = [
    "DROP INDEX IF EXISTS ix_listings_active_location_scope",
    """
    DO $$ BEGIN
        EXECUTE format('ALTER DATABASE %I RESET pg_trgm.word_similarity_threshold', current_database());
    END $$
    """,
]


def upgrade() -> None:
    for statement in UPGRADE:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE:
        op.execute(statement)
