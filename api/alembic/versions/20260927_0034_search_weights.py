"""search: the words of a category weigh less than the words of the ad itself

The category name and its synonyms are written into every ad's search document — that is what lets a
Ukrainian word find a Spanish ad. They used to carry weight A, the same as the title, so once the
goods and motor categories got a proper list of synonyms, a search for "диван" would have ranked every
piece of furniture exactly as high as the sofa somebody is actually selling.

Title A, category B, place C, body D: what the seller wrote comes first, what we know about the ad
comes after it.

Revision ID: 0034
Revises: 0033
Create Date: 2026-09-27
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0034"
down_revision: str | None = "0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# only the setweight() line differs from 0005; everything else is copied so the function stays whole
BODY = """
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
               setweight(x.title, 'A') || setweight(x.cat, {cat}) || setweight(x.loc, {loc})
               || setweight(x.body, {body}),
               x.trgm, now()
        FROM (
            SELECT
                public.f_ml_tsv(tr.es_title, tr.en_title, tr.other_title) AS title,
                public.f_ml_tsv(tr.es_body, tr.en_body, tr.other_body) AS body,
                public.f_ml_tsv(
                    concat_ws(' ', c.name ->> 'es', public.f_jsonb_words(c.synonyms, 'es'),
                              p.name ->> 'es', public.f_jsonb_words(p.synonyms, 'es')),
                    concat_ws(' ', c.name ->> 'en', public.f_jsonb_words(c.synonyms, 'en'),
                              p.name ->> 'en', public.f_jsonb_words(p.synonyms, 'en')),
                    concat_ws(' ', c.name ->> 'uk', c.name ->> 'ru',
                              public.f_jsonb_words(c.synonyms, 'uk'), public.f_jsonb_words(c.synonyms, 'ru'),
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

REBUILD = "SELECT public.rebuild_listing_search(id) FROM listings"


def upgrade() -> None:
    op.execute(BODY.format(cat="'B'", loc="'C'", body="'D'"))
    op.execute(REBUILD)


def downgrade() -> None:
    op.execute(BODY.format(cat="'A'", loc="'B'", body="'C'"))
    op.execute(REBUILD)
