from typing import Any

from sqlalchemy import ColumnElement, Select, func
from sqlalchemy.orm import aliased

from app.models import Location


def coords() -> tuple[ColumnElement[float], ColumnElement[float]]:
    point = func.ST_GeomFromWKB(func.ST_AsBinary(Location.geog))
    return func.ST_Y(point).label("lat"), func.ST_X(point).label("lon")


def search_condition(q: str) -> ColumnElement[bool]:
    """Substring match over every name and alias (es, co-official, Cyrillic, transliteration)."""
    escaped = q.strip().lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return Location.search_text.like(func.concat("%", func.public.f_unaccent(escaped), "%"))


def with_parent_name(stmt: Select[Any]) -> tuple[Select[Any], Any]:
    parent = aliased(Location)
    return stmt.outerjoin(parent, parent.id == Location.parent_id), parent
