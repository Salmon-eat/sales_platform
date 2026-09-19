"""no "original language": the fallback text is Spanish when present, else the first of en/uk/ru

The platform is multilingual; listings.original_lang now only says which text is shown where the
visitor's language is missing. Recompute it for existing listings.

Revision ID: 0012
Revises: 0011
Create Date: 2026-09-18
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE listings l SET original_lang = (
            SELECT t.lang FROM listing_translations t WHERE t.listing_id = l.id
            ORDER BY array_position(ARRAY['es', 'en', 'uk', 'ru']::varchar[], t.lang::varchar)
            LIMIT 1
        )
        WHERE EXISTS (SELECT 1 FROM listing_translations t WHERE t.listing_id = l.id)
        """
    )


def downgrade() -> None:
    pass  # the old value was a manual choice; nothing to restore
