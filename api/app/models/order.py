"""What somebody bought, for how much, and whether it has been switched on yet."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

ORDER_STATUSES = ("new", "paid", "failed", "refunded", "cancelled")
PROVIDERS = ("card", "manual")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    # no foreign key on purpose: the receipt outlives the ad it paid for
    listing_id: Mapped[int | None]
    company_id: Mapped[int | None]
    product: Mapped[str] = mapped_column(String(30))
    days: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")
    # in cents; money is never a float
    amount: Mapped[int]
    currency: Mapped[str] = mapped_column(String(3), default="EUR", server_default="EUR")
    status: Mapped[str] = mapped_column(String(20), default="new", server_default="new")
    provider: Mapped[str] = mapped_column(String(20), default="card", server_default="card")
    provider_ref: Mapped[str | None] = mapped_column(String(200))
    note: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # when what was bought was actually switched on, so nothing is applied twice
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
