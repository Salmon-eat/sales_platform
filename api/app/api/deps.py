from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.redis import get_redis
from app.core.security import hash_token
from app.models import User, UserRole, UserSession

SessionDep = Annotated[AsyncSession, Depends(get_session)]
RedisDep = Annotated[Redis, Depends(get_redis)]

_bearer = HTTPBearer(auto_error=False)

LAST_SEEN_EVERY = timedelta(minutes=5)  # do not write on every request


async def get_current_session(
    request: Request,
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> UserSession:
    """The session token comes only in the Authorization header, never from a cookie: a forged
    cross-site request cannot carry it (CSRF). The Next.js server reads the httpOnly cookie and
    adds the header; the browser never talks to /v1/admin itself."""
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    now = datetime.now(UTC)
    row = await session.scalar(
        select(UserSession).where(
            UserSession.token_hash == hash_token(credentials.credentials),
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > now,
        )
    )
    user = await session.get(User, row.user_id) if row else None
    if row is None or user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    if now - row.last_seen_at > LAST_SEEN_EVERY:
        row.last_seen_at = now
        await session.commit()
    request.state.user_id = user.id  # for the admin action log (app.main)
    return row


CurrentSession = Annotated[UserSession, Depends(get_current_session)]

ADMIN_LANGS = ("uk", "ru", "en", "es")


def get_admin_lang(request: Request) -> str:
    """Admin UI language (the web app sends it as Accept-Language): names of professions, cities and
    listing titles in admin lists come back in it."""
    code = (request.headers.get("accept-language") or "")[:2].lower()
    return code if code in ADMIN_LANGS else "uk"


AdminLang = Annotated[str, Depends(get_admin_lang)]


async def get_current_user(row: CurrentSession, session: SessionDep) -> User:
    user = await session.get(User, row.user_id)
    assert user is not None  # checked in get_current_session
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_staff(user: CurrentUser) -> User:
    """Managers and admins: applications, candidates, listings, employer requests, export."""
    if not user.is_staff:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Staff only")
    return user


async def require_admin(user: CurrentUser) -> User:
    """Admins only: dictionaries, content, SEO, users, GDPR deletion."""
    if user.role != UserRole.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin only")
    return user
