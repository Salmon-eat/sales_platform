"""Staff sessions: whitelist check, session creation and revocation (admin spec §1)."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import new_session_token
from app.models import User, UserSession


class NotAllowed(Exception):
    """The email is not on the staff whitelist or its access is switched off."""


async def allowed_staff(session: AsyncSession, email: str) -> User:
    """A signed-in Google account is not enough: the email must be an active manager/admin row."""
    user = await session.scalar(select(User).where(User.email == email.lower()))
    if user is None or not user.is_active or not user.is_staff:
        raise NotAllowed(email)
    return user


async def open_session(
    session: AsyncSession, user: User, *, ip: str | None, user_agent: str | None
) -> tuple[str, UserSession]:
    token, token_hash = new_session_token()
    now = datetime.now(UTC)
    row = UserSession(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=now + timedelta(days=settings.session_days),
        last_seen_at=now,
        ip=ip,
        user_agent=(user_agent or "")[:300] or None,
    )
    session.add(row)
    user.last_login_at = now
    await session.commit()
    return token, row


async def revoke_all(session: AsyncSession, user_id: int) -> int:
    """ "Sign out on all devices" and switching access off."""
    result = await session.execute(
        update(UserSession)
        .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    await session.commit()
    return result.rowcount or 0
