from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

EVENT_TYPES = (
    "page_view",
    "page_leave",
    "listing_view",
    "apply_open",
    "apply_sent",
    "search",
    "contact_click",
    "link_click",
)
DEVICES = ("mobile", "tablet", "desktop")
LINK_CHANNELS = (
    "blogger",
    "instagram",
    "tiktok",
    "facebook",
    "telegram",
    "youtube",
    "google",
    "partner",
    "other",
)


class AnalyticsEvent(Base):
    """Own anonymous site analytics: random visitor/session ids from the browser, no IP, no user agent.

    source/campaign are the visit's attribution (utm or referrer), copied onto every event of the
    session so reports need no joins.
    """

    __tablename__ = "analytics_events"
    __table_args__ = (
        Index("ix_analytics_events_type_created", "type", "created_at"),
        Index("ix_analytics_events_session", "session"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    visitor: Mapped[str] = mapped_column(String(32))
    session: Mapped[str] = mapped_column(String(32))
    type: Mapped[str] = mapped_column(String(20))
    path: Mapped[str] = mapped_column(String(300), default="", server_default="")
    lang: Mapped[str | None] = mapped_column(String(2))
    device: Mapped[str] = mapped_column(String(10), default="desktop", server_default="desktop")
    source: Mapped[str] = mapped_column(String(40), default="direct", server_default="direct")
    campaign: Mapped[str | None] = mapped_column(String(60))
    listing_id: Mapped[int | None]
    duration_ms: Mapped[int | None]
    props: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")


class TrackedLink(TimestampMixin, Base):
    """An ad link for a blogger or a channel: /go/<code> -> target page with utm_campaign=<code>."""

    __tablename__ = "tracked_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(60), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    channel: Mapped[str] = mapped_column(String(20))
    target_path: Mapped[str] = mapped_column(String(300))
    cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
