"""The visitor's own area: sign in without a password, profile, saved listings.

Separate from /v1/auth, which is the team's sign-in: there the email must be on the staff whitelist,
here anyone can create an account.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentSession, CurrentUser, RedisDep, SessionDep
from app.core.config import settings
from app.core.ratelimit import client_ip
from app.core.security import GoogleTokenError, verify_google_token
from app.models import Favorite, User
from app.schemas.account import (
    AccountOut,
    AccountSession,
    AccountUpdate,
    CodeIn,
    EmailIn,
    FavoritesIn,
    GoogleLoginIn,
    TelegramLoginIn,
)
from app.services import accounts
from app.services.auth import open_session, revoke_all

router = APIRouter(prefix="/account", tags=["account"])


async def _sign_in(session: AsyncSession, request: Request, user: User) -> AccountSession:
    token, row = await open_session(
        session, user, ip=client_ip(request), user_agent=request.headers.get("user-agent")
    )
    return AccountSession(
        token=token,
        expires_at=row.expires_at,
        user=AccountOut.model_validate(user, from_attributes=True),
    )


@router.post("/code", status_code=status.HTTP_202_ACCEPTED)
async def request_code(body: EmailIn, redis: RedisDep) -> dict[str, bool]:
    """Send a sign-in code. The answer is the same whether or not the address has an account."""
    await accounts.send_code(redis, body.email, body.lang)
    return {"sent": True}


@router.post("/session", response_model=AccountSession)
async def sign_in_with_code(
    body: CodeIn, request: Request, session: SessionDep, redis: RedisDep
) -> AccountSession:
    await accounts.check_code(redis, body.email, body.code)
    user = await accounts.get_or_create(session, email=body.email, lang=body.lang)
    return await _sign_in(session, request, user)


@router.post("/google", response_model=AccountSession)
async def sign_in_with_google(body: GoogleLoginIn, request: Request, session: SessionDep) -> AccountSession:
    if not settings.google_client_id:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "google_not_configured")
    try:
        identity = await verify_google_token(body.credential)
    except GoogleTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_token") from exc
    user = await accounts.get_or_create(
        session,
        email=identity.email,
        name=identity.name,
        lang=body.lang,
        google_sub=identity.sub,
        avatar=identity.picture,
    )
    return await _sign_in(session, request, user)


@router.post("/telegram", response_model=AccountSession)
async def sign_in_with_telegram(
    body: TelegramLoginIn, request: Request, session: SessionDep
) -> AccountSession:
    """The Telegram widget hands over the person's data signed with our login bot's token."""
    accounts.check_telegram(body.model_dump(exclude={"lang"}, exclude_none=True))
    user = await accounts.from_telegram(
        session,
        telegram_id=body.id,
        name=" ".join(filter(None, [body.first_name, body.last_name])) or None,
        username=body.username,
        avatar=body.photo_url,
        lang=body.lang,
    )
    return await _sign_in(session, request, user)


@router.get("/me", response_model=AccountOut)
async def me(user: CurrentUser) -> AccountOut:
    return AccountOut.model_validate(user, from_attributes=True)


@router.patch("/me", response_model=AccountOut)
async def update_me(body: AccountUpdate, user: CurrentUser, session: SessionDep) -> AccountOut:
    if body.name is not None:
        user.name = body.name or None
    if body.phone is not None:
        user.phone = body.phone
    if body.lang is not None:
        user.lang = body.lang
    if body.notify_email is not None:
        user.notify_email = body.notify_email
    if body.notify_telegram is not None:
        user.notify_telegram = body.notify_telegram
    await session.commit()
    return AccountOut.model_validate(user, from_attributes=True)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(user: CurrentUser, session: SessionDep) -> None:
    """The visitor deletes their account: contacts are wiped and every session is closed."""
    if user.is_staff:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "staff_account")
    await revoke_all(session, user.id)
    await accounts.delete_account(session, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(row: CurrentSession, session: SessionDep) -> None:
    row.revoked_at = datetime.now(UTC)
    await session.commit()


@router.get("/favorites", response_model=list[int])
async def favorites(user: CurrentUser, session: SessionDep) -> list[int]:
    rows = await session.scalars(
        select(Favorite.listing_id).where(Favorite.user_id == user.id).order_by(Favorite.created_at.desc())
    )
    return list(rows.all())


@router.put("/favorites", response_model=list[int])
async def save_favorites(body: FavoritesIn, user: CurrentUser, session: SessionDep) -> list[int]:
    """The account's saved listings; signing in merges what the browser kept while the person was a guest."""
    current = set(
        (await session.scalars(select(Favorite.listing_id).where(Favorite.user_id == user.id))).all()
    )
    wanted = set(body.ids)
    for listing_id in wanted - current:
        session.add(Favorite(user_id=user.id, listing_id=listing_id))
    if body.replace and (gone := current - wanted):
        await session.execute(
            delete(Favorite).where(Favorite.user_id == user.id, Favorite.listing_id.in_(gone))
        )
    await session.commit()
    return await favorites(user, session)
