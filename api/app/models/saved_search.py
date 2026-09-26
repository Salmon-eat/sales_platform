"""A search somebody asked to be told about."""

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

MAX_SEARCHES = 20


class SavedSearch(Base):
    __tablename__ = "saved_searches"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(200))
    lang: Mapped[str] = mapped_column(String(2), default="es", server_default="es")
    section_key: Mapped[str | None] = mapped_column(String(50))
    category_slug: Mapped[str | None] = mapped_column(String(120))
    location_slug: Mapped[str | None] = mapped_column(String(120))
    # everything else exactly as it stood in the address bar: {"q": "piso", "price_max": "900"}
    params: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    notify: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    # the highest ad id this person has already been told about
    last_seen_id: Mapped[int] = mapped_column(default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
