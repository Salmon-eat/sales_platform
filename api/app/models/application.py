from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

APPLICATION_STATUSES = ("new", "in_progress", "done", "rejected")
MESSENGERS = ("phone", "telegram", "whatsapp", "viber")


class Application(TimestampMixin, Base):
    """A candidate's request: for a listing, a category, or just "call me about work" (spec §8, §10)."""

    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int | None]  # FK is added together with the listings table (stage 2)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"))
    location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id", ondelete="SET NULL"))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(20))  # E.164; a site chat message may come without one
    chat_token: Mapped[str | None] = mapped_column(String(64), unique=True)
    messenger: Mapped[str] = mapped_column(String(20))
    answers: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    lang: Mapped[str] = mapped_column(String(2))
    source: Mapped[str] = mapped_column(String(10), default="site", server_default="site")
    utm: Mapped[dict[str, str]] = mapped_column(JSONB, default=dict, server_default="{}")
    status: Mapped[str] = mapped_column(String(20), default="new", server_default="new")
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consent_version: Mapped[str] = mapped_column(String(20))
    ip: Mapped[str | None] = mapped_column(String(45))
    # personal data erased (on request or after the retention period); the statistics stay
    anonymized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # source = 'bot': the application number in the Telegram bot and what the bot knows about it
    bot_app_id: Mapped[int | None] = mapped_column(unique=True)
    bot: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")


class ApplicationMessage(Base):
    """A conversation: the site chat (orange window) or the Telegram bot; staff reply from the card."""

    __tablename__ = "application_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), index=True)
    author: Mapped[str] = mapped_column(String(10))  # visitor | staff | note (the team's note in Telegram)
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    author_name: Mapped[str | None] = mapped_column(String(120))  # a manager who wrote in Telegram
    text: Mapped[str] = mapped_column(Text)
    content_type: Mapped[str | None] = mapped_column(String(20))  # Telegram: text, photo, voice...
    bot_message_id: Mapped[int | None] = mapped_column(unique=True)
    delivery: Mapped[str | None] = mapped_column(String(10))  # Telegram: pending | delivered | failed
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ApplicationFile(Base):
    """The candidate's CV. Kept in the database (backed up with it); only staff can download it."""

    __tablename__ = "application_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(200))
    content_type: Mapped[str] = mapped_column(String(100))
    size: Mapped[int]
    data: Mapped[bytes] = mapped_column(LargeBinary, deferred=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BotOutgoing(Base):
    """Replies and status changes made in the admin for bot applications; the bot takes them in id order."""

    __tablename__ = "bot_outgoing"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(10))  # message | status
    message_id: Mapped[int | None] = mapped_column(ForeignKey("application_messages.id", ondelete="CASCADE"))
    status: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ApplicationNote(Base):
    __tablename__ = "application_notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id", ondelete="CASCADE"))
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
