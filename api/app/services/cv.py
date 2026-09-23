"""The candidate's CV attached to an application (optional).

The file comes after the application, with a one-time key the application answer gave (valid one hour),
so a failed upload never loses the application. Only PDF, Word and images, up to 5 MB, recognised by
their content, not by the name. Only staff download it, always as a download (never opened inline).
"""

import re
import secrets
import unicodedata

from fastapi import HTTPException, status
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ApplicationFile

MAX_BYTES = 5 * 1024 * 1024
TOKEN_TTL = 3600

# content signature -> (type, extension); DOCX is a ZIP, old DOC an OLE file
SIGNATURES: tuple[tuple[bytes, str, str], ...] = (
    (b"%PDF-", "application/pdf", "pdf"),
    (b"PK\x03\x04", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx"),
    (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", "application/msword", "doc"),
    (b"\xff\xd8\xff", "image/jpeg", "jpg"),
    (b"\x89PNG\r\n\x1a\n", "image/png", "png"),
)


async def new_token(redis: Redis, application_id: int) -> str | None:
    token = secrets.token_urlsafe(24)
    try:
        await redis.set(f"cv:{token}", application_id, ex=TOKEN_TTL)
    except RedisError:
        return None  # no CV this time; the application itself is saved
    return token


async def token_application(redis: Redis, token: str) -> int:
    try:
        value = await redis.get(f"cv:{token}")
    except RedisError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "try again later") from exc
    if not value:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "upload link expired")
    return int(value)


async def drop_token(redis: Redis, token: str) -> None:
    """After a successful upload; a rejected file (wrong type) can be replaced with another try."""
    try:
        await redis.delete(f"cv:{token}")
    except RedisError:
        pass


def detect(data: bytes) -> tuple[str, str]:
    for magic, content_type, ext in SIGNATURES:
        if data.startswith(magic):
            if ext == "docx" and b"word/" not in data[:4096] and b"[Content_Types].xml" not in data[:4096]:
                break  # some other ZIP
            return content_type, ext
    raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "unsupported_file")


def safe_name(raw: str | None, ext: str) -> str:
    """A name safe for a download header: letters, digits, spaces, dots and dashes; our extension."""
    name = unicodedata.normalize("NFC", raw or "").rsplit(".", 1)[0]
    name = re.sub(r"[^\w\s.-]", "", name, flags=re.UNICODE).strip(" .-")[:80] or "cv"
    return f"{name}.{ext}"


async def save(
    session: AsyncSession, application_id: int, data: bytes, filename: str | None
) -> ApplicationFile:
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "empty_file")
    if len(data) > MAX_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "file_too_large")
    content_type, ext = detect(data)
    # one CV per application: a second upload replaces the first
    await session.execute(delete(ApplicationFile).where(ApplicationFile.application_id == application_id))
    row = ApplicationFile(
        application_id=application_id,
        filename=safe_name(filename, ext),
        content_type=content_type,
        size=len(data),
        data=data,
    )
    session.add(row)
    await session.commit()
    return row
