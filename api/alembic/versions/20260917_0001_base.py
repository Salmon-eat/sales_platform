"""base: extensions, f_unaccent, users

Revision ID: 0001
Revises:
Create Date: 2026-09-17
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# asyncpg does not allow several commands in one prepared statement -> one statement per item.
UPGRADE = [
    "CREATE EXTENSION IF NOT EXISTS postgis",
    "CREATE EXTENSION IF NOT EXISTS pg_trgm",
    "CREATE EXTENSION IF NOT EXISTS unaccent",
    # unaccent() is STABLE, so it can't be used in indexes / generated columns directly.
    """
    CREATE OR REPLACE FUNCTION public.f_unaccent(text) RETURNS text
    LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
    AS $$ SELECT public.unaccent('public.unaccent'::regdictionary, $1) $$
    """,
    """
    CREATE TABLE users (
        id SERIAL NOT NULL,
        email VARCHAR(320),
        name VARCHAR(200),
        avatar VARCHAR(500),
        lang VARCHAR(2) DEFAULT 'es' NOT NULL,
        role VARCHAR(32) DEFAULT 'user' NOT NULL,
        password_hash VARCHAR(255),
        is_active BOOLEAN DEFAULT true NOT NULL,
        created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
        updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
        CONSTRAINT pk_users PRIMARY KEY (id),
        CONSTRAINT uq_users_email UNIQUE (email)
    )
    """,
]

DOWNGRADE = [
    "DROP TABLE IF EXISTS users",
    "DROP FUNCTION IF EXISTS public.f_unaccent(text)",
]


def upgrade() -> None:
    for statement in UPGRADE:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE:
        op.execute(statement)
