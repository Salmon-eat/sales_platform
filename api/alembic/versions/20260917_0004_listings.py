"""listings + listing_translations (spec §8)

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-17
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPGRADE = [
    """
    CREATE TABLE listings (
        id SERIAL NOT NULL,
        section_id INTEGER NOT NULL,
        category_id INTEGER NOT NULL,
        location_id INTEGER,
        location_scope VARCHAR(20) DEFAULT 'local' NOT NULL,
        geog geography(POINT, 4326),
        status VARCHAR(20) DEFAULT 'draft' NOT NULL,
        original_lang VARCHAR(2) NOT NULL,
        salary_min INTEGER,
        salary_max INTEGER,
        salary_period VARCHAR(10),
        salary_monthly_min INTEGER,
        housing BOOLEAN DEFAULT false NOT NULL,
        no_language BOOLEAN DEFAULT false NOT NULL,
        no_experience BOOLEAN DEFAULT false NOT NULL,
        schedule TEXT[] DEFAULT '{}' NOT NULL,
        contract VARCHAR(20),
        attributes JSONB DEFAULT '{}'::jsonb NOT NULL,
        contact JSONB DEFAULT '{}'::jsonb NOT NULL,
        source VARCHAR(20) DEFAULT 'agency' NOT NULL,
        employer_name VARCHAR(200),
        is_pinned BOOLEAN DEFAULT false NOT NULL,
        published_at TIMESTAMPTZ,
        expires_at TIMESTAMPTZ,
        closed_at TIMESTAMPTZ,
        created_by INTEGER,
        created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
        updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
        CONSTRAINT pk_listings PRIMARY KEY (id),
        CONSTRAINT fk_listings_section_id_sections FOREIGN KEY (section_id)
            REFERENCES sections (id) ON DELETE RESTRICT,
        CONSTRAINT fk_listings_category_id_categories FOREIGN KEY (category_id)
            REFERENCES categories (id) ON DELETE RESTRICT,
        CONSTRAINT fk_listings_location_id_locations FOREIGN KEY (location_id)
            REFERENCES locations (id) ON DELETE RESTRICT,
        CONSTRAINT fk_listings_created_by_users FOREIGN KEY (created_by)
            REFERENCES users (id) ON DELETE SET NULL,
        CONSTRAINT ck_listings_status CHECK (
            status IN ('draft', 'pending', 'active', 'paused', 'expired', 'closed', 'rejected')
        ),
        CONSTRAINT ck_listings_original_lang CHECK (original_lang IN ('es', 'en', 'uk', 'ru')),
        CONSTRAINT ck_listings_location_scope CHECK (
            (location_scope = 'local' AND location_id IS NOT NULL)
            OR (location_scope = 'spain_wide' AND location_id IS NULL)
        ),
        CONSTRAINT ck_listings_salary_period CHECK (salary_period IN ('hour', 'day', 'week', 'month')),
        CONSTRAINT ck_listings_salary_pair CHECK (
            (salary_min IS NULL AND salary_max IS NULL) = (salary_period IS NULL)
        ),
        CONSTRAINT ck_listings_salary_range CHECK (
            salary_min IS NULL OR salary_max IS NULL OR salary_max >= salary_min
        ),
        CONSTRAINT ck_listings_schedule CHECK (schedule <@ ARRAY['full', 'part', 'weekends', 'shifts']),
        CONSTRAINT ck_listings_contract CHECK (contract IN ('indefinido', 'temporal', 'fijo_discontinuo')),
        CONSTRAINT ck_listings_source CHECK (source IN ('agency', 'partner', 'employer')),
        CONSTRAINT ck_listings_attributes_object CHECK (jsonb_typeof(attributes) = 'object'),
        CONSTRAINT ck_listings_active_published CHECK (status <> 'active' OR published_at IS NOT NULL)
    )
    """,
    "CREATE INDEX ix_listings_status_category_location ON listings (status, category_id, location_id)",
    "CREATE INDEX ix_listings_attributes ON listings USING gin (attributes jsonb_path_ops)",
    "CREATE INDEX ix_listings_geog ON listings USING gist (geog)",
    "CREATE INDEX ix_listings_published_at ON listings (published_at DESC)",
    "CREATE INDEX ix_listings_active_expires_at ON listings (expires_at) WHERE status = 'active'",
    "CREATE INDEX ix_listings_created_by ON listings (created_by)",
    """
    CREATE TABLE listing_translations (
        id SERIAL NOT NULL,
        listing_id INTEGER NOT NULL,
        lang VARCHAR(2) NOT NULL,
        title VARCHAR(200) NOT NULL,
        description TEXT NOT NULL,
        requirements TEXT,
        conditions TEXT,
        slug VARCHAR(160) NOT NULL,
        is_machine BOOLEAN DEFAULT false NOT NULL,
        created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
        updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
        CONSTRAINT pk_listing_translations PRIMARY KEY (id),
        CONSTRAINT fk_listing_translations_listing_id_listings FOREIGN KEY (listing_id)
            REFERENCES listings (id) ON DELETE CASCADE,
        CONSTRAINT uq_listing_translations_listing_id_lang UNIQUE (listing_id, lang),
        CONSTRAINT ck_listing_translations_lang CHECK (lang IN ('es', 'en', 'uk', 'ru')),
        CONSTRAINT ck_listing_translations_slug CHECK (slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$')
    )
    """,
    """ALTER TABLE applications ADD CONSTRAINT fk_applications_listing_id_listings
       FOREIGN KEY (listing_id) REFERENCES listings (id) ON DELETE SET NULL""",
    "CREATE INDEX ix_applications_listing_id ON applications (listing_id)",
]

DOWNGRADE = [
    "DROP INDEX IF EXISTS ix_applications_listing_id",
    "ALTER TABLE applications DROP CONSTRAINT IF EXISTS fk_applications_listing_id_listings",
    "DROP TABLE IF EXISTS listing_translations",
    "DROP TABLE IF EXISTS listings",
]


def upgrade() -> None:
    for statement in UPGRADE:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE:
        op.execute(statement)
