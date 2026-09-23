"""ads posted by people themselves: a fourth kind of author

An ad from a visitor is neither the agency, nor a partner, nor a company hiring: it is a person selling
their own sofa. The card shows their name instead of "Citobazar agency".

Revision ID: 0023
Revises: 0022
Create Date: 2026-09-23
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONSTRAINT = "ck_listings_source"


def upgrade() -> None:
    op.execute(f"ALTER TABLE listings DROP CONSTRAINT {CONSTRAINT}")
    op.execute(
        f"ALTER TABLE listings ADD CONSTRAINT {CONSTRAINT} "
        "CHECK (source IN ('agency', 'partner', 'employer', 'private'))"
    )
    # what the automatic check noticed: ["contact_in_text", "stop_word:..."]. The moderator still
    # decides; these only say where to look first.
    op.add_column(
        "listings",
        sa.Column(
            "flags",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
    )
    # the moderation queue and "my ads" both read by status
    op.create_index("ix_listings_status_created", "listings", ["status", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_listings_status_created", table_name="listings")
    op.drop_column("listings", "flags")
    op.execute("UPDATE listings SET source = 'employer' WHERE source = 'private'")
    op.execute(f"ALTER TABLE listings DROP CONSTRAINT {CONSTRAINT}")
    op.execute(
        f"ALTER TABLE listings ADD CONSTRAINT {CONSTRAINT} "
        "CHECK (source IN ('agency', 'partner', 'employer'))"
    )
