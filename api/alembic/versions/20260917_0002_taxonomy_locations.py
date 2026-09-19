"""taxonomy (sections, categories, attribute_definitions), locations, slug_history

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-17
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LANGS_CHECK = "?& array['es','en','uk','ru']"

UPGRADE = [
    # array_to_string() is STABLE; this wrapper lets us use it in a generated column.
    """
    CREATE OR REPLACE FUNCTION public.f_text_join(text[]) RETURNS text
    LANGUAGE sql IMMUTABLE PARALLEL SAFE
    AS $$ SELECT coalesce(array_to_string($1, ' '), '') $$
    """,
    # ---------- sections ----------
    f"""
    CREATE TABLE sections (
        id SERIAL NOT NULL,
        key VARCHAR(50) NOT NULL,
        slug JSONB NOT NULL,
        name JSONB NOT NULL,
        is_enabled BOOLEAN DEFAULT true NOT NULL,
        sort INTEGER DEFAULT 0 NOT NULL,
        CONSTRAINT pk_sections PRIMARY KEY (id),
        CONSTRAINT uq_sections_key UNIQUE (key),
        CONSTRAINT ck_sections_slug_langs CHECK (slug {LANGS_CHECK}),
        CONSTRAINT ck_sections_name_langs CHECK (name {LANGS_CHECK})
    )
    """,
    # ---------- categories: sector -> profession ----------
    f"""
    CREATE TABLE categories (
        id SERIAL NOT NULL,
        section_id INTEGER NOT NULL,
        parent_id INTEGER,
        slug JSONB NOT NULL,
        name JSONB NOT NULL,
        synonyms JSONB DEFAULT '{{}}'::jsonb NOT NULL,
        icon VARCHAR(50),
        sort INTEGER DEFAULT 0 NOT NULL,
        is_enabled BOOLEAN DEFAULT true NOT NULL,
        seo_text JSONB DEFAULT '{{}}'::jsonb NOT NULL,
        CONSTRAINT pk_categories PRIMARY KEY (id),
        CONSTRAINT fk_categories_section_id_sections FOREIGN KEY (section_id)
            REFERENCES sections (id) ON DELETE RESTRICT,
        CONSTRAINT fk_categories_parent_id_categories FOREIGN KEY (parent_id)
            REFERENCES categories (id) ON DELETE RESTRICT,
        CONSTRAINT ck_categories_slug_langs CHECK (slug {LANGS_CHECK}),
        CONSTRAINT ck_categories_name_langs CHECK (name {LANGS_CHECK}),
        CONSTRAINT ck_categories_not_own_parent CHECK (parent_id IS NULL OR parent_id <> id)
    )
    """,
    *[
        f"CREATE UNIQUE INDEX uq_categories_section_slug_{lang} ON categories (section_id, (slug->>'{lang}'))"
        for lang in ("es", "en", "uk", "ru")
    ],
    "CREATE INDEX ix_categories_parent_id ON categories (parent_id)",
    # ---------- attribute definitions ----------
    """
    CREATE TABLE attribute_definitions (
        id SERIAL NOT NULL,
        category_id INTEGER NOT NULL,
        key VARCHAR(50) NOT NULL,
        type VARCHAR(20) NOT NULL,
        label JSONB NOT NULL,
        options JSONB DEFAULT '[]'::jsonb NOT NULL,
        filterable BOOLEAN DEFAULT true NOT NULL,
        facet_order INTEGER DEFAULT 0 NOT NULL,
        required BOOLEAN DEFAULT false NOT NULL,
        seo_indexable BOOLEAN DEFAULT false NOT NULL,
        CONSTRAINT pk_attribute_definitions PRIMARY KEY (id),
        CONSTRAINT fk_attribute_definitions_category_id_categories FOREIGN KEY (category_id)
            REFERENCES categories (id) ON DELETE CASCADE,
        CONSTRAINT uq_attribute_definitions_category_key UNIQUE (category_id, key),
        CONSTRAINT ck_attribute_definitions_key_format CHECK (key ~ '^[a-z][a-z0-9_]*$'),
        CONSTRAINT ck_attribute_definitions_type CHECK (type IN ('bool', 'enum', 'multi_enum', 'int_range')),
        CONSTRAINT ck_attribute_definitions_label_langs CHECK (label ?& array['es','en','uk','ru']),
        CONSTRAINT ck_attribute_definitions_options_array CHECK (jsonb_typeof(options) = 'array')
    )
    """,
    # ---------- locations: comunidad -> provincia -> municipio ----------
    """
    CREATE TABLE locations (
        id SERIAL NOT NULL,
        level VARCHAR(20) NOT NULL,
        parent_id INTEGER,
        ine_code VARCHAR(5) NOT NULL,
        slug VARCHAR(120) NOT NULL,
        names JSONB NOT NULL,
        aliases TEXT[] DEFAULT '{}' NOT NULL,
        population INTEGER,
        geog geography(POINT, 4326),
        search_text TEXT GENERATED ALWAYS AS (
            public.f_unaccent(lower(
                coalesce(names->>'es', '') || ' ' || coalesce(names->>'en', '') || ' ' ||
                coalesce(names->>'uk', '') || ' ' || coalesce(names->>'ru', '') || ' ' ||
                public.f_text_join(aliases)
            ))
        ) STORED,
        CONSTRAINT pk_locations PRIMARY KEY (id),
        CONSTRAINT fk_locations_parent_id_locations FOREIGN KEY (parent_id)
            REFERENCES locations (id) ON DELETE RESTRICT,
        CONSTRAINT uq_locations_slug UNIQUE (slug),
        CONSTRAINT uq_locations_level_ine_code UNIQUE (level, ine_code),
        CONSTRAINT ck_locations_level CHECK (level IN ('comunidad', 'provincia', 'municipio')),
        CONSTRAINT ck_locations_names_es CHECK (names ? 'es'),
        CONSTRAINT ck_locations_slug_format CHECK (slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),
        CONSTRAINT ck_locations_level_prefix CHECK (
            (level = 'comunidad' AND slug LIKE 'comunidad-%')
            OR (level = 'provincia' AND slug LIKE 'provincia-%')
            OR (level = 'municipio' AND slug NOT LIKE 'comunidad-%' AND slug NOT LIKE 'provincia-%')
        ),
        CONSTRAINT ck_locations_municipio_geog CHECK (level <> 'municipio' OR geog IS NOT NULL)
    )
    """,
    "CREATE INDEX ix_locations_geog ON locations USING gist (geog)",
    "CREATE INDEX ix_locations_search_text_trgm ON locations USING gin (search_text gin_trgm_ops)",
    "CREATE INDEX ix_locations_parent_id ON locations (parent_id)",
    "CREATE INDEX ix_locations_level_population ON locations (level, population DESC NULLS LAST)",
    # ---------- slug history (301 from old slugs) ----------
    """
    CREATE TABLE slug_history (
        id SERIAL NOT NULL,
        entity_type VARCHAR(20) NOT NULL,
        entity_id INTEGER NOT NULL,
        lang VARCHAR(2) NOT NULL,
        old_slug VARCHAR(120) NOT NULL,
        created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
        CONSTRAINT pk_slug_history PRIMARY KEY (id),
        CONSTRAINT uq_slug_history_entity_type_lang_old_slug UNIQUE (entity_type, lang, old_slug)
    )
    """,
    # ---------- a category slug must never equal a location slug (path resolver, spec §6) ----------
    """
    CREATE OR REPLACE FUNCTION public.trg_category_slug_not_location() RETURNS trigger
    LANGUAGE plpgsql AS $$
    DECLARE clash text;
    BEGIN
        SELECT s.value INTO clash
        FROM jsonb_each_text(NEW.slug) s
        JOIN locations l ON l.slug = s.value
        LIMIT 1;
        IF clash IS NOT NULL THEN
            RAISE EXCEPTION 'category slug "%" is already used by a location', clash
                USING ERRCODE = 'unique_violation';
        END IF;
        RETURN NEW;
    END $$
    """,
    """
    CREATE TRIGGER categories_slug_not_location
    BEFORE INSERT OR UPDATE OF slug ON categories
    FOR EACH ROW EXECUTE FUNCTION public.trg_category_slug_not_location()
    """,
    """
    CREATE OR REPLACE FUNCTION public.trg_location_slug_not_category() RETURNS trigger
    LANGUAGE plpgsql AS $$
    BEGIN
        IF EXISTS (SELECT 1 FROM categories c, jsonb_each_text(c.slug) s WHERE s.value = NEW.slug) THEN
            RAISE EXCEPTION 'location slug "%" is already used by a category', NEW.slug
                USING ERRCODE = 'unique_violation';
        END IF;
        RETURN NEW;
    END $$
    """,
    """
    CREATE TRIGGER locations_slug_not_category
    BEFORE INSERT OR UPDATE OF slug ON locations
    FOR EACH ROW EXECUTE FUNCTION public.trg_location_slug_not_category()
    """,
    # ---------- categories: max depth sector -> profession, same section as parent ----------
    """
    CREATE OR REPLACE FUNCTION public.trg_category_depth() RETURNS trigger
    LANGUAGE plpgsql AS $$
    DECLARE p categories%ROWTYPE;
    BEGIN
        IF NEW.parent_id IS NULL THEN RETURN NEW; END IF;
        SELECT * INTO p FROM categories WHERE id = NEW.parent_id;
        IF p.parent_id IS NOT NULL THEN
            RAISE EXCEPTION 'categories are limited to sector -> profession (2 levels under a section)';
        END IF;
        IF p.section_id <> NEW.section_id THEN
            RAISE EXCEPTION 'category must belong to the same section as its parent';
        END IF;
        RETURN NEW;
    END $$
    """,
    """
    CREATE TRIGGER categories_depth
    BEFORE INSERT OR UPDATE OF parent_id, section_id ON categories
    FOR EACH ROW EXECUTE FUNCTION public.trg_category_depth()
    """,
    # ---------- record old slugs automatically ----------
    """
    CREATE OR REPLACE FUNCTION public.trg_slug_history_jsonb() RETURNS trigger
    LANGUAGE plpgsql AS $$
    BEGIN
        INSERT INTO slug_history (entity_type, entity_id, lang, old_slug)
        SELECT TG_ARGV[0], OLD.id, o.key, o.value
        FROM jsonb_each_text(OLD.slug) o
        WHERE o.value IS DISTINCT FROM NEW.slug->>o.key
        ON CONFLICT (entity_type, lang, old_slug) DO UPDATE SET entity_id = EXCLUDED.entity_id;
        RETURN NEW;
    END $$
    """,
    """
    CREATE TRIGGER categories_slug_history
    AFTER UPDATE OF slug ON categories
    FOR EACH ROW WHEN (OLD.slug IS DISTINCT FROM NEW.slug)
    EXECUTE FUNCTION public.trg_slug_history_jsonb('category')
    """,
    """
    CREATE TRIGGER sections_slug_history
    AFTER UPDATE OF slug ON sections
    FOR EACH ROW WHEN (OLD.slug IS DISTINCT FROM NEW.slug)
    EXECUTE FUNCTION public.trg_slug_history_jsonb('section')
    """,
    """
    CREATE OR REPLACE FUNCTION public.trg_slug_history_location() RETURNS trigger
    LANGUAGE plpgsql AS $$
    BEGIN
        -- location slugs are the same in every language -> lang '*'
        INSERT INTO slug_history (entity_type, entity_id, lang, old_slug)
        VALUES ('location', OLD.id, '*', OLD.slug)
        ON CONFLICT (entity_type, lang, old_slug) DO UPDATE SET entity_id = EXCLUDED.entity_id;
        RETURN NEW;
    END $$
    """,
    """
    CREATE TRIGGER locations_slug_history
    AFTER UPDATE OF slug ON locations
    FOR EACH ROW WHEN (OLD.slug IS DISTINCT FROM NEW.slug)
    EXECUTE FUNCTION public.trg_slug_history_location()
    """,
]

DOWNGRADE = [
    "DROP TABLE IF EXISTS slug_history",
    "DROP TABLE IF EXISTS locations",
    "DROP TABLE IF EXISTS attribute_definitions",
    "DROP TABLE IF EXISTS categories",
    "DROP TABLE IF EXISTS sections",
    "DROP FUNCTION IF EXISTS public.trg_slug_history_location()",
    "DROP FUNCTION IF EXISTS public.trg_slug_history_jsonb()",
    "DROP FUNCTION IF EXISTS public.trg_category_depth()",
    "DROP FUNCTION IF EXISTS public.trg_location_slug_not_category()",
    "DROP FUNCTION IF EXISTS public.trg_category_slug_not_location()",
    "DROP FUNCTION IF EXISTS public.f_text_join(text[])",
]


def upgrade() -> None:
    for statement in UPGRADE:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE:
        op.execute(statement)
