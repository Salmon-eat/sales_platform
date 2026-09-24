from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, str_enum
from app.models.enums import UserRole


class User(TimestampMixin, Base):
    """Staff are a whitelist: a manager/admin row with the email must exist before Google sign-in works."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str | None] = mapped_column(String(320), unique=True)
    name: Mapped[str | None] = mapped_column(String(200))
    avatar: Mapped[str | None] = mapped_column(String(500))
    lang: Mapped[str] = mapped_column(String(2), default="es", server_default="es")
    role: Mapped[UserRole] = mapped_column(
        str_enum(UserRole), default=UserRole.USER, server_default=UserRole.USER
    )
    # Google account bound on the first sign-in: a re-created account with the same email is refused.
    google_sub: Mapped[str | None] = mapped_column(String(64), unique=True)
    phone: Mapped[str | None] = mapped_column(String(20))
    # signed in with Telegram: there is no email there, the account is keyed by the Telegram id
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    telegram_username: Mapped[str | None] = mapped_column(String(64))
    # how we may tell them a message is waiting; both on until they say otherwise
    notify_email: Mapped[bool] = mapped_column(default=True, server_default="true")
    notify_telegram: Mapped[bool] = mapped_column(default=True, server_default="true")
    # Access is switched off, never deleted, so the name stays in notes and history (admin spec §1).
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # the visitor deleted their account: contacts wiped, the row stays for the statistics
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    @property
    def is_staff(self) -> bool:
        return self.role in (UserRole.MANAGER, UserRole.ADMIN)

    @property
    def has_telegram(self) -> bool:
        """Signed in with Telegram at some point, so the bot has someone to write to."""
        return self.telegram_id is not None


class Favorite(Base):
    """A listing saved by a signed-in visitor (guests keep them in the browser until they sign in)."""

    __tablename__ = "favorites"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    listing_id: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserSession(Base):
    """Server-side session: the cookie holds a random token, the table only its SHA-256."""

    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ip: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(300))
