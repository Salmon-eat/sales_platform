"""search: listing_search document + rebuild triggers, search_misses (spec §7)

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-17
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPGRADE = [
    # es text -> spanish stemmer, en -> english, everything (incl. uk/ru) -> simple + unaccent.
    # Cyrillic stemmers in Postgres are weak; synonyms and prefix search compensate (spec §7).
    """
    CREATE OR REPLACE FUNCTION public.f_ml_tsv(es text, en text, other text) RETURNS tsvector
    LANGUAGE sql IMMUTABLE PARALLEL SAFE
    AS $$
        SELECT to_tsvector('spanish'::regconfig, coalesce(es, ''))
            || to_tsvector('english'::regconfig, coalesce(en, ''))
            || to_tsvector('simple'::regconfig, public.f_unaccent(lower(concat_ws(' ', es, en, other))))
    $$
    """,
    """
    CREATE OR REPLACE FUNCTION public.f_jsonb_words(j jsonb, key text) RETURNS text
    LANGUAGE sql IMMUTABLE PARALLEL SAFE
    AS $$
        SELECT CASE jsonb_typeof(j -> key)
            WHEN 'array' THEN (SELECT string_agg(v, ' ') FROM jsonb_array_elements_text(j -> key) v)
            ELSE j ->> key
        END
    $$
    """,
    """
    CREATE TABLE listing_search (
        listing_id INTEGER NOT NULL,
        tsv_title TSVECTOR NOT NULL,
        tsv_category TSVECTOR NOT NULL,
        tsv_location TSVECTOR NOT NULL,
        tsv_body TSVECTOR NOT NULL,
        tsv_all TSVECTOR NOT NULL,
        trgm_text TEXT NOT NULL,
        updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
        CONSTRAINT pk_listing_search PRIMARY KEY (listing_id),
        CONSTRAINT fk_listing_search_listing_id_listings FOREIGN KEY (listing_id)
            REFERENCES listings (id) ON DELETE CASCADE
    )
    """,
    # one weighted vector for matching + ranking; the per-field vectors stay for debugging/tuning
    "CREATE INDEX ix_listing_search_tsv_all ON listing_search USING gin (tsv_all)",
    "CREATE INDEX ix_listing_search_trgm_text ON listing_search USING gin (trgm_text gin_trgm_ops)",
    """
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
               setweight(x.title, 'A') || setweight(x.cat, 'A') || setweight(x.loc, 'B') || setweight(x.body, 'C'),
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
    """,
    # ---------- triggers: listing, its texts, its category (names/synonyms), its location ----------
    """
    CREATE OR REPLACE FUNCTION public.trg_listing_search_listing() RETURNS trigger
    LANGUAGE plpgsql AS $$
    BEGIN
        PERFORM public.rebuild_listing_search(NEW.id);
        RETURN NULL;
    END $$
    """,
    """
    CREATE TRIGGER listings_search_rebuild
    AFTER INSERT OR UPDATE OF category_id, location_id ON listings
    FOR EACH ROW EXECUTE FUNCTION public.trg_listing_search_listing()
    """,
    """
    CREATE OR REPLACE FUNCTION public.trg_listing_search_translation() RETURNS trigger
    LANGUAGE plpgsql AS $$
    BEGIN
        PERFORM public.rebuild_listing_search(COALESCE(NEW.listing_id, OLD.listing_id));
        RETURN NULL;
    END $$
    """,
    """
    CREATE TRIGGER listing_translations_search_rebuild
    AFTER INSERT OR UPDATE OR DELETE ON listing_translations
    FOR EACH ROW EXECUTE FUNCTION public.trg_listing_search_translation()
    """,
    """
    CREATE OR REPLACE FUNCTION public.trg_listing_search_category() RETURNS trigger
    LANGUAGE plpgsql AS $$
    BEGIN
        PERFORM public.rebuild_listing_search(l.id)
        FROM listings l
        WHERE l.category_id = NEW.id
           OR l.category_id IN (SELECT id FROM categories WHERE parent_id = NEW.id);
        RETURN NULL;
    END $$
    """,
    """
    CREATE TRIGGER categories_search_rebuild
    AFTER UPDATE OF name, synonyms, parent_id ON categories
    FOR EACH ROW
    WHEN (OLD.name IS DISTINCT FROM NEW.name OR OLD.synonyms IS DISTINCT FROM NEW.synonyms
          OR OLD.parent_id IS DISTINCT FROM NEW.parent_id)
    EXECUTE FUNCTION public.trg_listing_search_category()
    """,
    """
    CREATE OR REPLACE FUNCTION public.trg_listing_search_location() RETURNS trigger
    LANGUAGE plpgsql AS $$
    BEGIN
        PERFORM public.rebuild_listing_search(l.id)
        FROM listings l
        WHERE l.location_id = NEW.id
           OR l.location_id IN (SELECT id FROM locations WHERE parent_id = NEW.id);
        RETURN NULL;
    END $$
    """,
    """
    CREATE TRIGGER locations_search_rebuild
    AFTER UPDATE OF names, aliases ON locations
    FOR EACH ROW
    WHEN (NEW.level IN ('municipio', 'provincia')
          AND (OLD.names IS DISTINCT FROM NEW.names OR OLD.aliases IS DISTINCT FROM NEW.aliases))
    EXECUTE FUNCTION public.trg_listing_search_location()
    """,
    # ---------- queries without results -> which synonyms to add (spec §7) ----------
    """
    CREATE TABLE search_misses (
        id SERIAL NOT NULL,
        lang VARCHAR(2) NOT NULL,
        section VARCHAR(50) DEFAULT '' NOT NULL,
        q VARCHAR(200) NOT NULL,
        hits INTEGER DEFAULT 1 NOT NULL,
        first_seen TIMESTAMPTZ DEFAULT now() NOT NULL,
        last_seen TIMESTAMPTZ DEFAULT now() NOT NULL,
        CONSTRAINT pk_search_misses PRIMARY KEY (id),
        CONSTRAINT uq_search_misses_lang_section_q UNIQUE (lang, section, q)
    )
    """,
    "CREATE INDEX ix_search_misses_hits ON search_misses (hits DESC)",
    # ---------- filter helpers ----------
    "CREATE INDEX ix_listings_active_salary ON listings (salary_monthly_min) WHERE status = 'active'",
    "CREATE INDEX ix_listings_active_section_published ON listings (section_id, published_at DESC) WHERE status = 'active'",
    # backfill
    "SELECT public.rebuild_listing_search(id) FROM listings",
]

DOWNGRADE = [
    "DROP INDEX IF EXISTS ix_listings_active_section_published",
    "DROP INDEX IF EXISTS ix_listings_active_salary",
    "DROP TABLE IF EXISTS search_misses",
    "DROP TRIGGER IF EXISTS locations_search_rebuild ON locations",
    "DROP TRIGGER IF EXISTS categories_search_rebuild ON categories",
    "DROP TRIGGER IF EXISTS listing_translations_search_rebuild ON listing_translations",
    "DROP TRIGGER IF EXISTS listings_search_rebuild ON listings",
    "DROP FUNCTION IF EXISTS public.trg_listing_search_location()",
    "DROP FUNCTION IF EXISTS public.trg_listing_search_category()",
    "DROP FUNCTION IF EXISTS public.trg_listing_search_translation()",
    "DROP FUNCTION IF EXISTS public.trg_listing_search_listing()",
    "DROP FUNCTION IF EXISTS public.rebuild_listing_search(integer)",
    "DROP TABLE IF EXISTS listing_search",
    "DROP FUNCTION IF EXISTS public.f_jsonb_words(jsonb, text)",
    "DROP FUNCTION IF EXISTS public.f_ml_tsv(text, text, text)",
]


def upgrade() -> None:
    for statement in UPGRADE:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE:
        op.execute(statement)
