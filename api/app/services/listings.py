from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from geoalchemy2 import WKTElement
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    AttributeDefinition,
    Category,
    Listing,
    ListingTranslation,
    Location,
    Section,
    User,
    UserRole,
)
from app.models.i18n import tr
from app.schemas.listing import (
    AdminListingDetail,
    AdminListingItem,
    ListingCard,
    ListingCategoryRef,
    ListingIn,
    LocationBrief,
    PointIn,
    TranslationOut,
)
from app.seo.paths import listing_path
from app.services.attributes import attribute_definitions
from app.services.card_tags import card_tags
from app.services.listing_rules import (
    AttributeSpec,
    TransitionError,
    apply_action,
    listing_slug,
    monthly_min,
    validate_attributes,
)

ADMIN_LANG = "uk"  # default language of admin lists; the admin UI sends its own (AdminLang)
FALLBACK_LANGS = ("es", "en", "uk", "ru")


def unprocessable(field: str, *messages: str) -> HTTPException:
    return HTTPException(
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        [{"loc": ["body", field], "msg": m, "type": "value_error"} for m in messages],
    )


def can_edit(user: User, listing: Listing) -> bool:
    """Admins edit everything; managers edit the listings they created (BOLA check, spec §9)."""
    return user.role == UserRole.ADMIN or listing.created_by == user.id


def ensure_can_edit(user: User, listing: Listing) -> None:
    if not can_edit(user, listing):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the author or an admin can change this listing")


async def get_listing(session: AsyncSession, listing_id: int) -> Listing:
    listing = await session.scalar(
        select(Listing).where(Listing.id == listing_id).options(selectinload(Listing.translations))
    )
    if listing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Listing not found")
    return listing


async def attribute_specs(session: AsyncSession, category: Category) -> list[AttributeSpec]:
    """Section tags + own attributes + the ones inherited from the parent sector."""
    rows = await attribute_definitions(session, section_id=category.section_id, category=category)
    return [AttributeSpec(a.key, a.type, tuple(o["value"] for o in a.options), a.required) for a in rows]


async def point_of(session: AsyncSession, geog_column: Any, where: Any) -> PointIn | None:
    geom = func.ST_GeomFromWKB(func.ST_AsBinary(geog_column))
    row = (await session.execute(select(func.ST_Y(geom), func.ST_X(geom)).where(where))).first()
    return PointIn(lat=row[0], lon=row[1]) if row and row[0] is not None else None


async def save_listing(
    session: AsyncSession, user: User, data: ListingIn, listing: Listing | None = None
) -> Listing:
    category = await session.get(Category, data.category_id)
    if category is None:
        raise unprocessable("category_id", "category_not_found")
    section = await session.get(Section, category.section_id)
    if section is not None and section.kind == "services":
        # documents, training: permanent agency services with their own pages, not listings
        raise unprocessable("category_id", "category_is_service")

    # location: a municipality, or a village -> its municipality + the village point
    municipality: Location | None = None
    point = data.point
    if data.location_scope == "local":
        chosen = await session.get(Location, data.location_id)
        if chosen is None or chosen.level not in {"municipio", "localidad"}:
            raise unprocessable("location_id", "location_required")
        municipality = (
            chosen if chosen.level == "municipio" else await session.get(Location, chosen.parent_id)
        )
        if point is None:
            point = await point_of(session, Location.geog, Location.id == chosen.id)

    attributes, errors = validate_attributes(await attribute_specs(session, category), data.attributes)
    if errors:
        raise unprocessable("attributes", *errors)

    if listing is None:
        listing = Listing(created_by=user.id, status="draft", translations=[])
        session.add(listing)

    listing.section_id = category.section_id
    listing.category_id = category.id
    listing.location_scope = data.location_scope
    listing.location_id = municipality.id if municipality else None
    listing.geog = WKTElement(f"POINT({point.lon} {point.lat})", srid=4326) if point else None
    # the language shown where a translation is missing: Spanish, else the first filled one
    langs = {t.lang for t in data.translations}
    listing.original_lang = next(code for code in FALLBACK_LANGS if code in langs)
    listing.salary_min, listing.salary_max, listing.salary_period = (
        data.salary_min,
        data.salary_max,
        data.salary_period,
    )
    listing.salary_monthly_min = monthly_min(data.salary_min, data.salary_max, data.salary_period)
    listing.housing, listing.no_language, listing.no_experience = (
        data.housing,
        data.no_language,
        data.no_experience,
    )
    listing.schedule = list(data.schedule)
    listing.contract = data.contract
    listing.vacancies, listing.start_date = data.vacancies, data.start_date
    listing.is_urgent, listing.duration_months = data.is_urgent, data.duration_months
    listing.attributes = attributes
    listing.contact = data.contact.model_dump(exclude_none=True)
    listing.source = data.source
    listing.employer_name = data.employer_name if data.source != "agency" else None
    listing.is_pinned = data.is_pinned
    if data.expires_at is not None:
        listing.expires_at = data.expires_at

    # translations: upsert the given languages, drop the removed ones
    location_slug = municipality.slug if municipality else None
    existing = {t.lang: t for t in listing.translations}
    keep = set()
    for t in data.translations:
        row = existing.get(t.lang)
        if row is None:
            row = ListingTranslation(lang=t.lang)
            listing.translations.append(row)
        row.title, row.description = t.title, t.description
        row.requirements, row.conditions = t.requirements, t.conditions
        row.slug = listing_slug(t.title, t.lang, location_slug)
        row.is_machine = False
        keep.add(t.lang)
    for lang, row in existing.items():
        if lang not in keep:
            listing.translations.remove(row)

    await session.commit()
    return await get_listing(session, listing.id)


PUBLISH_LANG = "es"  # admin spec §6: a draft can be saved any time, published only with the Spanish text


async def perform_action(session: AsyncSession, listing: Listing, action: str, days: int) -> Listing:
    if action == "publish" and not any(t.lang == PUBLISH_LANG for t in listing.translations):
        raise HTTPException(status.HTTP_409_CONFLICT, "publish_needs_es")
    try:
        change = apply_action(
            action,
            status=listing.status,
            published_at=listing.published_at,
            expires_at=listing.expires_at,
            closed_at=listing.closed_at,
            now=datetime.now(UTC),
            days=days,
        )
    except TransitionError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    listing.status = change.status
    listing.published_at, listing.expires_at, listing.closed_at = (
        change.published_at,
        change.expires_at,
        change.closed_at,
    )
    await session.commit()
    return await get_listing(session, listing.id)


async def expire_listings(session: AsyncSession) -> int:
    """Worker job: active listings past expires_at -> expired."""
    result = await session.execute(
        update(Listing)
        .where(Listing.status == "active", Listing.expires_at.is_not(None), Listing.expires_at <= func.now())
        .values(status="expired")
    )
    await session.commit()
    return result.rowcount or 0


# ---------------------------------------------------------------------------- output helpers


async def _location_briefs(session: AsyncSession, ids: set[int], lang: str) -> dict[int, LocationBrief]:
    if not ids:
        return {}
    rows = await session.execute(select(Location).where(Location.id.in_(ids)))
    locations = rows.scalars().all()
    parents = {
        p.id: p
        for p in (
            await session.scalars(
                select(Location).where(
                    Location.id.in_({item.parent_id for item in locations if item.parent_id})
                )
            )
        ).all()
    }
    return {
        loc.id: LocationBrief(
            id=loc.id,
            level=loc.level,
            slug=loc.slug,
            name=tr(loc.names, lang),
            parent_name=tr(parents[loc.parent_id].names, lang) if loc.parent_id in parents else None,
        )
        for loc in locations
    }


async def _categories(session: AsyncSession, ids: set[int]) -> dict[int, Category]:
    rows = await session.scalars(select(Category).where(Category.id.in_(ids)))
    categories = {c.id: c for c in rows}
    parent_ids = {c.parent_id for c in categories.values() if c.parent_id and c.parent_id not in categories}
    if parent_ids:
        categories.update(
            {c.id: c for c in await session.scalars(select(Category).where(Category.id.in_(parent_ids)))}
        )
    return categories


def _translation(listing: Listing, lang: str) -> ListingTranslation:
    by_lang = {t.lang: t for t in listing.translations}
    return by_lang.get(lang) or by_lang.get(listing.original_lang) or listing.translations[0]


async def admin_items(
    session: AsyncSession, user: User, listings: list[Listing], lang: str = ADMIN_LANG
) -> list[AdminListingItem]:
    categories = await _categories(session, {item.category_id for item in listings})
    locations = await _location_briefs(
        session, {item.location_id for item in listings if item.location_id}, lang
    )
    authors = dict(
        (
            await session.execute(
                select(User.id, User.email).where(
                    User.id.in_({item.created_by for item in listings if item.created_by})
                )
            )
        ).all()
    )
    items = []
    for item in listings:
        category = categories[item.category_id]
        sector = categories.get(category.parent_id) if category.parent_id else None
        items.append(
            AdminListingItem(
                id=item.id,
                status=item.status,
                title=_translation(item, lang).title,
                langs=[t.lang for t in item.translations],
                original_lang=item.original_lang,
                category_name=tr(category.name, lang),
                sector_name=tr(sector.name, lang) if sector else None,
                location=locations.get(item.location_id) if item.location_id else None,
                location_scope=item.location_scope,
                salary_min=item.salary_min,
                salary_max=item.salary_max,
                salary_period=item.salary_period,
                is_pinned=item.is_pinned,
                published_at=item.published_at,
                expires_at=item.expires_at,
                created_by_email=authors.get(item.created_by),
                updated_at=item.updated_at,
                can_edit=can_edit(user, item),
            )
        )
    return items


async def admin_detail(
    session: AsyncSession, user: User, listing: Listing, lang: str = ADMIN_LANG
) -> AdminListingDetail:
    locations = await _location_briefs(session, {listing.location_id} if listing.location_id else set(), lang)
    author = await session.get(User, listing.created_by) if listing.created_by else None
    return AdminListingDetail(
        **{
            column: getattr(listing, column)
            for column in (
                "id",
                "status",
                "section_id",
                "category_id",
                "location_scope",
                "original_lang",
                "salary_min",
                "salary_max",
                "salary_period",
                "salary_monthly_min",
                "housing",
                "no_language",
                "no_experience",
                "schedule",
                "contract",
                "vacancies",
                "start_date",
                "is_urgent",
                "duration_months",
                "attributes",
                "contact",
                "source",
                "employer_name",
                "is_pinned",
                "published_at",
                "expires_at",
                "closed_at",
                "created_at",
                "updated_at",
            )
        },  # fmt: skip
        location=locations.get(listing.location_id) if listing.location_id else None,
        point=await point_of(session, Listing.geog, Listing.id == listing.id),
        created_by_email=author.email if author else None,
        translations=[TranslationOut.model_validate(t, from_attributes=True) for t in listing.translations],
        can_edit=can_edit(user, listing),
    )


async def public_cards(session: AsyncSession, listings: list[Listing], lang: str) -> list[ListingCard]:
    categories = await _categories(session, {item.category_id for item in listings})
    locations = await _location_briefs(
        session, {item.location_id for item in listings if item.location_id}, lang
    )
    sections = {s.id: s for s in (await session.scalars(select(Section))).all()}
    # the whole dictionary is small (tens of rows): one query for all cards
    definitions = (await session.scalars(select(AttributeDefinition))).all()
    cards = []
    for item in listings:
        text = _translation(item, lang)
        category = categories[item.category_id]
        sector = categories.get(category.parent_id) if category.parent_id else None

        def ref(c: Category) -> ListingCategoryRef:
            return ListingCategoryRef(key=c.slug["es"], slug=c.slug[lang], name=tr(c.name, lang), icon=c.icon)

        cards.append(
            ListingCard(
                id=item.id,
                slug=text.slug,
                path=listing_path(sections[item.section_id].slug[lang], lang, text.slug, item.id),
                lang=text.lang,
                is_translated=text.lang == lang,
                title=text.title,
                section_key=sections[item.section_id].key,
                category=ref(category),
                sector=ref(sector) if sector else None,
                location=locations.get(item.location_id) if item.location_id else None,
                location_scope=item.location_scope,
                salary_min=item.salary_min,
                salary_max=item.salary_max,
                salary_period=item.salary_period,
                housing=item.housing,
                no_language=item.no_language,
                no_experience=item.no_experience,
                source=item.source,
                employer_name=item.employer_name,
                is_urgent=item.is_urgent,
                is_pinned=item.is_pinned,
                published_at=item.published_at,
                schedule=item.schedule or [],
                contract=item.contract,
                vacancies=item.vacancies,
                tags=card_tags(
                    item,
                    [
                        d
                        for d in definitions
                        if d.section_id == item.section_id
                        or d.category_id in (category.id, category.parent_id)
                    ],
                    lang,
                ),
            )
        )
    return cards
