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


class SearchWord(Base):
    """A word that really appears in the ads, in any language; the site's own vocabulary.

    It is what a misspelled or differently-ended word is repaired against, so no correction can ever
    point at something nobody wrote.
    """

    __tablename__ = "search_words"

    word: Mapped[str] = mapped_column(String(60), primary_key=True)
    hits: Mapped[int] = mapped_column(default=1, server_default="1")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SynonymProposal(Base):
    """A word that found nothing, and the category people opened after searching for it.

    This is how the dictionary grows without anybody editing a file: the nightly job watches what
    visitors typed and where they went next. Strong, repeated evidence is applied on its own; the rest
    waits for a person to agree, because a wrong synonym is worse than a missing one — it attaches
    itself to every ad in the category.
    """

    __tablename__ = "synonym_proposals"

    id: Mapped[int] = mapped_column(primary_key=True)
    word: Mapped[str] = mapped_column(String(60))
    lang: Mapped[str] = mapped_column(String(2))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"))
    searches: Mapped[int] = mapped_column(default=0, server_default="0")
    # how many of those searches ended with somebody opening an ad of that category
    opened: Mapped[int] = mapped_column(default=0, server_default="0")
    status: Mapped[str] = mapped_column(String(10), default="new", server_default="new")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_by: Mapped[int | None]


class SearchMiss(Base):
    __tablename__ = "search_misses"

    id: Mapped[int] = mapped_column(primary_key=True)
    lang: Mapped[str] = mapped_column(String(2))
    section: Mapped[str] = mapped_column(String(50), default="", server_default="")
    q: Mapped[str] = mapped_column(String(200))
    hits: Mapped[int] = mapped_column(default=1, server_default="1")
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
