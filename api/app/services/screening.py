"""The automatic look at an ad before a person sees it.

Nothing here rejects an ad on its own, except a plain repeat of one the same person already posted.
Everything else is a note for the moderator: "there is a phone number in the text", "this word is
usually a scam". The moderator decides; the machine only says where to look first.
"""

import re
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Listing, ListingTranslation

DUPLICATE_WINDOW = timedelta(days=30)

# a phone number written in any of the usual ways, an email, a link, a messenger handle
PHONE = re.compile(r"(?:\+?\d[\s().-]?){9,}")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]{2,}")
LINK = re.compile(r"(?:https?://|www\.)\S+|\b[\w-]+\.(?:com|es|net|org|ru|ua|info|biz)\b", re.I)
HANDLE = re.compile(r"(?:^|\s)@[A-Za-z][\w]{4,}")

# words that, in a classified ad, almost always mean a scam or something we may not publish.
# Four languages, lowercase, matched as whole words.
STOP_WORDS: dict[str, tuple[str, ...]] = {
    "papers": (
        "поддельные", "підроблені", "fake documents", "documentos falsos", "falsificad",
        "липовые", "липові", "купить права", "купити права", "carnet sin examen",
    ),
    "drugs": ("кокаин", "кокаїн", "марихуан", "cocaina", "cocaína", "marihuana", "hachís", "mdma"),
    "weapons": ("оружие", "зброя", "pistola", "munición", "глушитель"),
    "adult": ("эскорт", "ескорт", "escort", "intim", "интим", "інтим"),
    "money": (
        "быстрый заработок", "швидкий заробіток", "dinero rápido", "easy money",
        "предоплат", "передоплат", "western union", "вложите", "вкладіть",
    ),
}

FLAG_LABELS = {
    "contact_in_text": "a phone, email or link inside the text",
    "link_in_title": "a link in the title",
}


PUNCTUATION = re.compile(r"[^\w\s]+", re.UNICODE)


def _words(text: str) -> str:
    """Lowercase, punctuation out: "Купить-права!" and "купить права" must look the same."""
    return f" {PUNCTUATION.sub(' ', text.lower())} "


def check_text(title: str, description: str) -> list[str]:
    """Flags for one ad's text, in the order a moderator would want to see them."""
    flags: list[str] = []
    body = f"{title}\n{description}"
    if PHONE.search(body) or EMAIL.search(body) or LINK.search(body) or HANDLE.search(body):
        # contacts belong in the contact fields, where the site can protect them from harvesters
        flags.append("contact_in_text")
    if LINK.search(title):
        flags.append("link_in_title")
    haystack = _words(body)
    for group, words in STOP_WORDS.items():
        # stems on purpose ("предоплат" catches both "предоплата" and "предоплату")
        if any(word in haystack for word in words):
            flags.append(f"stop_word:{group}")
    return flags


async def is_duplicate(
    session: AsyncSession, owner_id: int, title: str, category_id: int, listing_id: int | None
) -> bool:
    """The same person posting the same title in the same category again within a month."""
    query = (
        select(func.count())
        .select_from(Listing)
        .join(ListingTranslation, ListingTranslation.listing_id == Listing.id)
        .where(
            Listing.owner_id == owner_id,
            Listing.category_id == category_id,
            Listing.status.in_(("pending", "active", "paused")),
            Listing.created_at > datetime.now(UTC) - DUPLICATE_WINDOW,
            func.lower(func.trim(ListingTranslation.title)) == title.strip().lower(),
        )
    )
    if listing_id is not None:
        query = query.where(Listing.id != listing_id)
    return bool(await session.scalar(query))
