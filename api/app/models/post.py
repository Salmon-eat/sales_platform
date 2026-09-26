"""An article: written by the team, in one language, by hand."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

POST_STATUSES = ("draft", "published")
MAX_BODY = 40_000


class Post(TimestampMixin, Base):
    __tablename__ = "posts"
    __table_args__ = (UniqueConstraint("lang", "slug", name="uq_posts_lang_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(160))
    lang: Mapped[str] = mapped_column(String(2), default="es", server_default="es")
    title: Mapped[str] = mapped_column(String(200))
    # the line under the title in the list and in search results
    excerpt: Mapped[str] = mapped_column(String(300), default="", server_default="")
    body: Mapped[str] = mapped_column(Text, default="", server_default="")
    cover: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="draft", server_default="draft")
    author_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
