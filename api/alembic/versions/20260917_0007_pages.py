"""public pages: seo_pages (thresholds + hysteresis), content_blocks, employer_requests

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-17
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPGRADE = [
    # One row per language and list page: /{lang}/{section}/{sector?}/{profession?}/{feature?}/{location?}
    """
    CREATE TABLE seo_pages (
        id SERIAL NOT NULL,
        path_key VARCHAR(300) NOT NULL,
        lang VARCHAR(2) NOT NULL,
        section_key VARCHAR(50) NOT NULL,
        category_key VARCHAR(100),
        feature VARCHAR(50),
        location_slug VARCHAR(120),
        tier VARCHAR(20) NOT NULL,
        active_count INTEGER DEFAULT 0 NOT NULL,
        threshold INTEGER DEFAULT 0 NOT NULL,
        indexable BOOLEAN DEFAULT false NOT NULL,
        below_since TIMESTAMPTZ,
        last_listing_at TIMESTAMPTZ,
        title_override VARCHAR(200),
        description_override VARCHAR(400),
        recounted_at TIMESTAMPTZ DEFAULT now() NOT NULL,
        CONSTRAINT pk_seo_pages PRIMARY KEY (id),
        CONSTRAINT uq_seo_pages_path_key UNIQUE (path_key),
        CONSTRAINT ck_seo_pages_lang CHECK (lang IN ('es', 'en', 'uk', 'ru'))
    )
    """,
    "CREATE INDEX ix_seo_pages_lang_indexable ON seo_pages (lang, indexable)",
    # Static pages and FAQ texts; missing language -> Spanish (spec §2)
    """
    CREATE TABLE content_blocks (
        id SERIAL NOT NULL,
        key VARCHAR(100) NOT NULL,
        lang VARCHAR(2) NOT NULL,
        title VARCHAR(200) NOT NULL,
        body TEXT DEFAULT '' NOT NULL,
        data JSONB DEFAULT '{}'::jsonb NOT NULL,
        updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
        CONSTRAINT pk_content_blocks PRIMARY KEY (id),
        CONSTRAINT uq_content_blocks_key_lang UNIQUE (key, lang),
        CONSTRAINT ck_content_blocks_lang CHECK (lang IN ('es', 'en', 'uk', 'ru'))
    )
    """,
    # "Publish a job" requests from employers (spec §8); managers turn them into listings (stage 5 screen)
    """
    CREATE TABLE employer_requests (
        id SERIAL NOT NULL,
        company VARCHAR(200) NOT NULL,
        contact_name VARCHAR(200) NOT NULL,
        phone VARCHAR(20) NOT NULL,
        email VARCHAR(320),
        messenger VARCHAR(20) DEFAULT 'phone' NOT NULL,
        text TEXT NOT NULL,
        lang VARCHAR(2) NOT NULL,
        status VARCHAR(20) DEFAULT 'new' NOT NULL,
        consent_at TIMESTAMPTZ NOT NULL,
        consent_version VARCHAR(20) NOT NULL,
        ip VARCHAR(45),
        created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
        updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
        CONSTRAINT pk_employer_requests PRIMARY KEY (id),
        CONSTRAINT ck_employer_requests_status CHECK (status IN ('new', 'in_progress', 'done', 'rejected')),
        CONSTRAINT ck_employer_requests_phone_e164 CHECK (phone ~ '^\\+[1-9][0-9]{6,14}$')
    )
    """,
    "CREATE INDEX ix_employer_requests_status ON employer_requests (status)",
]

DOWNGRADE = [
    "DROP TABLE IF EXISTS employer_requests",
    "DROP TABLE IF EXISTS content_blocks",
    "DROP TABLE IF EXISTS seo_pages",
]


def upgrade() -> None:
    for statement in UPGRADE:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE:
        op.execute(statement)
