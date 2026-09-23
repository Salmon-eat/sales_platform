"""Ads people post about themselves: write, send for checking, close, extend.

The rules in one place:
  draft      - being written, only the author sees it
  pending    - sent in, waiting for a moderator
  active     - published, for `listing_days` days
  rejected   - refused with a reason; the author may fix it and send it again
  paused / closed / expired - taken down, by the author or by time

Editing a published ad sends it back for checking: otherwise a clean ad could be replaced with anything
the moment it was approved.
"""

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from geoalchemy2 import WKTElement
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models import Category, Listing, ListingPhoto, ListingTranslation, Location, Section, User
from app.models.i18n import tr
from app.models.listing import MAX_PHOTOS
from app.schemas.my import MyListingIn, MyListingItem, MyListingOut, PhotoOut
from app.seo.paths import listing_path
from app.services import photos as photo_files
from app.services import screening
from app.services.attributes import attribute_definitions
from app.services.listing_rules import AttributeSpec, listing_slug, validate_attributes
from app.services.listings import point_of, unprocessable

# statuses the author may still change the text of; a published ad goes back for checking after an edit
EDITABLE = ("draft", "pending", "rejected", "active", "paused", "expired")
OPEN = ("draft", "pending", "active", "paused")


def _forbidden() -> HTTPException:
    # the same answer for "not yours" and "does not exist": nobody can probe for other people's ads
    return HTTPException(status.HTTP_404_NOT_FOUND, "not_found")


async def get_own(session: AsyncSession, user: User, listing_id: int) -> Listing:
    listing = await session.scalar(
        select(Listing)
        .where(Listing.id == listing_id, Listing.owner_id == user.id)
        .options(selectinload(Listing.translations), selectinload(Listing.photos))
    )
    if listing is None:
        raise _forbidden()
    return listing


async def _category(session: AsyncSession, category_id: int) -> tuple[Category, Section]:
    category = await session.get(Category, category_id)
    if category is None or not category.is_enabled:
        raise unprocessable("category_id", "category_not_found")
    section = await session.get(Section, category.section_id)
    if section is None or not section.is_enabled or section.kind != "listings":
        raise unprocessable("category_id", "category_not_found")
    # a category with children is a heading: the ad goes into one of them
    has_children = await session.scalar(
        select(func.count()).select_from(Category).where(Category.parent_id == category.id)
    )
    if has_children:
        raise unprocessable("category_id", "category_not_final")
    return category, section


async def _specs(session: AsyncSession, category: Category) -> list[AttributeSpec]:
    rows = await attribute_definitions(session, section_id=category.section_id, category=category)
    return [AttributeSpec(a.key, a.type, tuple(o["value"] for o in a.options), a.required) for a in rows]


async def count_open(session: AsyncSession, user: User) -> int:
    return (
        await session.scalar(
            select(func.count())
            .select_from(Listing)
            .where(Listing.owner_id == user.id, Listing.status.in_(OPEN))
        )
        or 0
    )


async def save(
    session: AsyncSession, user: User, data: MyListingIn, listing: Listing | None = None
) -> Listing:
    if listing is None and await count_open(session, user) >= settings.listings_per_user:
        raise HTTPException(status.HTTP_409_CONFLICT, "too_many_listings")
    if listing is not None and listing.status not in EDITABLE:
        raise HTTPException(status.HTTP_409_CONFLICT, "not_editable")

    category, _ = await _category(session, data.category_id)
    town = await session.get(Location, data.location_id)
    if town is None or town.level not in ("municipio", "localidad"):
        raise unprocessable("location_id", "location_required")
    municipality = town if town.level == "municipio" else await session.get(Location, town.parent_id)

    attributes, errors = validate_attributes(await _specs(session, category), data.attributes)
    if errors:
        raise unprocessable("attributes", *errors)

    if await screening.is_duplicate(
        session, user.id, data.title, category.id, listing.id if listing else None
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, "duplicate_listing")

    # every query has to happen before the row exists: an unfinished row would be flushed into it
    point = await _point(session, town)

    if listing is None:
        listing = Listing(owner_id=user.id, created_by=user.id, status="draft", translations=[])
        session.add(listing)

    listing.section_id = category.section_id
    listing.category_id = category.id
    listing.location_scope = "local"
    listing.location_id = municipality.id if municipality else None
    listing.geog = point
    listing.original_lang = data.lang
    listing.price, listing.price_period, listing.price_kind = data.price, data.price_period, data.price_kind
    listing.attributes = attributes
    listing.contact = _contact(user, data)
    listing.source = "private"
    listing.employer_name = user.name or None

    text = listing.translations[0] if listing.translations else None
    if text is None:
        text = ListingTranslation(lang=data.lang)
        listing.translations.append(text)
    text.lang, text.title, text.description = data.lang, data.title, data.description
    text.slug = listing_slug(data.title, data.lang, municipality.slug if municipality else None)
    text.is_machine = False

    listing.flags = screening.check_text(data.title, data.description)
    await session.commit()
    return await get_own(session, user, listing.id)


async def _point(session: AsyncSession, town: Location):
    point = await point_of(session, Location.geog, Location.id == town.id)
    return WKTElement(f"POINT({point.lon} {point.lat})", srid=4326) if point else None


def _contact(user: User, data: MyListingIn) -> dict[str, str]:
    """What the buyer sees. Empty fields fall back to the account, so nobody has to retype their phone."""
    given = data.contact.model_dump(exclude_none=True)
    given.setdefault("name", user.name or "")
    if user.phone:
        given.setdefault("phone", user.phone)
    return {key: value for key, value in given.items() if value}


# ---------------------------------------------------------------------------- photos


async def add_photo(session: AsyncSession, user: User, listing: Listing, data: bytes) -> ListingPhoto:
    if len(listing.photos) >= MAX_PHOTOS:
        raise HTTPException(status.HTTP_409_CONFLICT, "too_many_photos")
    if listing.status not in EDITABLE:
        raise HTTPException(status.HTTP_409_CONFLICT, "not_editable")
    path, width, height, size = photo_files.save(data)
    row = ListingPhoto(
        listing_id=listing.id,
        path=path,
        width=width,
        height=height,
        size=size,
        sort=len(listing.photos),
    )
    session.add(row)
    await session.commit()
    return row


async def drop_photo(session: AsyncSession, listing: Listing, photo_id: int) -> None:
    photo = next((p for p in listing.photos if p.id == photo_id), None)
    if photo is None:
        raise _forbidden()
    path = photo.path
    await session.delete(photo)
    await session.commit()
    photo_files.delete(path)


# ---------------------------------------------------------------------------- what the author can do


async def submit(session: AsyncSession, user: User, listing: Listing) -> Listing:
    """Send the ad to the moderators. Pre-moderation: nothing appears on the site before a check."""
    if listing.status not in ("draft", "rejected", "expired", "paused"):
        raise HTTPException(status.HTTP_409_CONFLICT, "not_submittable")
    if not listing.translations or not listing.translations[0].title:
        raise HTTPException(status.HTTP_409_CONFLICT, "empty_listing")
    listing.status = "pending"
    listing.reject_reason, listing.reject_note = None, None
    listing.moderated_by, listing.moderated_at = None, None
    await session.commit()
    return await get_own(session, user, listing.id)


async def act(session: AsyncSession, user: User, listing: Listing, action: str) -> Listing:
    now = datetime.now(UTC)
    if action == "submit":
        return await submit(session, user, listing)
    if action == "close":
        if listing.status not in OPEN + ("expired",):
            raise HTTPException(status.HTTP_409_CONFLICT, "not_open")
        listing.status, listing.closed_at = "closed", now
    elif action == "reopen":
        # a closed or expired ad goes through the check again, like a new one
        if listing.status not in ("closed", "expired", "paused"):
            raise HTTPException(status.HTTP_409_CONFLICT, "not_closed")
        if await count_open(session, user) >= settings.listings_per_user:
            raise HTTPException(status.HTTP_409_CONFLICT, "too_many_listings")
        listing.status, listing.closed_at = "pending", None
    elif action == "extend":
        if listing.status != "active":
            raise HTTPException(status.HTTP_409_CONFLICT, "not_active")
        base = max(listing.expires_at or now, now)
        listing.expires_at = base + timedelta(days=settings.listing_days)
        listing.bumped_at = now
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "unknown_action")
    await session.commit()
    return await get_own(session, user, listing.id)


async def remove(session: AsyncSession, listing: Listing) -> None:
    """The author deletes their ad for good, with its photos."""
    paths = [photo.path for photo in listing.photos]
    await session.delete(listing)
    await session.commit()
    for path in paths:
        photo_files.delete(path)


# ---------------------------------------------------------------------------- output


def _photo_out(photo: ListingPhoto) -> PhotoOut:
    return PhotoOut(
        id=photo.id,
        path=photo.path,
        thumb=photo_files.thumb_path(photo.path),
        width=photo.width,
        height=photo.height,
    )


async def _names(session: AsyncSession, listing: Listing, lang: str) -> tuple[str, str | None]:
    category = await session.get(Category, listing.category_id)
    town = await session.get(Location, listing.location_id) if listing.location_id else None
    return (
        tr(category.name, lang) if category else "",
        tr(town.names, lang) if town else None,
    )


async def item_out(session: AsyncSession, listing: Listing, lang: str) -> MyListingItem:
    text = listing.translations[0] if listing.translations else None
    category_name, town_name = await _names(session, listing, lang)
    section = await session.get(Section, listing.section_id)
    path = None
    if listing.status == "active" and text and section:
        path = listing_path(section.slug[text.lang], text.lang, text.slug, listing.id, section.key)
    return MyListingItem(
        id=listing.id,
        status=listing.status,
        title=text.title if text else "",
        lang=text.lang if text else listing.original_lang,
        path=path,
        photo=photo_files.thumb_path(listing.photos[0].path) if listing.photos else None,
        price=listing.price,
        price_period=listing.price_period,
        price_kind=listing.price_kind,
        category_name=category_name,
        location_name=town_name,
        published_at=listing.published_at,
        expires_at=listing.expires_at,
        reject_reason=listing.reject_reason,
        reject_note=listing.reject_note,
        photos_count=len(listing.photos),
        updated_at=listing.updated_at,
    )


async def detail_out(session: AsyncSession, listing: Listing, lang: str) -> MyListingOut:
    base = await item_out(session, listing, lang)
    text = listing.translations[0] if listing.translations else None
    return MyListingOut(
        **base.model_dump(),
        category_id=listing.category_id,
        location_id=listing.location_id,
        description=text.description if text else "",
        attributes=listing.attributes or {},
        contact=listing.contact or {},
        photos=[_photo_out(photo) for photo in listing.photos],
    )


async def mine(session: AsyncSession, user: User, lang: str) -> list[MyListingItem]:
    rows = (
        await session.scalars(
            select(Listing)
            .where(Listing.owner_id == user.id)
            .options(selectinload(Listing.translations), selectinload(Listing.photos))
            .order_by(Listing.updated_at.desc())
        )
    ).all()
    return [await item_out(session, row, lang) for row in rows]
