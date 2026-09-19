from datetime import datetime
from typing import Any

from geoalchemy2 import Geography
from sqlalchemy import Computed, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

LOCATION_LEVELS = ("comunidad", "provincia", "municipio", "localidad")

SEARCH_TEXT_SQL = (
    "public.f_unaccent(lower("
    "coalesce(names->>'es', '') || ' ' || coalesce(names->>'en', '') || ' ' || "
    "coalesce(names->>'uk', '') || ' ' || coalesce(names->>'ru', '') || ' ' || "
    "public.f_text_join(aliases)))"
)


class Location(Base):
    """Spain as a tree with INE codes: comunidad -> provincia -> municipio.

    Below a municipality sit localidades (villages, pedanías, parroquias from GeoNames). They are for
    search/autocomplete and a listing's own point only; listings and URLs use the municipality (spec §3).
    """

    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    level: Mapped[str] = mapped_column(String(20))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id", ondelete="RESTRICT"))
    # comunidad: CODAUTO (2), provincia: CPRO (2), municipio: CPRO+CMUN (5), localidad: none
    ine_code: Mapped[str | None] = mapped_column(String(5))
    geonames_id: Mapped[int | None] = mapped_column(unique=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    names: Mapped[dict[str, str]] = mapped_column(JSONB)
    aliases: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, server_default="{}")
    population: Mapped[int | None]
    geog: Mapped[Any | None] = mapped_column(Geography("POINT", srid=4326, spatial_index=False))
    search_text: Mapped[str] = mapped_column(Text, Computed(SEARCH_TEXT_SQL, persisted=True), deferred=True)


class SlugHistory(Base):
    __tablename__ = "slug_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(20))  # section | category | location
    entity_id: Mapped[int]
    lang: Mapped[str] = mapped_column(String(2))  # "*" for locations
    old_slug: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
