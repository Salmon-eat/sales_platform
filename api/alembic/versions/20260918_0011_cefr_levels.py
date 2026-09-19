"""language levels become CEFR (a1..c2): basic -> a2, fluent -> c1 in listings.attributes

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-18
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MAPPING = {"basic": "a2", "fluent": "c1"}
KEYS = ("spanish_level", "english_level")


def _remap(mapping: dict[str, str]) -> None:
    for key in KEYS:
        for old, new in mapping.items():
            op.execute(
                f"UPDATE listings SET attributes = jsonb_set(attributes, '{{{key}}}', '\"{new}\"') "
                f"WHERE attributes->>'{key}' = '{old}'"
            )


def upgrade() -> None:
    _remap(MAPPING)


def downgrade() -> None:
    _remap({new: old for old, new in MAPPING.items()})
