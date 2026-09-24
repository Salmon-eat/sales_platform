"""Telling someone by email that a message is waiting for them.

Not one letter per message: a person typing three lines in a row would send three letters. The worker
waits a few minutes, then sends one letter per recipient, however many conversations it covers, and
only about messages that are still unread.
"""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Conversation, ConversationMessage, User
from app.services import mail

log = logging.getLogger("bazarcito.chat_notify")

# how long a message may sit unread before its owner is told
QUIET_MINUTES = 5
# never write to the same person more often than this
BATCH_LIMIT = 200

URL_PREFIX = {"es": "es", "en": "en", "uk": "ua", "ru": "ru"}
ACCOUNT_SLUG = {"es": "cuenta", "en": "account", "uk": "kabinet", "ru": "kabinet"}

SUBJECT = {
    "es": "Tienes {count} mensaje(s) nuevo(s) en Citobazar",
    "en": "You have {count} new message(s) on Citobazar",
    "uk": "У вас {count} нових повідомлень на Citobazar",
    "ru": "У вас {count} новых сообщений на Citobazar",
}
BODY = {
    "es": (
        "Alguien te ha escrito sobre tus anuncios.\n\n{lines}\n\n"
        "Responde desde tu cuenta: {url}\n\n"
        "Si no quieres estos avisos, escríbenos desde la página de contacto."
    ),
    "en": (
        "Somebody wrote to you about your ads.\n\n{lines}\n\n"
        "Answer from your account: {url}\n\n"
        "If you would rather not get these, tell us from the contact page."
    ),
    "uk": (
        "Вам написали щодо ваших оголошень.\n\n{lines}\n\n"
        "Відповісти можна в кабінеті: {url}\n\n"
        "Якщо такі листи не потрібні — напишіть нам зі сторінки контактів."
    ),
    "ru": (
        "Вам написали по вашим объявлениям.\n\n{lines}\n\n"
        "Ответить можно в кабинете: {url}\n\n"
        "Если такие письма не нужны — напишите нам со страницы контактов."
    ),
}
LINE = {
    "es": "· {name}: {text}",
    "en": "· {name}: {text}",
    "uk": "· {name}: {text}",
    "ru": "· {name}: {text}",
}


def _account_url(lang: str) -> str:
    site = settings.public_site_url.rstrip("/")
    code = lang if lang in URL_PREFIX else "es"
    return f"{site}/{URL_PREFIX[code]}/{ACCOUNT_SLUG[code]}?tab=chats"


def _short(text: str, limit: int = 120) -> str:
    one_line = " ".join(text.split())
    return one_line if len(one_line) <= limit else f"{one_line[: limit - 1]}…"


async def pending_messages(session: AsyncSession) -> list[tuple[ConversationMessage, Conversation]]:
    """Unread, not yet announced, and old enough that the writer has stopped typing."""
    cutoff = datetime.now(UTC) - timedelta(minutes=QUIET_MINUTES)
    rows = await session.execute(
        select(ConversationMessage, Conversation)
        .join(Conversation, Conversation.id == ConversationMessage.conversation_id)
        .where(
            ConversationMessage.read_at.is_(None),
            ConversationMessage.notified_at.is_(None),
            ConversationMessage.created_at < cutoff,
        )
        .order_by(ConversationMessage.id)
        .limit(BATCH_LIMIT)
    )
    return list(rows.all())


async def notify_unread(session: AsyncSession) -> int:
    """One letter per person. Returns how many people were written to."""
    pending = await pending_messages(session)
    if not pending:
        return 0

    # recipient -> the messages waiting for them
    for_person: dict[int, list[tuple[ConversationMessage, Conversation]]] = {}
    for message, chat in pending:
        if message.sender_id is None:
            continue
        recipient = chat.other_side(message.sender_id)
        for_person.setdefault(recipient, []).append((message, chat))

    written = 0
    for user_id, items in for_person.items():
        user = await session.get(User, user_id)
        ids = [message.id for message, _ in items]
        if user is None or not user.email or not user.is_active:
            # nobody to write to; the messages are still marked so we do not look at them again
            await _mark(session, ids)
            continue

        lang = user.lang if user.lang in SUBJECT else "es"
        lines = []
        for message, _chat in items:
            sender = await session.get(User, message.sender_id) if message.sender_id else None
            name = (sender.name if sender else None) or "—"
            lines.append(LINE[lang].format(name=name, text=_short(message.text)))

        sent = await mail.send(
            user.email,
            SUBJECT[lang].format(count=len(items)),
            BODY[lang].format(lines="\n".join(lines), url=_account_url(lang)),
        )
        # marked either way: a letter that cannot be sent must not be retried forever
        await _mark(session, ids)
        written += 1 if sent else 0

    await session.commit()
    return written


async def _mark(session: AsyncSession, ids: list[int]) -> None:
    if ids:
        await session.execute(
            update(ConversationMessage)
            .where(ConversationMessage.id.in_(ids))
            .values(notified_at=datetime.now(UTC))
        )
