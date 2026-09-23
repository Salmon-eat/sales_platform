"""Visitor accounts: sign in with a code sent by email, or with Google. No passwords anywhere.

The code lives in Redis for ten minutes as a hash, with a limit on tries and on how often a new one can be
asked for. The account itself is an ordinary `users` row with role 'user'; the session is the same
server-side session the team uses, only under a different cookie on the site.
"""

import hashlib
import hmac
import logging
import secrets
from datetime import UTC, datetime

from fastapi import HTTPException, status
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import User
from app.models.enums import UserRole
from app.services import mail

log = logging.getLogger("bazarcito.accounts")

CODE_TTL = 600  # ten minutes
MAX_TRIES = 5
RESEND_AFTER = 60  # seconds between two codes for the same address
CODES_PER_DAY = 10

SUBJECT = {
    "es": "Tu código de acceso a Citobazar",
    "en": "Your Citobazar sign-in code",
    "uk": "Ваш код входу на Citobazar",
    "ru": "Ваш код входа на Citobazar",
}
BODY = {
    "es": "Tu código es {code}. Caduca en 10 minutos.\n\nSi no lo has pedido, ignora este mensaje.",
    "en": "Your code is {code}. It expires in 10 minutes.\n\nIf you did not ask for it, ignore this email.",
    "uk": "Ваш код: {code}. Він дійсний 10 хвилин.\n\nЯкщо ви його не замовляли, просто проігноруйте лист.",
    "ru": "Ваш код: {code}. Он действует 10 минут.\n\nЕсли вы его не запрашивали, проигнорируйте письмо.",
}


def _key(email: str) -> str:
    return f"login:{email}"


def _hash(email: str, code: str) -> str:
    return hashlib.sha256(f"{email}:{code}".encode()).hexdigest()


async def send_code(redis: Redis, email: str, lang: str) -> None:
    """A six-digit code by email. The answer never says whether the address is known to us."""
    email = email.lower().strip()
    code = f"{secrets.randbelow(1_000_000):06d}"
    try:
        if await redis.ttl(_key(email)) > CODE_TTL - RESEND_AFTER:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "wait_before_resend")
        day_key = f"login:day:{email}"
        sent_today = await redis.incr(day_key)
        if sent_today == 1:
            await redis.expire(day_key, 86400)
        if sent_today > CODES_PER_DAY:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "too_many_codes")
        await redis.hset(_key(email), mapping={"hash": _hash(email, code), "tries": 0})
        await redis.expire(_key(email), CODE_TTL)
    except RedisError as exc:
        log.error("redis is down, cannot start a sign-in: %r", exc)
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "try_again_later") from exc

    text = BODY.get(lang, BODY["es"]).format(code=code)
    await mail.send(email, SUBJECT.get(lang, SUBJECT["es"]), text)


async def check_code(redis: Redis, email: str, code: str) -> None:
    email = email.lower().strip()
    try:
        data = await redis.hgetall(_key(email))
        if not data:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "code_expired")
        if int(data.get("tries", 0)) >= MAX_TRIES:
            await redis.delete(_key(email))
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "too_many_tries")
        if not secrets.compare_digest(data.get("hash", ""), _hash(email, code.strip())):
            await redis.hincrby(_key(email), "tries", 1)
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "wrong_code")
        await redis.delete(_key(email))
    except RedisError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "try_again_later") from exc


async def get_or_create(
    session: AsyncSession,
    *,
    email: str,
    name: str | None = None,
    lang: str = "es",
    google_sub: str | None = None,
    avatar: str | None = None,
) -> User:
    """The visitor's account. An email that belongs to the team signs that person in as staff instead."""
    email = email.lower().strip()
    user = await session.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            email=email,
            name=name,
            lang=lang,
            role=UserRole.USER,
            avatar=avatar,
            google_sub=google_sub,
            is_active=True,  # set here: the column default only lands on the insert
        )
        session.add(user)
    else:
        if user.deleted_at is not None:  # signing in again brings a deleted account back
            user.deleted_at = None
            user.is_active = True
        if google_sub and user.google_sub and user.google_sub != google_sub:
            # the address now belongs to a different Google account
            raise HTTPException(status.HTTP_403_FORBIDDEN, "not_allowed")
        user.google_sub = user.google_sub or google_sub
        user.name = user.name or name
        user.avatar = avatar or user.avatar
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "not_allowed")
    await session.flush()
    return user


TELEGRAM_MAX_AGE = 86400  # Telegram signs the moment of the sign-in; a day-old signature is refused


def check_telegram(data: dict[str, str]) -> None:
    """Telegram signs the sign-in data with our bot's token; without the signature anyone could claim
    to be anyone. The token is only a key here — no request is ever made to Telegram with it."""
    if not settings.telegram_login_token:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "telegram_not_configured")
    given = data.get("hash", "")
    pairs = sorted(f"{k}={v}" for k, v in data.items() if k != "hash" and v not in (None, ""))
    secret = hashlib.sha256(settings.telegram_login_token.encode()).digest()
    expected = hmac.new(secret, "\n".join(pairs).encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, given):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_token")
    age = datetime.now(UTC).timestamp() - float(data.get("auth_date", 0))
    if age > TELEGRAM_MAX_AGE or age < -300:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "expired_token")


async def from_telegram(
    session: AsyncSession,
    *,
    telegram_id: int,
    name: str | None,
    username: str | None,
    avatar: str | None,
    lang: str,
) -> User:
    """The account behind a Telegram sign-in. There is no email in Telegram: the id is the key."""
    user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
    if user is None:
        user = User(
            telegram_id=telegram_id,
            telegram_username=username,
            name=name,
            avatar=avatar,
            lang=lang,
            role=UserRole.USER,
            is_active=True,
        )
        session.add(user)
    else:
        if user.deleted_at is not None:
            user.deleted_at = None
            user.is_active = True
        user.telegram_username = username or user.telegram_username
        user.name = user.name or name
        user.avatar = avatar or user.avatar
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "not_allowed")
    await session.flush()
    return user


async def delete_account(session: AsyncSession, user: User) -> None:
    """GDPR: the person's data goes, the row stays so the statistics do not break."""
    user.email = f"deleted-{user.id}@citobazar.invalid"
    user.name = None
    user.phone = None
    user.avatar = None
    user.google_sub = None
    user.telegram_id = None
    user.telegram_username = None
    user.is_active = False
    user.deleted_at = datetime.now(UTC)
    await session.commit()
