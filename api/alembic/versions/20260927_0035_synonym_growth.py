"""search: words the site learns by itself, and the proposals behind them

The synonyms in seeds/taxonomy.json are overwritten every time the taxonomy is seeded, so anything
added from the admin has to live somewhere the seed never touches: categories.extra_synonyms.

synonym_proposals is what the nightly job writes: a word somebody searched for that found nothing,
together with the category people opened afterwards. Strong evidence is applied on its own; the rest
waits for a person to say yes or no.

Revision ID: 0035
Revises: 0034
Create Date: 2026-09-27
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0035"
down_revision: str | None = "0034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# the category part of the document, now with the words the site learned on its own
LEARNED = {
    "learned_es": "\n                          public.f_jsonb_words(c.extra_synonyms, 'es'),",
    "learned_en": "\n                          public.f_jsonb_words(c.extra_synonyms, 'en'),",
    "learned_other": (
        "\n                          public.f_jsonb_words(c.extra_synonyms, 'uk'),"
        " public.f_jsonb_words(c.extra_synonyms, 'ru'),"
    ),
}
NOTHING_LEARNED = dict.fromkeys(LEARNED, "")

REBUILD = """
CREATE OR REPLACE FUNCTION public.rebuild_listing_search(p_id integer) RETURNS void
LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM listings WHERE id = p_id) THEN
        DELETE FROM listing_search WHERE listing_id = p_id;
        RETURN;
    END IF;

    INSERT INTO listing_search AS s
        (listing_id, tsv_title, tsv_category, tsv_location, tsv_body, tsv_all, trgm_text, updated_at)
    SELECT p_id, x.title, x.cat, x.loc, x.body,
           setweight(x.title, 'A') || setweight(x.cat, 'B') || setweight(x.loc, 'C')
           || setweight(x.body, 'D'),
           x.trgm, now()
    FROM (
        SELECT
            public.f_ml_tsv(tr.es_title, tr.en_title, tr.other_title) AS title,
            public.f_ml_tsv(tr.es_body, tr.en_body, tr.other_body) AS body,
            public.f_ml_tsv(
                concat_ws(' ', c.name ->> 'es', public.f_jsonb_words(c.synonyms, 'es'),{learned_es}
                          p.name ->> 'es', public.f_jsonb_words(p.synonyms, 'es')),
                concat_ws(' ', c.name ->> 'en', public.f_jsonb_words(c.synonyms, 'en'),{learned_en}
                          p.name ->> 'en', public.f_jsonb_words(p.synonyms, 'en')),
                concat_ws(' ', c.name ->> 'uk', c.name ->> 'ru',
                          public.f_jsonb_words(c.synonyms, 'uk'), public.f_jsonb_words(c.synonyms, 'ru'),{learned_other}
                          p.name ->> 'uk', p.name ->> 'ru',
                          public.f_jsonb_words(p.synonyms, 'uk'), public.f_jsonb_words(p.synonyms, 'ru'))
            ) AS cat,
            to_tsvector('simple'::regconfig, concat_ws(' ', m.search_text, pr.search_text)) AS loc,
            public.f_unaccent(lower(concat_ws(' ', tr.all_titles,
                c.name ->> 'es', c.name ->> 'en', c.name ->> 'uk', c.name ->> 'ru'))) AS trgm
        FROM listings l
        JOIN categories c ON c.id = l.category_id
        LEFT JOIN categories p ON p.id = c.parent_id
        LEFT JOIN locations m ON m.id = l.location_id
        LEFT JOIN locations pr ON pr.id = m.parent_id
        CROSS JOIN LATERAL (
            SELECT
                string_agg(t.title, ' ') FILTER (WHERE t.lang = 'es') AS es_title,
                string_agg(t.title, ' ') FILTER (WHERE t.lang = 'en') AS en_title,
                string_agg(t.title, ' ') FILTER (WHERE t.lang IN ('uk', 'ru')) AS other_title,
                string_agg(concat_ws(' ', t.description, t.requirements, t.conditions), ' ')
                    FILTER (WHERE t.lang = 'es') AS es_body,
                string_agg(concat_ws(' ', t.description, t.requirements, t.conditions), ' ')
                    FILTER (WHERE t.lang = 'en') AS en_body,
                string_agg(concat_ws(' ', t.description, t.requirements, t.conditions), ' ')
                    FILTER (WHERE t.lang IN ('uk', 'ru')) AS other_body,
                string_agg(t.title, ' ') AS all_titles
            FROM listing_translations t
            WHERE t.listing_id = l.id
        ) tr
        WHERE l.id = p_id
    ) x
    ON CONFLICT (listing_id) DO UPDATE SET
        tsv_title = EXCLUDED.tsv_title,
        tsv_category = EXCLUDED.tsv_category,
        tsv_location = EXCLUDED.tsv_location,
        tsv_body = EXCLUDED.tsv_body,
        tsv_all = EXCLUDED.tsv_all,
        trgm_text = EXCLUDED.trgm_text,
        updated_at = now();
END $$
"""

TRIGGER = """
CREATE TRIGGER categories_search_rebuild
AFTER UPDATE OF name, synonyms, extra_synonyms, parent_id ON categories
FOR EACH ROW
WHEN (OLD.name IS DISTINCT FROM NEW.name OR OLD.synonyms IS DISTINCT FROM NEW.synonyms
      OR OLD.extra_synonyms IS DISTINCT FROM NEW.extra_synonyms
      OR OLD.parent_id IS DISTINCT FROM NEW.parent_id)
EXECUTE FUNCTION public.trg_listing_search_category()
"""

OLD_TRIGGER = """
CREATE TRIGGER categories_search_rebuild
AFTER UPDATE OF name, synonyms, parent_id ON categories
FOR EACH ROW
WHEN (OLD.name IS DISTINCT FROM NEW.name OR OLD.synonyms IS DISTINCT FROM NEW.synonyms
      OR OLD.parent_id IS DISTINCT FROM NEW.parent_id)
EXECUTE FUNCTION public.trg_listing_search_category()
"""


def upgrade() -> None:
    op.add_column(
        "categories",
        sa.Column("extra_synonyms", JSONB(), server_default="{}", nullable=False),
    )
    op.execute(REBUILD.format(**LEARNED))
    op.execute("DROP TRIGGER IF EXISTS categories_search_rebuild ON categories")
    op.execute(TRIGGER)

    op.create_table(
        "synonym_proposals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("word", sa.String(60), nullable=False),
        sa.Column("lang", sa.String(2), nullable=False),
        # what people opened after searching this word; null when nothing suggests a category
        sa.Column(
            "category_id",
            sa.Integer(),
            sa.ForeignKey("categories.id", ondelete="CASCADE", name="fk_synonym_proposals_category"),
        ),
        sa.Column("searches", sa.Integer(), server_default="0", nullable=False),
        sa.Column("opened", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(10), server_default="new", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("decided_by", sa.Integer()),
        sa.UniqueConstraint("word", "lang", name="uq_synonym_proposals_word_lang"),
        sa.CheckConstraint("status IN ('new', 'added', 'ignored')", name="status"),
        sa.CheckConstraint("lang IN ('es', 'en', 'uk', 'ru')", name="lang"),
    )
    op.create_index("ix_synonym_proposals_status", "synonym_proposals", ["status", "searches"])


def downgrade() -> None:
    op.drop_table("synonym_proposals")
    op.execute("DROP TRIGGER IF EXISTS categories_search_rebuild ON categories")
    op.execute(OLD_TRIGGER)
    # the function must stop reading the column before the column goes away
    op.execute(REBUILD.format(**NOTHING_LEARNED))
    op.drop_column("categories", "extra_synonyms")
