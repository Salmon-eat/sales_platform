"""A firm in the directory: it stays, collects reviews and is found by what it does."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

COMPANY_STATUSES = ("draft", "pending", "active", "rejected", "hidden")
MAX_ABOUT = 4000
MAX_CATEGORIES = 8


class Company(TimestampMixin, Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    # the address of the page: /{lang}/firmy/{slug}
    slug: Mapped[str] = mapped_column(String(140), unique=True)
    # the language the firm wrote its own text in; we never machine-translate it
    lang: Mapped[str] = mapped_column(String(2), default="es", server_default="es")
    about: Mapped[str] = mapped_column(Text, default="", server_default="")
    city_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id", ondelete="SET NULL"))
    address: Mapped[str | None] = mapped_column(String(200))
    hours: Mapped[str | None] = mapped_column(String(200))
    # what the firm does, as taxonomy category ids: the catalogue filters like the rest of the site
    category_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer), default=list, server_default="{}")

    phone: Mapped[str | None] = mapped_column(String(20))
    whatsapp: Mapped[str | None] = mapped_column(String(20))
    telegram: Mapped[str | None] = mapped_column(String(64))
    email: Mapped[str | None] = mapped_column(String(320))
    site: Mapped[str | None] = mapped_column(String(200))
    logo: Mapped[str | None] = mapped_column(String(200))

    status: Mapped[str] = mapped_column(String(20), default="draft", server_default="draft")
    reject_reason: Mapped[str | None] = mapped_column(String(40))
    reject_note: Mapped[str | None] = mapped_column(Text)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    moderated_by: Mapped[int | None]
    moderated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
