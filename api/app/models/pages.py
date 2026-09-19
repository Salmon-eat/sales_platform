from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SeoPage(Base):
    """Counters and index state of a list page (spec §6: thresholds with a 14-day hysteresis)."""

    __tablename__ = "seo_pages"

    id: Mapped[int] = mapped_column(primary_key=True)
    path_key: Mapped[str] = mapped_column(String(300), unique=True)  # lang|section|category|feature|location
    lang: Mapped[str] = mapped_column(String(2))
    section_key: Mapped[str] = mapped_column(String(50))
    category_key: Mapped[str | None] = mapped_column(String(100))  # Spanish slug
    feature: Mapped[str | None] = mapped_column(String(50))
    location_slug: Mapped[str | None] = mapped_column(String(120))
    tier: Mapped[str] = mapped_column(String(20))
    active_count: Mapped[int] = mapped_column(default=0, server_default="0")
    threshold: Mapped[int] = mapped_column(default=0, server_default="0")
    indexable: Mapped[bool] = mapped_column(default=False, server_default="false")
    below_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_listing_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    title_override: Mapped[str | None] = mapped_column(String(200))
    description_override: Mapped[str | None] = mapped_column(String(400))
    recounted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ContentBlock(Base):
    __tablename__ = "content_blocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(100))
    lang: Mapped[str] = mapped_column(String(2))
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text, default="", server_default="")
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EmployerRequest(TimestampMixin, Base):
    __tablename__ = "employer_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    company: Mapped[str] = mapped_column(String(200))
    contact_name: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(320))
    messenger: Mapped[str] = mapped_column(String(20), default="phone", server_default="phone")
    text: Mapped[str] = mapped_column(Text)
    lang: Mapped[str] = mapped_column(String(2))
    status: Mapped[str] = mapped_column(String(20), default="new", server_default="new")
    consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consent_version: Mapped[str] = mapped_column(String(20))
    ip: Mapped[str | None] = mapped_column(String(45))
