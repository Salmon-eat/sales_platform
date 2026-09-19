"""localities (villages under municipalities), applications + notes

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-17
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPGRADE = [
    # ---------- localities: villages / pedanías / parroquias under a municipality ----------
    "ALTER TABLE locations DROP CONSTRAINT ck_locations_level",
    """ALTER TABLE locations ADD CONSTRAINT ck_locations_level
       CHECK (level IN ('comunidad', 'provincia', 'municipio', 'localidad'))""",
    "ALTER TABLE locations DROP CONSTRAINT ck_locations_level_prefix",
    """ALTER TABLE locations ADD CONSTRAINT ck_locations_level_prefix CHECK (
        (level = 'comunidad' AND slug LIKE 'comunidad-%')
        OR (level = 'provincia' AND slug LIKE 'provincia-%')
        OR (level = 'localidad' AND slug LIKE 'localidad-%')
        OR (level = 'municipio' AND slug NOT LIKE 'comunidad-%' AND slug NOT LIKE 'provincia-%'
            AND slug NOT LIKE 'localidad-%')
    )""",
    "ALTER TABLE locations DROP CONSTRAINT ck_locations_municipio_geog",
    """ALTER TABLE locations ADD CONSTRAINT ck_locations_point_geog
       CHECK (level NOT IN ('municipio', 'localidad') OR geog IS NOT NULL)""",
    "ALTER TABLE locations ALTER COLUMN ine_code DROP NOT NULL",
    "ALTER TABLE locations ADD CONSTRAINT ck_locations_ine_code CHECK (level = 'localidad' OR ine_code IS NOT NULL)",
    "ALTER TABLE locations ADD COLUMN geonames_id INTEGER",
    "ALTER TABLE locations ADD CONSTRAINT uq_locations_geonames_id UNIQUE (geonames_id)",
    # ---------- applications (spec §8, §10) ----------
    """
    CREATE TABLE applications (
        id SERIAL NOT NULL,
        listing_id INTEGER,
        category_id INTEGER,
        location_id INTEGER,
        user_id INTEGER,
        name VARCHAR(200) NOT NULL,
        phone VARCHAR(20) NOT NULL,
        messenger VARCHAR(20) NOT NULL,
        answers JSONB DEFAULT '{}'::jsonb NOT NULL,
        lang VARCHAR(2) NOT NULL,
        source VARCHAR(10) DEFAULT 'site' NOT NULL,
        utm JSONB DEFAULT '{}'::jsonb NOT NULL,
        status VARCHAR(20) DEFAULT 'new' NOT NULL,
        assignee_id INTEGER,
        consent_at TIMESTAMPTZ NOT NULL,
        consent_version VARCHAR(20) NOT NULL,
        ip VARCHAR(45),
        created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
        updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
        CONSTRAINT pk_applications PRIMARY KEY (id),
        CONSTRAINT fk_applications_category_id_categories FOREIGN KEY (category_id)
            REFERENCES categories (id) ON DELETE SET NULL,
        CONSTRAINT fk_applications_location_id_locations FOREIGN KEY (location_id)
            REFERENCES locations (id) ON DELETE SET NULL,
        CONSTRAINT fk_applications_user_id_users FOREIGN KEY (user_id)
            REFERENCES users (id) ON DELETE SET NULL,
        CONSTRAINT fk_applications_assignee_id_users FOREIGN KEY (assignee_id)
            REFERENCES users (id) ON DELETE SET NULL,
        CONSTRAINT ck_applications_messenger CHECK (messenger IN ('phone', 'telegram', 'whatsapp', 'viber')),
        CONSTRAINT ck_applications_source CHECK (source IN ('site', 'bot')),
        CONSTRAINT ck_applications_status CHECK (status IN ('new', 'in_progress', 'done', 'rejected')),
        CONSTRAINT ck_applications_phone_e164 CHECK (phone ~ '^\\+[1-9][0-9]{6,14}$')
    )
    """,
    "CREATE INDEX ix_applications_status_created_at ON applications (status, created_at)",
    "CREATE INDEX ix_applications_phone ON applications (phone)",
    """
    CREATE TABLE application_notes (
        id SERIAL NOT NULL,
        application_id INTEGER NOT NULL,
        author_id INTEGER,
        text TEXT NOT NULL,
        created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
        CONSTRAINT pk_application_notes PRIMARY KEY (id),
        CONSTRAINT fk_application_notes_application_id_applications FOREIGN KEY (application_id)
            REFERENCES applications (id) ON DELETE CASCADE,
        CONSTRAINT fk_application_notes_author_id_users FOREIGN KEY (author_id)
            REFERENCES users (id) ON DELETE SET NULL
    )
    """,
    "CREATE INDEX ix_application_notes_application_id ON application_notes (application_id)",
]

DOWNGRADE = [
    "DROP TABLE IF EXISTS application_notes",
    "DROP TABLE IF EXISTS applications",
    "DELETE FROM locations WHERE level = 'localidad'",
    "ALTER TABLE locations DROP CONSTRAINT uq_locations_geonames_id",
    "ALTER TABLE locations DROP COLUMN geonames_id",
    "ALTER TABLE locations DROP CONSTRAINT ck_locations_ine_code",
    "ALTER TABLE locations ALTER COLUMN ine_code SET NOT NULL",
    "ALTER TABLE locations DROP CONSTRAINT ck_locations_point_geog",
    "ALTER TABLE locations ADD CONSTRAINT ck_locations_municipio_geog CHECK (level <> 'municipio' OR geog IS NOT NULL)",
    "ALTER TABLE locations DROP CONSTRAINT ck_locations_level_prefix",
    """ALTER TABLE locations ADD CONSTRAINT ck_locations_level_prefix CHECK (
        (level = 'comunidad' AND slug LIKE 'comunidad-%')
        OR (level = 'provincia' AND slug LIKE 'provincia-%')
        OR (level = 'municipio' AND slug NOT LIKE 'comunidad-%' AND slug NOT LIKE 'provincia-%')
    )""",
    "ALTER TABLE locations DROP CONSTRAINT ck_locations_level",
    "ALTER TABLE locations ADD CONSTRAINT ck_locations_level CHECK (level IN ('comunidad', 'provincia', 'municipio'))",
]


def upgrade() -> None:
    for statement in UPGRADE:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE:
        op.execute(statement)
