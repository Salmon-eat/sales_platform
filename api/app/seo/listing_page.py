"""Public listing card (L4): text in the requested language, attribute labels, similar listings, state."""

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Category, Listing, Location, Section, User
from app.models.i18n import format_number, tr
from app.schemas.pages import (
    AttributeValue,
    ListingDetail,
    ListingPhotoOut,
    NamedSlug,
    PlaceRef,
    SellerBrief,
)
from app.seo.rules import closed_state
from app.services import photos as photo_files
from app.services import questions, reviews
from app.services.attributes import attribute_definitions
from app.services.listings import public_cards

SIMILAR = 6
PUBLIC_STATUSES = {"active", "expired", "closed"}


def listing_state(listing: Listing, now: datetime) -> str:
    if listing.status == "active":
        return "active"
    return closed_state(listing.closed_at if listing.status == "closed" else listing.expires_at, now)


async def get_public_listing(session: AsyncSession, listing_id: int) -> Listing:
    listing = await session.scalar(
        select(Listing)
        .where(Listing.id == listing_id)
        .options(selectinload(Listing.translations), selectinload(Listing.photos))
    )
    if listing is None or listing.status not in PUBLIC_STATUSES:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Listing not found")
    return listing


async def similar_listings(session: AsyncSession, listing: Listing, limit: int = SIMILAR) -> list[Listing]:
    """Same profession first, nearby first (same municipality, then by distance), then the same sector."""
    category = await session.get(Category, listing.category_id)
    sector_ids = (
        select(Category.id).where(
            or_(Category.id == category.parent_id, Category.parent_id == category.parent_id)
        )
        if category and category.parent_id
        else select(Category.id).where(Category.id == listing.category_id)
    )
    order = [(Listing.category_id != listing.category_id).asc()]
    if listing.geog is not None:
        order.append(
            func.coalesce(
                func.ST_Distance(
                    Listing.geog, select(Listing.geog).where(Listing.id == listing.id).scalar_subquery()
                ),
                1e9,
            )
        )
    order.append(Listing.published_at.desc())
    rows = await session.scalars(
        select(Listing)
        .where(Listing.status == "active", Listing.id != listing.id, Listing.category_id.in_(sector_ids))
        .options(selectinload(Listing.translations))
        .order_by(*order)
        .limit(limit)
    )
    return list(rows.all())


async def build_listing_detail(session: AsyncSession, listing: Listing, lang: str) -> ListingDetail:
    now = datetime.now(UTC)
    [card] = await public_cards(session, [listing], lang)
    by_lang = {t.lang: t for t in listing.translations}
    text = by_lang.get(lang) or by_lang[listing.original_lang]
    section = await session.get(Section, listing.section_id)

    category = await session.get(Category, listing.category_id)
    chain = [category]
    if category.parent_id:
        chain.insert(0, await session.get(Category, category.parent_id))

    defs = await attribute_definitions(session, section_id=listing.section_id, category=category)
    attributes = []
    for d in defs:
        value = listing.attributes.get(d.key)
        if value in (None, False, [], {}):
            continue
        labels = {o["value"]: tr(o["label"], lang) for o in d.options}
        if d.type == "bool":
            shown: list[str] = []
        elif d.type == "int_range":
            shown = [f"{value.get('min', '')}–{value.get('max', '')}"]
        elif d.type == "int":
            unit = tr(d.unit, lang) if d.unit else None
            shown = [f"{format_number(value, lang)} {unit}" if unit else format_number(value, lang)]
        else:
            shown = [labels.get(v, v) for v in (value if isinstance(value, list) else [value])]
        attributes.append(
            AttributeValue(
                key=d.key,
                label=tr(d.label, lang),
                values=shown,
                group="tags" if d.section_id is not None else "category",
            )
        )

    province = None
    lat = lon = None
    if listing.location_id:
        municipio = await session.get(Location, listing.location_id)
        if municipio and municipio.parent_id:
            p = await session.get(Location, municipio.parent_id)
            province = PlaceRef(slug=p.slug, level=p.level, name=tr(p.names, lang))
    if listing.geog is not None:
        geom = func.ST_GeomFromWKB(func.ST_AsBinary(Listing.geog))
        lat, lon = (
            await session.execute(select(func.ST_Y(geom), func.ST_X(geom)).where(Listing.id == listing.id))
        ).one()

    similar = await public_cards(session, await similar_listings(session, listing), lang)

    seller = None
    if listing.owner_id:
        owner = await session.get(User, listing.owner_id)
        if owner is not None and owner.is_active and owner.deleted_at is None:
            average, count = await reviews.rating_of(session, owner.id)
            seller = SellerBrief(
                id=owner.id,
                name=owner.name or (owner.email.split("@")[0] if owner.email else "—"),
                rating=average,
                reviews_count=count,
            )
    return ListingDetail(
        **card.model_dump(),
        description=text.description,
        seller=seller,
        photos=[
            ListingPhotoOut(
                path=photo.path,
                thumb=photo_files.thumb_path(photo.path),
                width=photo.width,
                height=photo.height,
            )
            for photo in listing.photos
        ],
        requirements=text.requirements,
        conditions=text.conditions,
        original_lang=listing.original_lang,
        translations=sorted(by_lang),
        salary_monthly_min=listing.salary_monthly_min,
        start_date=listing.start_date,
        duration_months=listing.duration_months,
        attributes=attributes,
        questions=questions.public(listing.questions or [], lang),
        expires_at=listing.expires_at,
        closed_at=listing.closed_at,
        state=listing_state(listing, now),
        section_slug=section.slug[lang],
        section_name=tr(section.name, lang),
        category_path=[NamedSlug(key=c.slug["es"], slug=c.slug[lang], name=tr(c.name, lang)) for c in chain],
        location_detail=card.location,
        province=province,
        lat=lat,
        lon=lon,
        similar=similar,
    )
