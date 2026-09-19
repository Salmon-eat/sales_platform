"""Staff sign-in (admin spec §1): Google for whitelisted emails, no passwords, 30-day sessions."""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request, status

from app.api.deps import CurrentSession, CurrentUser, RedisDep, SessionDep
from app.core.config import settings
from app.core.security import GoogleTokenError, verify_google_token
from app.models import User
from app.schemas.auth import AuthConfig, DevLoginIn, GoogleLoginIn, SessionOut, UserOut
from app.services.auth import NotAllowed, allowed_staff, open_session, revoke_all

router = APIRouter(prefix="/auth", tags=["auth"])
log = logging.getLogger("bazarcito.auth")

LOGIN_WINDOW = 600  # seconds


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


async def _rate_limit(redis: RedisDep, request: Request) -> None:
    key = f"rl:login:{_client_ip(request)}"
    attempts = await redis.incr(key)
    if attempts == 1:
        await redis.expire(key, LOGIN_WINDOW)
    if attempts > settings.login_attempts_per_ip:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "too_many_attempts")


async def _session_for(session: SessionDep, request: Request, user: User) -> SessionOut:
    token, row = await open_session(
        session, user, ip=_client_ip(request), user_agent=request.headers.get("user-agent")
    )
    log.info("staff login user_id=%s", user.id)
    out = UserOut.model_validate(user, from_attributes=True)
    return SessionOut(token=token, expires_at=row.expires_at, user=out)


@router.get("/config", response_model=AuthConfig)
async def config() -> AuthConfig:
    """What the login page shows: the Google button and/or the local development form."""
    return AuthConfig(google_client_id=settings.google_client_id or None, dev_login=settings.admin_dev_login)


@router.post("/google", response_model=SessionOut)
async def google(body: GoogleLoginIn, request: Request, session: SessionDep, redis: RedisDep) -> SessionOut:
    """ID token from Google Identity Services -> session. A valid Google account whose email is not
    on the staff whitelist gets 403: without this check anyone with a Google account would get in."""
    await _rate_limit(redis, request)
    try:
        identity = await verify_google_token(body.credential)
    except GoogleTokenError as exc:
        log.warning("google token rejected: %s", exc)
        if not settings.google_client_id:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "google_not_configured") from exc
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_token") from exc
    try:
        user = await allowed_staff(session, identity.email)
    except NotAllowed as exc:
        log.warning("login refused for %s (not on the whitelist or switched off)", identity.email)
        raise HTTPException(status.HTTP_403_FORBIDDEN, "not_allowed") from exc
    if user.google_sub and user.google_sub != identity.sub:
        # the email now belongs to another Google account (e.g. deleted and re-created)
        log.warning("login refused for %s: different Google account", identity.email)
        raise HTTPException(status.HTTP_403_FORBIDDEN, "not_allowed")
    user.google_sub = identity.sub
    user.name = user.name or identity.name
    user.avatar = identity.picture or user.avatar
    return await _session_for(session, request, user)


@router.post("/dev-login", response_model=SessionOut)
async def dev_login(body: DevLoginIn, request: Request, session: SessionDep, redis: RedisDep) -> SessionOut:
    """Local development only (ADMIN_DEV_LOGIN=true, refused in production): whitelisted email, no Google."""
    if not settings.admin_dev_login or settings.is_production:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not Found")
    await _rate_limit(redis, request)
    try:
        user = await allowed_staff(session, body.email)
    except NotAllowed as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "not_allowed") from exc
    return await _session_for(session, request, user)


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user, from_attributes=True)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(row: CurrentSession, session: SessionDep) -> None:
    row.revoked_at = datetime.now(UTC)
    await session.commit()


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(user: CurrentUser, session: SessionDep) -> None:
    """ "Sign out on all devices", e.g. after losing a phone."""
    count = await revoke_all(session, user.id)
    log.info("staff logout-all user_id=%s sessions=%s", user.id, count)
