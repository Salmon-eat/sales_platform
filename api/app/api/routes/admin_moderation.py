"""The moderation queue: every ad a visitor sends in waits here until a person looks at it.

Pre-moderation, on purpose: nothing a stranger writes appears on the site before one of the team has
read it. The list is ordered oldest first, so nobody waits longer than they have to.
"""

from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import AdminLang, RedisDep, SessionDep, require_staff
from app.core.config import settings
from app.models import Category, Listing, Location, Section, User
from app.models.i18n import tr
from app.schemas.common import Page
from app.services import photos as photo_files
from app.services.cache import bump_cache_version

router = APIRouter(prefix="/admin/moderation", tags=["admin: moderation"])

Staff = Annotated[User, Depends(require_staff)]

# why an ad can be refused; the admin shows these as buttons, the person gets the text in their language
REJECT_REASONS = (
    "wrong_category",
    "contacts_in_text",
    "bad_photos",
    "duplicate",
    "prohibited",
    "spam",
    "unclear",
    "other",
)
RejectReason = Literal[REJECT_REASONS]  # type: ignore[valid-type]


class QueueItem(BaseModel):
    id: int
    title: str
    description: str
    lang: str
    section_name: str
    category_name: str
    location_name: str | None
    price: int | None
    price_period: str | None
    price_kind: str
    attributes: dict
    contact: dict
    photos: list[str]
    flags: list[str]
    author_name: str | None
    author_email: str | None
    author_ads: int = Field(description="how many ads this person already has on the site")
    created_at: datetime
    updated_at: datetime


class RejectIn(BaseModel):
    reason: RejectReason
    note: str | None = Field(None, max_length=500, description="a line the author will read")


async def _queue_item(session: SessionDep, listing: Listing, lang: str) -> QueueItem:
    text = listing.translations[0] if listing.translations else None
    category = await session.get(Category, listing.category_id)
    section = await session.get(Section, listing.section_id)
    town = await session.get(Location, listing.location_id) if listing.location_id else None
    author = await session.get(User, listing.owner_id) if listing.owner_id else None
    published = (
        await session.scalar(
            select(func.count())
            .select_from(Listing)
            .where(Listing.owner_id == listing.owner_id, Listing.status == "active")
        )
        or 0
        if listing.owner_id
        else 0
    )
    return QueueItem(
        id=listing.id,
        title=text.title if text else "",
        description=text.description if text else "",
        lang=text.lang if text else listing.original_lang,
        section_name=tr(section.name, lang) if section else "",
        category_name=tr(category.name, lang) if category else "",
        location_name=tr(town.names, lang) if town else None,
        price=listing.price,
        price_period=listing.price_period,
        price_kind=listing.price_kind,
        attributes=listing.attributes or {},
        contact=listing.contact or {},
        photos=[photo_files.thumb_path(photo.path) for photo in listing.photos],
        flags=listing.flags or [],
        author_name=author.name if author else None,
        author_email=author.email if author else None,
        author_ads=published,
        created_at=listing.created_at,
        updated_at=listing.updated_at,
    )


@router.get("/queue", response_model=Page[QueueItem])
async def queue(
    session: SessionDep,
    user: Staff,
    lang: AdminLang,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=50)] = 20,
) -> Page[QueueItem]:
    conds = [Listing.status == "pending"]
    total = await session.scalar(select(func.count()).select_from(Listing).where(*conds)) or 0
    rows = (
        await session.scalars(
            select(Listing)
            .where(*conds)
            .options(selectinload(Listing.translations), selectinload(Listing.photos))
            .order_by(Listing.updated_at)  # oldest first: nobody is left waiting
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
    ).all()
    return Page(
        items=[await _queue_item(session, row, lang) for row in rows],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/count")
async def pending_count(session: SessionDep, user: Staff) -> dict[str, int]:
    """For the badge on the admin menu."""
    return {
        "pending": await session.scalar(
            select(func.count()).select_from(Listing).where(Listing.status == "pending")
        )
        or 0
    }


async def _load(session: SessionDep, listing_id: int) -> Listing:
    """With its text and photos: after a commit the row is expired and lazy loading would break async."""
    listing = await session.scalar(
        select(Listing)
        .where(Listing.id == listing_id)
        .options(selectinload(Listing.translations), selectinload(Listing.photos))
    )
    if listing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found")
    return listing


async def _pending(session: SessionDep, listing_id: int) -> Listing:
    listing = await _load(session, listing_id)
    if listing.status != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, "already_checked")
    return listing


@router.post("/{listing_id}/approve", response_model=QueueItem)
async def approve(
    listing_id: int, session: SessionDep, redis: RedisDep, user: Staff, lang: AdminLang
) -> QueueItem:
    listing = await _pending(session, listing_id)
    now = datetime.now(UTC)
    listing.status = "active"
    listing.published_at = listing.published_at or now
    listing.expires_at = now + timedelta(days=settings.listing_days)
    listing.moderated_by, listing.moderated_at = user.id, now
    listing.reject_reason, listing.reject_note = None, None
    await session.commit()
    await bump_cache_version(redis)
    return await _queue_item(session, await _load(session, listing_id), lang)


@router.post("/{listing_id}/reject", response_model=QueueItem)
async def reject(
    listing_id: int, body: RejectIn, session: SessionDep, user: Staff, lang: AdminLang
) -> QueueItem:
    """The author sees the reason in their own area and can fix the ad and send it again."""
    listing = await _pending(session, listing_id)
    listing.status = "rejected"
    listing.reject_reason, listing.reject_note = body.reason, body.note
    listing.moderated_by, listing.moderated_at = user.id, datetime.now(UTC)
    await session.commit()
    return await _queue_item(session, await _load(session, listing_id), lang)
