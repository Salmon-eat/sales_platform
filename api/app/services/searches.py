"""Saved searches and the letters they send.

A saved search is the search itself, kept exactly as it stood in the address bar, so the notice that
goes out is found by the same code that fills the page — not by a second, slightly different query
that would quietly drift apart from it.
"""

import logging
from datetime import UTC, datetime

from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import SavedSearch, Section, User
from app.models.saved_search import MAX_SEARCHES
from app.search.service import search_listings
from app.services import mail, telegram_send
from app.services.chat_notify import URL_PREFIX, _short

log = logging.getLogger("bazarcito.searches")

# how many new ads one letter mentions by name
IN_LETTER = 5
# never write about the same search more often than this
PER_RUN = 100

SUBJECT = {
    "es": "Novedades para tu búsqueda «{title}»",
    "en": "New ads for your search “{title}”",
    "uk": "Нове за вашим пошуком «{title}»",
    "ru": "Новое по вашему поиску «{title}»",
}
BODY = {
    "es": "Han aparecido {count} anuncios nuevos:\n\n{lines}\n\nVer todos: {url}",
    "en": "{count} new ads have appeared:\n\n{lines}\n\nSee them all: {url}",
    "uk": "Зʼявилося нових оголошень: {count}\n\n{lines}\n\nПодивитися всі: {url}",
    "ru": "Появилось новых объявлений: {count}\n\n{lines}\n\nПосмотреть все: {url}",
}


async def mine(session: AsyncSession, user: User) -> list[SavedSearch]:
    rows = await session.scalars(
        select(SavedSearch).where(SavedSearch.user_id == user.id).order_by(SavedSearch.created_at.desc())
    )
    return list(rows.all())


async def save(
    session: AsyncSession,
    redis: Redis,
    user: User,
    *,
    title: str,
    lang: str,
    section_key: str | None,
    category_slug: str | None,
    location_slug: str | None,
    params: dict[str, str],
) -> SavedSearch:
    count = (
        await session.scalar(
            select(func.count()).select_from(SavedSearch).where(SavedSearch.user_id == user.id)
        )
        or 0
    )
    if count >= MAX_SEARCHES:
        raise HTTPException(status.HTTP_409_CONFLICT, "too_many_searches")

    search = SavedSearch(
        user_id=user.id,
        title=title[:200],
        lang=lang,
        section_key=section_key,
        category_slug=category_slug,
        location_slug=location_slug,
        params=params,
    )
    # everything already on the site is "seen": the first letter is about what comes next
    found = await _matches(session, redis, search)
    search.last_seen_id = max((item.id for item in found), default=0)
    session.add(search)
    await session.commit()
    await session.refresh(search)
    return search


async def remove(session: AsyncSession, user: User, search_id: int) -> None:
    search = await session.scalar(
        select(SavedSearch).where(SavedSearch.id == search_id, SavedSearch.user_id == user.id)
    )
    if search is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found")
    await session.delete(search)
    await session.commit()


async def set_notify(session: AsyncSession, user: User, search_id: int, notify: bool) -> SavedSearch:
    search = await session.scalar(
        select(SavedSearch).where(SavedSearch.id == search_id, SavedSearch.user_id == user.id)
    )
    if search is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found")
    search.notify = notify
    await session.commit()
    await session.refresh(search)
    return search


async def _matches(session: AsyncSession, redis: Redis, search: SavedSearch):
    """The newest ads this search finds, through the very same code the page uses."""
    raw = {key: [value] for key, value in (search.params or {}).items() if value}
    raw.setdefault("sort", ["new"])
    try:
        found = await search_listings(
            session,
            redis,
            lang=search.lang,
            section_key=search.section_key,
            category_slug=search.category_slug,
            location_slug=search.location_slug,
            raw=raw,
            per_page=20,
        )
    except HTTPException:
        # the section or category was renamed away under it; the owner will see nothing new
        log.warning("saved search %s no longer resolves", search.id)
        return []
    return found.items


async def _url(session: AsyncSession, search: SavedSearch, site: str) -> str:
    """The address as the owner would see it: the section is stored by key, the page shows its slug
    in their language ("articulos" is the key, "rechi" is what a Ukrainian reader sees)."""
    code = search.lang if search.lang in URL_PREFIX else "es"
    section_slug = None
    if search.section_key:
        section = await session.scalar(select(Section).where(Section.key == search.section_key))
        section_slug = section.slug.get(code) if section else search.section_key
    parts = [p for p in (section_slug, search.category_slug, search.location_slug) if p]
    query = "&".join(f"{k}={v}" for k, v in (search.params or {}).items() if v)
    path = "/".join(parts)
    return f"{site}/{URL_PREFIX[code]}/{path}{'?' + query if query else ''}"


async def notify_new(session: AsyncSession, redis: Redis, site: str) -> int:
    """Worker job: one letter per search that has something new. Returns how many were sent."""
    searches = (
        await session.scalars(
            select(SavedSearch).where(SavedSearch.notify.is_(True)).order_by(SavedSearch.id).limit(PER_RUN)
        )
    ).all()

    sent = 0
    for search in searches:
        items = await _matches(session, redis, search)
        fresh = [item for item in items if item.id > search.last_seen_id]
        if not fresh:
            continue

        user = await session.get(User, search.user_id)
        highest = max(item.id for item in fresh)
        if user is None or not user.is_active:
            search.last_seen_id = highest
            continue

        lang = search.lang if search.lang in SUBJECT else "es"
        lines = "\n".join(f"· {_short(item.title, 80)}" for item in fresh[:IN_LETTER])
        subject = SUBJECT[lang].format(title=_short(search.title, 60))
        body = BODY[lang].format(
            count=len(fresh), lines=lines, url=await _url(session, search, site)
        )

        delivered = False
        if user.notify_telegram and user.telegram_id:
            delivered = await telegram_send.send(user.telegram_id, f"{subject}\n\n{body}")
        if not delivered and user.notify_email and user.email:
            delivered = await mail.send(user.email, subject, body)

        search.last_seen_id = highest
        search.last_notified_at = datetime.now(UTC)
        sent += 1 if delivered else 0

    await session.commit()
    return sent
