from datetime import date, datetime
from typing import Any

from geoalchemy2 import Geography
from sqlalchemy import Date, DateTime, ForeignKey, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

# a visitor's ad goes draft -> pending (waiting for a manager) -> active or rejected
LISTING_STATUSES = ("draft", "pending", "active", "paused", "expired", "closed", "rejected")
SALARY_PERIODS = ("hour", "day", "week", "month")
PRICE_PERIODS = ("hour", "day", "week", "month")
# fixed: a number; negotiable: a number, open to offers; free: giving it away; from: "starting at"
PRICE_KINDS = ("fixed", "negotiable", "free", "from")
MAX_PHOTOS = 10
SCHEDULES = ("full", "part", "weekends", "shifts")
CONTRACTS = ("indefinido", "temporal", "fijo_discontinuo")
# private: posted by a visitor about their own thing, not by a company
SOURCES = ("agency", "partner", "employer", "private")
LOCATION_SCOPES = ("local", "spain_wide")


class Listing(TimestampMixin, Base):
    __tablename__ = "listings"

    id: Mapped[int] = mapped_column(primary_key=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id", ondelete="RESTRICT"))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"))
    # always a municipality; NULL only for location_scope = spain_wide
    location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id", ondelete="RESTRICT"))
    location_scope: Mapped[str] = mapped_column(String(20), default="local", server_default="local")
    # own point (warehouse, polígono) or a copy of the municipality point for radius search
    geog: Mapped[Any | None] = mapped_column(Geography("POINT", srid=4326, spatial_index=False))
    status: Mapped[str] = mapped_column(String(20), default="draft", server_default="draft")
    original_lang: Mapped[str] = mapped_column(String(2))

    salary_min: Mapped[int | None]
    salary_max: Mapped[int | None]
    salary_period: Mapped[str | None] = mapped_column(String(10))
    salary_monthly_min: Mapped[int | None]

    # outside the jobs section the price is what people look at first
    price: Mapped[int | None]
    price_period: Mapped[str | None] = mapped_column(String(10))  # null = one-off, else month/day/hour
    # fixed | negotiable | free | from
    price_kind: Mapped[str] = mapped_column(String(12), default="fixed", server_default="fixed")
    currency: Mapped[str] = mapped_column(String(3), default="EUR", server_default="EUR")

    housing: Mapped[bool] = mapped_column(default=False, server_default="false")
    no_language: Mapped[bool] = mapped_column(default=False, server_default="false")
    no_experience: Mapped[bool] = mapped_column(default=False, server_default="false")
    schedule: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, server_default="{}")
    contract: Mapped[str | None] = mapped_column(String(20))
    # hiring details shown on the card page: "5 places", "from 1 October", "urgent", "for 3 months"
    vacancies: Mapped[int | None] = mapped_column(SmallInteger)
    start_date: Mapped[date | None] = mapped_column(Date)
    is_urgent: Mapped[bool] = mapped_column(default=False, server_default="false")
    duration_months: Mapped[int | None] = mapped_column(SmallInteger)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    contact: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    # optional questions to the candidate (app.services.questions): [{"key": "licence_c"}, ...]
    questions: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, server_default="[]")

    source: Mapped[str] = mapped_column(String(20), default="agency", server_default="agency")
    employer_name: Mapped[str | None] = mapped_column(String(200))
    is_pinned: Mapped[bool] = mapped_column(default=False, server_default="false")

    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    # posted by a visitor (null = by the team); every visitor's ad is checked before it appears
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    # what the automatic check noticed when the ad was sent in: the moderator sees it first
    flags: Mapped[list[str]] = mapped_column(JSONB, default=list, server_default="[]")
    moderated_by: Mapped[int | None]
    moderated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reject_reason: Mapped[str | None] = mapped_column(String(40))
    reject_note: Mapped[str | None] = mapped_column(Text)
    bumped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    promoted_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # paid colour in the lists, until this moment
    highlighted_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    photos: Mapped[list["ListingPhoto"]] = relationship(
        back_populates="listing", cascade="all, delete-orphan", order_by="ListingPhoto.sort"
    )

    translations: Mapped[list["ListingTranslation"]] = relationship(
        lazy="raise", cascade="all, delete-orphan", order_by="ListingTranslation.lang"
    )


class ListingPhoto(Base):
    """A photo of the ad. The file lives on the server; the row keeps its place in the gallery."""

    __tablename__ = "listing_photos"

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), index=True)
    path: Mapped[str] = mapped_column(String(200))
    width: Mapped[int]
    height: Mapped[int]
    size: Mapped[int]
    sort: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    listing: Mapped["Listing"] = relationship(back_populates="photos")


class ListingTranslation(TimestampMixin, Base):
    __tablename__ = "listing_translations"

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"))
    lang: Mapped[str] = mapped_column(String(2))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    requirements: Mapped[str | None] = mapped_column(Text)
    conditions: Mapped[str | None] = mapped_column(Text)
    # without the id; the public URL is /{lang}/{section}/oferta/{slug}-{id}
    slug: Mapped[str] = mapped_column(String(160))
    is_machine: Mapped[bool] = mapped_column(default=False, server_default="false")
