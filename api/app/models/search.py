from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ListingSearch(Base):
    """Search document of a listing; rebuilt by DB triggers (migration 0005), never written by the app."""

    __tablename__ = "listing_search"

    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), primary_key=True)
    tsv_title: Mapped[str] = mapped_column(TSVECTOR)
    tsv_category: Mapped[str] = mapped_column(TSVECTOR)
    tsv_location: Mapped[str] = mapped_column(TSVECTOR)
    tsv_body: Mapped[str] = mapped_column(TSVECTOR)
    tsv_all: Mapped[str] = mapped_column(TSVECTOR)
    trgm_text: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SearchMiss(Base):
    __tablename__ = "search_misses"

    id: Mapped[int] = mapped_column(primary_key=True)
    lang: Mapped[str] = mapped_column(String(2))
    section: Mapped[str] = mapped_column(String(50), default="", server_default="")
    q: Mapped[str] = mapped_column(String(200))
    hits: Mapped[int] = mapped_column(default=1, server_default="1")
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
