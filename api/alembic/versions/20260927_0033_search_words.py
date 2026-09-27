"""the words that actually exist on the site, so a misspelled one can be repaired

Postgres knows the endings of Spanish and English and nothing about Ukrainian or Russian. Instead of
hunting for dictionaries for every language, the site collects its own vocabulary: every word that
appears in a live ad, in any of the four languages, with how many ads contain it.

A typed word that is not in that list is compared against it by trigrams — so "дивани", "diwan" and
"диван" all arrive at the word the ads really use. Nothing is ever corrected to a word nobody wrote,
which means a correction always leads somewhere.

Revision ID: 0033
Revises: 0032
Create Date: 2026-09-27
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0033"
down_revision: str | None = "0032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "search_words",
        sa.Column("word", sa.String(60), primary_key=True),
        # in how many ads it appears: a word from one ad is a weaker suggestion than a common one
        sa.Column("hits", sa.Integer(), server_default="1", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.execute("CREATE INDEX ix_search_words_trgm ON search_words USING gin (word gin_trgm_ops)")


def downgrade() -> None:
    op.drop_table("search_words")
