"""Conversations between a buyer and a seller about one ad.

Rules that matter:
  - one conversation per (ad, buyer); the seller never starts one, they answer;
  - only the two sides can read it, and a stranger's id leads to "not found", not "forbidden";
  - unread counters live on the conversation, so the header badge is one cheap query;
  - a message is emailed to the other side only if it stays unread for a few minutes (app.worker).
"""

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Conversation, ConversationMessage, Listing, Section, User
from app.schemas.chat import ChatItem, ChatOut, MessageOut
from app.seo.paths import listing_path
from app.services import photos as photo_files

# a conversation can only be about an ad that someone still stands behind
OPEN_STATUSES = ("active", "paused", "expired", "closed")


def _not_found() -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, "not_found")


async def get_own(session: AsyncSession, user: User, chat_id: int) -> Conversation:
    chat = await session.scalar(select(Conversation).where(Conversation.id == chat_id))
    if chat is None or user.id not in (chat.buyer_id, chat.seller_id):
        raise _not_found()
    return chat


async def start(session: AsyncSession, user: User, listing_id: int, text: str) -> Conversation:
    """The buyer writes first; the same buyer writing again lands in the same conversation."""
    listing = await session.get(Listing, listing_id)
    if listing is None or listing.status not in OPEN_STATUSES:
        raise _not_found()
    if listing.owner_id is None:
        # an agency listing: the application form is the way to answer it, not a private chat
        raise HTTPException(status.HTTP_409_CONFLICT, "no_chat_for_this_ad")
    if listing.owner_id == user.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "own_listing")

    chat = await session.scalar(
        select(Conversation).where(
            Conversation.listing_id == listing_id, Conversation.buyer_id == user.id
        )
    )
    if chat is None:
        chat = Conversation(listing_id=listing_id, buyer_id=user.id, seller_id=listing.owner_id)
        session.add(chat)
        await session.flush()
    await add_message(session, chat, user, text)
    return chat


async def add_message(
    session: AsyncSession, chat: Conversation, user: User, text: str
) -> ConversationMessage:
    if user.id not in (chat.buyer_id, chat.seller_id):
        raise _not_found()
    message = ConversationMessage(conversation_id=chat.id, sender_id=user.id, text=text)
    session.add(message)
    chat.last_message_at = datetime.now(UTC)
    if chat.is_seller(user.id):
        chat.buyer_unread += 1
        chat.buyer_hidden = False
    else:
        chat.seller_unread += 1
        chat.seller_hidden = False
    await session.commit()
    # a commit expires both rows; reading them again must happen through an await, not by accident
    await session.refresh(message)
    await session.refresh(chat)
    return message


async def mark_read(session: AsyncSession, chat: Conversation, user: User) -> None:
    """Opening a conversation means everything the other side wrote has been seen."""
    await session.execute(
        update(ConversationMessage)
        .where(
            ConversationMessage.conversation_id == chat.id,
            ConversationMessage.sender_id != user.id,
            ConversationMessage.read_at.is_(None),
        )
        .values(read_at=datetime.now(UTC))
    )
    if chat.is_seller(user.id):
        chat.seller_unread = 0
    else:
        chat.buyer_unread = 0
    await session.commit()
    await session.refresh(chat)


async def hide(session: AsyncSession, chat: Conversation, user: User) -> None:
    if chat.is_seller(user.id):
        chat.seller_hidden = True
    else:
        chat.buyer_hidden = True
    await session.commit()


async def unread_total(session: AsyncSession, user: User) -> int:
    buyer = await session.scalar(
        select(func.coalesce(func.sum(Conversation.buyer_unread), 0)).where(
            Conversation.buyer_id == user.id
        )
    )
    seller = await session.scalar(
        select(func.coalesce(func.sum(Conversation.seller_unread), 0)).where(
            Conversation.seller_id == user.id
        )
    )
    return int(buyer or 0) + int(seller or 0)


# ---------------------------------------------------------------------------- output


async def _listing_brief(
    session: AsyncSession, listing_id: int, lang: str
) -> tuple[str, str | None, str | None]:
    listing = await session.scalar(
        select(Listing)
        .where(Listing.id == listing_id)
        .options(selectinload(Listing.translations), selectinload(Listing.photos))
    )
    if listing is None:
        return "—", None, None
    by_lang = {t.lang: t for t in listing.translations}
    text = by_lang.get(lang) or by_lang.get(listing.original_lang) or next(iter(by_lang.values()), None)
    section = await session.get(Section, listing.section_id)
    path = None
    if listing.status == "active" and text and section:
        path = listing_path(section.slug[text.lang], text.lang, text.slug, listing.id, section.key)
    photo = photo_files.thumb_path(listing.photos[0].path) if listing.photos else None
    return (text.title if text else "—"), path, photo


async def _name_of(session: AsyncSession, user_id: int) -> str:
    """A deleted account keeps a placeholder address; never show it to the other side."""
    other = await session.get(User, user_id)
    if other is None or other.deleted_at is not None:
        return "—"
    return other.name or (other.email.split("@")[0] if other.email else "—")


async def item_out(session: AsyncSession, chat: Conversation, user: User, lang: str) -> ChatItem:
    title, path, photo = await _listing_brief(session, chat.listing_id, lang)
    last = await session.scalar(
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == chat.id)
        .order_by(ConversationMessage.id.desc())
        .limit(1)
    )
    return ChatItem(
        id=chat.id,
        listing_id=chat.listing_id,
        listing_title=title,
        listing_path=path,
        listing_photo=photo,
        other_name=await _name_of(session, chat.other_side(user.id)),
        selling=chat.is_seller(user.id),
        last_text=(last.text if last else ""),
        last_at=chat.last_message_at,
        unread=chat.unread_for(user.id),
    )


async def detail_out(session: AsyncSession, chat: Conversation, user: User, lang: str) -> ChatOut:
    base = await item_out(session, chat, user, lang)
    rows = (
        await session.scalars(
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == chat.id)
            .order_by(ConversationMessage.id)
        )
    ).all()
    return ChatOut(
        **base.model_dump(),
        messages=[
            MessageOut(
                id=row.id,
                mine=row.sender_id == user.id,
                text=row.text,
                created_at=row.created_at,
                read_at=row.read_at,
            )
            for row in rows
        ],
    )


async def mine(session: AsyncSession, user: User, lang: str) -> list[ChatItem]:
    rows = (
        await session.scalars(
            select(Conversation)
            .where(
                ((Conversation.buyer_id == user.id) & Conversation.buyer_hidden.is_(False))
                | ((Conversation.seller_id == user.id) & Conversation.seller_hidden.is_(False))
            )
            .order_by(Conversation.last_message_at.desc())
        )
    ).all()
    return [await item_out(session, row, user, lang) for row in rows]
