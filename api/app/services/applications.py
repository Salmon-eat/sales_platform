"""Applications without registration (spec §10).

Done here: E.164 phone, consent with policy version, rate limit per IP, 24h duplicate -> note.
Site chat (the orange window): a conversation with a token kept by the browser; the phone is optional.
"""

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Application, ApplicationMessage, ApplicationNote, Category, Listing, Location
from app.schemas.application import ApplicationCreated, ApplicationIn
from app.services import cv, questions

DUPLICATE_WINDOW = timedelta(hours=24)
CHAT_MESSAGES_PER_HOUR = 40


async def check_rate_limit(redis: Redis, ip: str | None) -> None:
    if not ip:
        return
    key = f"rl:applications:{ip}"
    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 3600)
    except RedisError:
        return  # never lose an application because Redis is down
    if count > settings.applications_per_ip_per_hour:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many applications, try again later")


async def create_application(
    session: AsyncSession, redis: Redis, data: ApplicationIn, ip: str | None
) -> ApplicationCreated:
    await check_rate_limit(redis, ip)

    if data.category_id is not None and await session.get(Category, data.category_id) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown category")
    location_id = None
    if data.location_slug:
        location_id = await session.scalar(select(Location.id).where(Location.slug == data.location_slug))

    answers: dict = {"in_spain": data.in_spain, "comment": data.comment}
    if data.listing_id is not None and data.questions:
        listing_questions = await session.scalar(
            select(Listing.questions).where(Listing.id == data.listing_id)
        )
        if listed := questions.answers_for(listing_questions or [], data.questions):
            answers["questions"] = listed
    now = datetime.now(UTC)

    if data.channel == "chat":
        return await _start_chat(session, data, answers, location_id, ip, now)

    duplicate = await session.scalar(
        select(Application)
        .where(
            Application.phone == data.phone,
            Application.listing_id.is_not_distinct_from(data.listing_id),
            Application.category_id.is_not_distinct_from(data.category_id),
            Application.created_at > now - DUPLICATE_WINDOW,
        )
        .order_by(Application.created_at.desc())
        .limit(1)
    )
    if duplicate is not None:
        details = ", ".join(
            f"{k}: {v}"
            for k, v in {"ім'я": data.name, "месенджер": data.messenger, **answers, "questions": None}.items()
            if v not in (None, "")
        )
        session.add(ApplicationNote(application_id=duplicate.id, text=f"Повторна заявка ({details})"))
        await session.commit()
        return ApplicationCreated(
            id=duplicate.id, duplicate=True, cv_token=await cv.new_token(redis, duplicate.id)
        )

    application = Application(
        listing_id=data.listing_id,
        category_id=data.category_id,
        location_id=location_id,
        name=data.name,
        phone=data.phone,
        messenger=data.messenger,
        answers=answers,
        lang=data.lang,
        source="site",
        utm=data.utm,
        consent_at=now,
        consent_version=settings.privacy_policy_version,
        ip=ip,
    )
    session.add(application)
    await session.commit()
    return ApplicationCreated(
        id=application.id, duplicate=False, cv_token=await cv.new_token(redis, application.id)
    )


async def _start_chat(
    session: AsyncSession,
    data: ApplicationIn,
    answers: dict,
    location_id: int | None,
    ip: str | None,
    now: datetime,
) -> ApplicationCreated:
    """A message from the orange window opens a conversation; the phone is optional there, so the
    reply can also come back into the window (the browser keeps the token)."""
    application = Application(
        category_id=data.category_id,
        location_id=location_id,
        name=data.name,
        phone=data.phone,
        messenger=data.messenger,
        answers=answers,
        lang=data.lang,
        source="chat",
        utm=data.utm,
        consent_at=now,
        consent_version=settings.privacy_policy_version,
        ip=ip,
        chat_token=secrets.token_urlsafe(24),
    )
    session.add(application)
    await session.flush()
    session.add(ApplicationMessage(application_id=application.id, author="visitor", text=data.comment or ""))
    await session.commit()
    return ApplicationCreated(id=application.id, duplicate=False, chat_token=application.chat_token)


async def chat_by_token(session: AsyncSession, token: str) -> Application:
    application = await session.scalar(select(Application).where(Application.chat_token == token))
    if application is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat not found")
    return application


async def chat_messages(session: AsyncSession, application_id: int) -> list[ApplicationMessage]:
    return list(
        (
            await session.scalars(
                select(ApplicationMessage)
                .where(ApplicationMessage.application_id == application_id)
                .order_by(ApplicationMessage.created_at, ApplicationMessage.id)
            )
        ).all()
    )


async def add_visitor_message(
    session: AsyncSession, redis: Redis, application: Application, text: str
) -> None:
    key = f"rl:chat:{application.id}"
    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 3600)
    except RedisError:
        count = 0
    if count > CHAT_MESSAGES_PER_HOUR:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many messages, try again later")
    session.add(ApplicationMessage(application_id=application.id, author="visitor", text=text))
    # a new message brings a closed conversation back to the managers' queue
    if application.status in ("done", "rejected"):
        application.status = "new"
    application.updated_at = datetime.now(UTC)
    await session.commit()
