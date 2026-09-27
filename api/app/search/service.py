"""Search orchestration for GET /v1/listings: tier 1, filters, backend, facets cache, relaxations."""

from collections.abc import Mapping
from dataclasses import replace

from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models import AttributeDefinition, Category, Listing, Location, SearchMiss, Section
from app.models.i18n import tr
from app.schemas.search import (
    CategoryFacet,
    FacetGroup,
    FacetValue,
    ListingCardWithDistance,
    PlaceFacet,
    Relaxation,
    SearchResponse,
    SelectedCategory,
    SelectedPlace,
)
from app.schemas.search import Understood as UnderstoodOut
from app.search.backend import FacetResult, PlaceRef, SearchBackend, SearchQuery
from app.search.params import (
    BOOL_KEYS,
    RADII,
    AttrSpec,
    cache_params,
    canonical_query,
    parse_filters,
)
from app.search.postgres import PostgresSearchBackend
from app.search.text import normalize
from app.search import spelling
from app.search.understanding import get_dictionary, understand
from app.services.attributes import attribute_definitions
from app.services.cache import cached
from app.services.listings import public_cards

MULTI_GROUPS = {"schedule", "contract"}
SINGLE_GROUPS = {"posted", "salary_min", "radius"}


def get_backend(session: AsyncSession) -> SearchBackend:
    """The only place that knows the implementation (swap for Meilisearch here)."""
    return PostgresSearchBackend(session)


# ---------------------------------------------------------------------------- tier 1


async def resolve_category(session: AsyncSession, section: Section | None, slug: str, lang: str) -> Category:
    stmt = select(Category).where(
        (Category.slug[lang].astext == slug) | (Category.slug["es"].astext == slug), Category.is_enabled
    )
    if section:
        stmt = stmt.where(Category.section_id == section.id)
    category = (await session.scalars(stmt.limit(1))).first()
    if category is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown category {slug!r}")
    return category


async def resolve_place(session: AsyncSession, slug: str) -> tuple[Location, PlaceRef]:
    geom = func.ST_GeomFromWKB(func.ST_AsBinary(Location.geog))
    row = (
        await session.execute(
            select(Location, func.ST_Y(geom), func.ST_X(geom)).where(
                Location.slug == slug, Location.level.in_(["municipio", "provincia", "comunidad"])
            )
        )
    ).first()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown location {slug!r}")
    loc, lat, lon = row
    return loc, PlaceRef(loc.id, loc.level, loc.slug, lat, lon, loc.parent_id)


async def filterable_definitions(
    session: AsyncSession, section: Section | None, category: Category | None
) -> list[AttributeDefinition]:
    """Section tags are filters in the whole section; category attributes only once it is chosen."""
    return await attribute_definitions(
        session, section_id=section.id if section else None, category=category, filterable_only=True
    )


def attribute_specs(definitions: list[AttributeDefinition]) -> dict[str, AttrSpec]:
    return {a.key: AttrSpec(a.key, a.type, tuple(o["value"] for o in a.options)) for a in definitions}


# ---------------------------------------------------------------------------- output helpers


def _selected_category(c: Category, lang: str, parent: Category | None) -> SelectedCategory:
    return SelectedCategory(
        id=c.id,
        key=c.slug["es"],
        slug=c.slug[lang],
        slugs=c.slug,
        name=tr(c.name, lang),
        parent=_selected_category(parent, lang, None) if parent else None,
    )


async def _selected_place(session: AsyncSession, loc: Location, lang: str) -> SelectedPlace:
    parent = await session.get(Location, loc.parent_id) if loc.parent_id else None
    return SelectedPlace(
        slug=loc.slug,
        level=loc.level,
        name=tr(loc.names, lang),
        parent_slug=parent.slug if parent else None,
        parent_name=tr(parent.names, lang) if parent else None,
    )


async def _category_facets(
    session: AsyncSession, section_id: int | None, selected: Category | None, facets: FacetResult, lang: str
) -> list[CategoryFacet]:
    counts = {int(b.value): b.count for b in facets.categories}
    stmt = select(Category).where(Category.is_enabled)
    if section_id:
        stmt = stmt.where(Category.section_id == section_id)
    categories = (await session.scalars(stmt.order_by(Category.sort, Category.id))).all()
    children: dict[int | None, list[Category]] = {}
    for c in categories:
        children.setdefault(c.parent_id, []).append(c)

    def total(c: Category) -> int:
        return counts.get(c.id, 0) + sum(counts.get(ch.id, 0) for ch in children.get(c.id, []))

    if selected is None:
        shown = children.get(None, [])  # sectors
    elif selected.parent_id is None:
        shown = children.get(selected.id, []) or [selected]  # professions of the sector
    else:
        shown = children.get(selected.parent_id, [])  # sibling professions
    return [
        CategoryFacet(
            id=c.id,
            slug=c.slug[lang],
            key=c.slug["es"],
            name=tr(c.name, lang),
            count=total(c),
            selected=selected is not None and c.id == selected.id,
        )
        for c in shown
    ]


async def _place_facets(
    session: AsyncSession, facets: FacetResult, selected: Location | None, lang: str
) -> list[PlaceFacet]:
    ids = [int(b.value) for b in facets.places]
    names = {
        loc.id: loc for loc in (await session.scalars(select(Location).where(Location.id.in_(ids)))).all()
    }
    return [
        PlaceFacet(
            slug=names[int(b.value)].slug,
            name=tr(names[int(b.value)].names, lang),
            count=b.count,
            selected=selected is not None and selected.id == int(b.value),
        )
        for b in facets.places
        if int(b.value) in names
    ]


def _facet_groups(facets: FacetResult, definitions: list[AttributeDefinition], lang: str) -> list[FacetGroup]:
    groups: list[FacetGroup] = []
    # the radius filter is not shown (the client removed it); old links with ?radius= still work
    order = [*BOOL_KEYS, "salary_min", "schedule", "contract", "posted"]
    for key in order:
        if key in facets.groups:
            kind = "bool" if key in BOOL_KEYS else "multi" if key in MULTI_GROUPS else "single"
            groups.append(
                FacetGroup(
                    key=key,
                    tier=2,
                    type=kind,
                    values=[FacetValue(value=b.value, count=b.count) for b in facets.groups[key]],
                )
            )
    # section tags -> tier 2 (always shown in the section), category attributes -> tier 3 (spec §5)
    for definition in definitions:
        buckets = facets.groups.get(f"a.{definition.key}")
        if buckets is None:
            continue
        option_labels = {o["value"]: tr(o["label"], lang) for o in definition.options}
        groups.append(
            FacetGroup(
                key=f"a.{definition.key}",
                tier=2 if definition.section_id is not None else 3,
                label=tr(definition.label, lang),
                type="bool" if definition.type == "bool" else "multi",
                values=[
                    FacetValue(value=b.value, count=b.count, label=option_labels.get(b.value))
                    for b in buckets
                ],
            )
        )
    return groups


async def record_miss(session: AsyncSession, lang: str, section: str, q: str) -> None:
    stmt = insert(SearchMiss).values(lang=lang, section=section, q=normalize(q)[:200])
    await session.execute(
        stmt.on_conflict_do_update(
            constraint="uq_search_misses_lang_section_q",
            set_={"hits": SearchMiss.hits + 1, "last_seen": func.now()},
        )
    )
    await session.commit()


# ---------------------------------------------------------------------------- main entry


async def search_listings(
    session: AsyncSession,
    redis: Redis,
    *,
    lang: str,
    section_key: str | None,
    category_slug: str | None,
    location_slug: str | None,
    raw: Mapping[str, list[str]],
    per_page: int,
) -> SearchResponse:
    section = None
    if section_key:
        section = await session.scalar(select(Section).where(Section.key == section_key))
        if section is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown section {section_key!r}")

    category = await resolve_category(session, section, category_slug, lang) if category_slug else None
    parent = await session.get(Category, category.parent_id) if category and category.parent_id else None
    category_ids: tuple[int, ...] = ()
    if category:
        children = await session.scalars(select(Category.id).where(Category.parent_id == category.id))
        category_ids = (category.id, *children.all())

    location, place = (await resolve_place(session, location_slug)) if location_slug else (None, None)
    definitions = await filterable_definitions(session, section, category)
    specs = attribute_specs(definitions)
    filters = parse_filters(raw, specs, radius_allowed=place is not None and place.level == "municipio")

    # a word the site has never seen is repaired against the words it has ("дiвани" -> "диван"),
    # before anything else looks at the query
    corrections: list[tuple[str, str]] = []
    if filters.q:
        repaired, corrections = await spelling.repair(session, filters.q)
        if corrections:
            raw = {**raw, "q": [repaired]}
            filters = parse_filters(raw, specs, radius_allowed=place is not None and place.level == "municipio")

    # "диван у Валенсії": the town named inside the query becomes the place filter, and only the rest
    # is looked for in the text. Without this the words "у валенсії" are searched for in the ad itself
    # and find nothing. A town given in the path always wins.
    if filters.q and location is None:
        guess = understand(await get_dictionary(session, redis), filters.q, section_key)
        # only when something is left over: a query that is fully understood ("прибирання Валенсія")
        # belongs to a page of its own, and the caller sends the visitor there instead
        if guess.place and guess.rest and guess.rest != filters.q:
            location, place = await resolve_place(session, guess.place.slug)
            filters = parse_filters(
                {**raw, "q": [guess.rest]},
                specs,
                radius_allowed=place is not None and place.level == "municipio",
            )

    query = SearchQuery(
        lang=lang,
        section_id=section.id if section else None,
        category_ids=category_ids,
        place=place,
        filters=filters,
        attr_specs=specs,
        per_page=per_page,
    )
    backend = get_backend(session)
    page = await backend.search(query)

    facet_key = {
        "section": query.section_id,
        "categories": category_ids,
        "place": place.id if place else None,
        "filters": cache_params(filters),
        "specs": sorted(specs),
    }
    facets = await cached(
        redis, "facets", facet_key, settings.facets_cache_ttl, FacetResult, lambda: backend.facets(query)
    )

    listings = (
        await session.scalars(
            select(Listing)
            .where(Listing.id.in_([h.listing_id for h in page.hits]))
            .options(selectinload(Listing.translations))
        )
    ).all()
    by_id = {listing.id: listing for listing in listings}
    ordered = [by_id[h.listing_id] for h in page.hits if h.listing_id in by_id]
    distances = {h.listing_id: h.distance_km for h in page.hits}
    cards = [
        ListingCardWithDistance(**card.model_dump(), distance_km=distances.get(card.id))
        for card in await public_cards(session, ordered, lang)
    ]

    understood = None
    if filters.q:
        u = understand(await get_dictionary(session, redis), filters.q, section_key)
        u_category = await session.get(Category, u.category.id) if u.category else None
        u_parent = (
            await session.get(Category, u_category.parent_id) if u_category and u_category.parent_id else None
        )
        u_location = await session.get(Location, u.place.id) if u.place else None
        understood = UnderstoodOut(
            category=_selected_category(u_category, lang, u_parent) if u_category else None,
            location=await _selected_place(session, u_location, lang) if u_location else None,
            rest_q=u.rest,
            complete=u.complete,
        )

    relaxations: list[Relaxation] = []
    if page.total == 0:
        if filters.q:
            await record_miss(session, lang, section_key or "", filters.q)
        category_keys = {d.key for d in definitions if d.category_id is not None}
        relaxations = await _relaxations(session, backend, query, location, category_keys)

    return SearchResponse(
        items=cards,
        total=page.total,
        page=filters.page,
        per_page=per_page,
        pages=-(-page.total // per_page),
        canonical_query=canonical_query(filters),
        sort=filters.effective_sort,
        category=_selected_category(category, lang, parent) if category else None,
        location=await _selected_place(session, location, lang) if location else None,
        categories=await _category_facets(session, query.section_id, category, facets, lang),
        places=await _place_facets(session, facets, location, lang),
        spain_wide=facets.spain_wide,
        facets=_facet_groups(facets, definitions, lang),
        understood=understood,
        relaxations=relaxations,
        fuzzy=page.used_fuzzy,
        corrected=[[typed, used] for typed, used in corrections],
    )


async def _relaxations(
    session: AsyncSession,
    backend: SearchBackend,
    query: SearchQuery,
    location: Location | None,
    category_keys: set[str],
) -> list[Relaxation]:
    """Empty result: drop tier 3 -> bigger radius -> whole province -> whole Spain (spec §5)."""
    f = query.filters
    out: list[Relaxation] = []

    if tier3 := [f"a.{key}" for key in f.attrs if key in category_keys]:
        relaxed = f.without(*tier3)
        count = await backend.count(replace(query, filters=relaxed))
        out.append(Relaxation(kind="attributes", count=count, query=canonical_query(relaxed)))

    place = query.place
    if place and place.level == "municipio":
        bigger = next((r for r in RADII if r > (f.radius or 0)), None)
        if bigger:
            relaxed = replace(f, radius=bigger, page=1)
            count = await backend.count(replace(query, filters=relaxed))
            out.append(
                Relaxation(
                    kind="radius", count=count, query=canonical_query(relaxed), label_value=str(bigger)
                )
            )
        if location and location.parent_id:
            province, province_ref = await resolve_place(
                session, (await session.get(Location, location.parent_id)).slug
            )
            relaxed = f.without("radius")
            count = await backend.count(replace(query, place=province_ref, filters=relaxed))
            out.append(
                Relaxation(
                    kind="province",
                    count=count,
                    query=canonical_query(relaxed),
                    location=province.slug,
                    label_value=tr(province.names, query.lang),
                )
            )
    if place:
        relaxed = f.without("radius")
        count = await backend.count(replace(query, place=None, filters=relaxed))
        out.append(Relaxation(kind="spain", count=count, query=canonical_query(relaxed)))
    return out


def raw_params(multi_items: list[tuple[str, str]]) -> dict[str, list[str]]:
    raw: dict[str, list[str]] = {}
    for key, value in multi_items:
        raw.setdefault(key, []).append(value)
    return raw
