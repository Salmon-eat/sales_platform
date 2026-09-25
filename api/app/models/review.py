"""What a buyer says about a seller after they have dealt with each other."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, SmallInteger, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

MAX_REVIEW = 1000
MAX_REPLY = 1000


class SellerReview(TimestampMixin, Base):
    __tablename__ = "seller_reviews"
    __table_args__ = (
        UniqueConstraint("seller_id", "author_id", name="uq_seller_reviews_seller_author"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    # which ad it was about; the ad may be gone by the time anybody reads the review
    listing_id: Mapped[int | None] = mapped_column(ForeignKey("listings.id", ondelete="SET NULL"))
    rating: Mapped[int] = mapped_column(SmallInteger)
    text: Mapped[str] = mapped_column(Text, default="", server_default="")
    reply: Mapped[str | None] = mapped_column(Text)
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # taken down by the team after a complaint; the row stays so the rating history is honest
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
