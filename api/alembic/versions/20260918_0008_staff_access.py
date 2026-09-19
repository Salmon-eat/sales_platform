"""staff access: Google sign-in for whitelisted emails, server-side sessions, no passwords

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-18
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPGRADE = [
    # admin spec §1: no passwords
    "ALTER TABLE users DROP COLUMN password_hash",
    "ALTER TABLE users ADD COLUMN google_sub VARCHAR(64)",
    "ALTER TABLE users ADD CONSTRAINT uq_users_google_sub UNIQUE (google_sub)",
    "ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP WITH TIME ZONE",
    """
    CREATE TABLE user_sessions (
        id SERIAL NOT NULL,
        user_id INTEGER NOT NULL,
        token_hash VARCHAR(64) NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
        last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
        revoked_at TIMESTAMP WITH TIME ZONE,
        ip VARCHAR(45),
        user_agent VARCHAR(300),
        CONSTRAINT pk_user_sessions PRIMARY KEY (id),
        CONSTRAINT fk_user_sessions_user_id_users FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
        CONSTRAINT uq_user_sessions_token_hash UNIQUE (token_hash)
    )
    """,
    "CREATE INDEX ix_user_sessions_user_id ON user_sessions (user_id)",
]

DOWNGRADE = [
    "DROP TABLE user_sessions",
    "ALTER TABLE users DROP COLUMN last_login_at",
    "ALTER TABLE users DROP CONSTRAINT uq_users_google_sub",
    "ALTER TABLE users DROP COLUMN google_sub",
    "ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)",
]


def upgrade() -> None:
    for statement in UPGRADE:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE:
        op.execute(statement)
