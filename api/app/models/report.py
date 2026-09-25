"""A complaint about an ad: the reader's way of saying "look at this one"."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# why an ad is being reported; the admin shows these as words in the staff member's language
REPORT_REASONS = (
    "fraud",
    "prohibited",
    "spam",
    "wrong_category",
    "duplicate",
    "offensive",
    "sold",
    "other",
)
REPORT_STATUSES = ("new", "accepted", "rejected")
MAX_NOTE = 500


class ListingReport(Base):
    __tablename__ = "listing_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), index=True)
    # null: reported by someone who was not signed in
    reporter_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reason: Mapped[str] = mapped_column(String(30))
    note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="new", server_default="new")
    ip: Mapped[str | None] = mapped_column(String(45))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reviewed_by: Mapped[int | None]
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
