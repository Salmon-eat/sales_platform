"""Sync with the Telegram bot (admin spec §8).

The bot stays the way managers work in Telegram; the admin shows the same applications and conversations
and lets the team answer from the site. The bot always calls us (it opens no port and we never read its
updates): it pushes new rows and picks up replies and status changes from bot_outgoing.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Application, ApplicationMessage
from app.models.application import BotOutgoing
from app.schemas.application import normalize_phone
from app.schemas.bot_sync import BotApplicationIn, BotMessageIn, BotOutgoingItem, BotSyncIn, BotSyncOut

AUTHORS = {"client": "visitor", "manager": "staff", "note": "note"}
DELIVERY = {"pending": "pending", "delivered": "delivered", "failed": "failed"}
# a Telegram message older than this is history: it does not light up as unread
UNREAD_WINDOW = timedelta(hours=24)
OUTGOING_BATCH = 100


def site_status(bot_status: str) -> str:
    return {"new": "new", "done": "done"}.get(bot_status, "in_progress")


def bot_status(status: str) -> str:
    """What the bot will have after the site sets this status (the bot has no "rejected")."""
    return {"new": "new", "in_progress": "in_work", "done": "done", "rejected": "done"}[status]


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=UTC)


def _phone(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return normalize_phone(value)
    except ValueError:
        return value[:20]  # typed by hand in the bot: kept as written


async def sync_from_bot(session: AsyncSession, data: BotSyncIn) -> BotSyncOut:
    apps = {a.bot_app_id: a for a in await _by_bot_id(session, {x.id for x in data.applications})}
    for item in data.applications:
        apps[item.id] = _upsert(session, apps.get(item.id), item)
    await session.flush()

    if data.topics:
        client_ids = {int(k) for k in data.topics}
        rows = await session.scalars(
            select(Application).where(
                Application.source == "bot",
                Application.bot["client_id"].as_integer().in_(client_ids),
                Application.anonymized_at.is_(None),
            )
        )
        for a in rows:
            url = data.topics.get(str(a.bot.get("client_id")))
            if url and url.startswith("https://t.me/") and a.bot.get("topic_url") != url:
                a.bot = {**a.bot, "topic_url": url}

    stored = 0
    wanted = {m.app_id for m in data.messages if m.app_id} - set(apps)
    apps.update({a.bot_app_id: a for a in await _by_bot_id(session, wanted)})
    for message in data.messages:
        stored += await _store_message(session, apps, message)
    await session.commit()
    return BotSyncOut(applications=len(data.applications), messages=stored)


async def _by_bot_id(session: AsyncSession, ids: set[int]) -> list[Application]:
    if not ids:
        return []
    return list((await session.scalars(select(Application).where(Application.bot_app_id.in_(ids)))).all())


def _upsert(session: AsyncSession, a: Application | None, item: BotApplicationIn) -> Application:
    info = {
        "client_id": item.client_id,
        "title": item.title,
        "card": item.card,
        "username": item.username,
        "manager_name": item.manager_name,
        "status": item.status,
    }
    if a is None:
        a = Application(
            bot_app_id=item.id,
            name=item.name or "—",
            phone=_phone(item.phone),
            messenger="telegram",
            answers={},
            lang=item.lang[:2],
            source="bot",
            status=site_status(item.status),
            consent_at=_time(item.created_at),
            consent_version="telegram",
            bot=info,
            created_at=_time(item.created_at),
            updated_at=_time(item.updated_at),
            anonymized_at=None,  # read after the flush: set, so it is not reloaded (no lazy IO in async)
        )
        session.add(a)
        return a
    if a.anonymized_at is not None:  # erased here: only the statistics follow the bot
        a.bot = {**a.bot, "status": item.status, "title": item.title}
    else:
        a.name = item.name or a.name
        a.phone = _phone(item.phone) or a.phone
        a.bot = {**a.bot, **info}
    # "rejected" here is "done" in the bot: the bot's "done" must not undo it
    if bot_status(a.status) != item.status:
        a.status = site_status(item.status)
    a.updated_at = max(a.updated_at, _time(item.updated_at))
    return a


async def _store_message(session: AsyncSession, apps: dict[int, Application], m: BotMessageIn) -> int:
    delivery = DELIVERY.get(m.delivery)
    if m.site_message_id:  # our own reply, now sent (or refused) by the bot
        own = await session.get(ApplicationMessage, m.site_message_id)
        if own is not None and own.bot_message_id is None:
            own.bot_message_id = m.id
            own.delivery = delivery
        return 0
    if await session.scalar(select(ApplicationMessage.id).where(ApplicationMessage.bot_message_id == m.id)):
        return 0  # sent again after a lost response
    a = apps.get(m.app_id) if m.app_id else None
    if a is None or a.anonymized_at is not None:
        return 0
    created = _time(m.created_at)
    author = AUTHORS[m.direction]
    fresh = datetime.now(UTC) - created < UNREAD_WINDOW
    session.add(
        ApplicationMessage(
            application_id=a.id,
            author=author,
            author_name=m.sender_name if author != "visitor" else None,
            text=m.text or "",
            content_type=m.content_type[:20],
            bot_message_id=m.id,
            delivery=delivery if author == "staff" else None,
            read_at=None if author == "visitor" and fresh else created,
            created_at=created,
        )
    )
    # in SQL: the row may have been flushed meanwhile, and reading it back here would be lazy IO
    a.updated_at = func.greatest(Application.updated_at, created)
    return 1


def queue_reply(session: AsyncSession, a: Application, message_id: int) -> None:
    session.add(BotOutgoing(application_id=a.id, kind="message", message_id=message_id))


def queue_status(session: AsyncSession, a: Application) -> None:
    session.add(BotOutgoing(application_id=a.id, kind="status", status=a.status))


async def outgoing(session: AsyncSession, after: int) -> list[BotOutgoingItem]:
    rows = await session.execute(
        select(BotOutgoing, Application.bot_app_id, ApplicationMessage)
        .join(Application, Application.id == BotOutgoing.application_id)
        .outerjoin(ApplicationMessage, ApplicationMessage.id == BotOutgoing.message_id)
        .where(BotOutgoing.id > after)
        .order_by(BotOutgoing.id)
        .limit(OUTGOING_BATCH)
    )
    return [
        BotOutgoingItem(
            id=row.id,
            kind=row.kind,
            app_id=bot_app_id,
            message_id=message.id if message else None,
            text=message.text if message else None,
            sender_name=message.author_name if message else None,
            status=row.status,
        )
        for row, bot_app_id, message in rows
    ]
