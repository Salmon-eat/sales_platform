"""Public listings: search with filters and facets, counters, autocomplete, query understanding."""

from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from app.api.deps import RedisDep, SessionDep
from app.models import Category, Listing
from app.schemas.common import Lang
from app.schemas.listing import ListingCard, ListingStats
from app.schemas.search import SearchResponse, SuggestResponse
from app.search.service import raw_params, search_listings
from app.search.suggest import suggest as build_suggest
from app.search.understanding import get_dictionary, understand
from app.services.listings import public_cards

router = APIRouter(tags=["listings"])

MADRID = ZoneInfo("Europe/Madrid")
TIER1_KEYS = {"lang", "section", "category", "location", "per_page"}


@router.get("/listings", response_model=SearchResponse)
async def listings(
    request: Request,
    session: SessionDep,
    redis: RedisDep,
    lang: Lang = "es",
    section: Annotated[str | None, Query(max_length=50, description="section key: empleo, servicios")] = None,
    category: Annotated[
        str | None, Query(max_length=120, description="category slug in `lang` or Spanish")
    ] = None,
    location: Annotated[str | None, Query(max_length=120, description="location slug")] = None,
    per_page: Annotated[int, Query(ge=1, le=50)] = 20,
) -> SearchResponse:
    """List + facets + total (spec §9).

    Tier 2/3 filters and q/sort/page come as query params (spec §5); unknown keys and values are ignored.
    `canonical_query` is the normalized query string: pages redirect when it differs from the request.
    """
    raw = raw_params([(k, v) for k, v in request.query_params.multi_items() if k not in TIER1_KEYS])
    return await search_listings(
        session,
        redis,
        lang=lang,
        section_key=section,
        category_slug=category,
        location_slug=location,
        raw=raw,
        per_page=per_page,
    )


@router.get("/listings/stats", response_model=ListingStats)
async def stats(
    session: SessionDep,
    section: Annotated[str | None, Query(max_length=50)] = None,
    category: Annotated[str | None, Query(max_length=100)] = None,
) -> ListingStats:
    conds = [Listing.status == "active"]
    if category:
        ids = select(Category.id).where(Category.slug["es"].astext == category)
        conds.append(
            or_(
                Listing.category_id.in_(ids),
                Listing.category_id.in_(select(Category.id).where(Category.parent_id.in_(ids))),
            )
        )
    start_of_day = datetime.now(MADRID).replace(hour=0, minute=0, second=0, microsecond=0)
    total, today = (
        await session.execute(
            select(func.count(), func.count().filter(Listing.published_at >= start_of_day)).where(*conds)
        )
    ).one()
    return ListingStats(total=total, today=today)


MAX_CARD_IDS = 100
# statuses a visitor may have seen the ad in: it was on the site, and now it is paused, over or sold
WAS_PUBLIC = ("active", "paused", "expired", "closed")


@router.get("/listings/cards", response_model=list[ListingCard])
async def cards(
    session: SessionDep,
    ids: Annotated[str, Query(max_length=1000, description="comma-separated listing ids, e.g. 12,7,31")],
    lang: Lang = "es",
    with_closed: Annotated[
        bool, Query(description="also ads that were public and are no longer (history: shown as inactive)")
    ] = False,
) -> list[ListingCard]:
    """Listings by id, in the order given: saved listings, application history, viewed history (spec §10).

    Normally only active ones; ids of closed or removed listings are left out and the client shows them as
    no longer available. With with_closed the ones that were once public come back too, marked inactive.
    Drafts, ads waiting for moderation and rejected ones never do.
    """
    wanted = [int(part) for part in ids.split(",") if part.strip().isdigit()][:MAX_CARD_IDS]
    if not wanted:
        return []
    statuses = WAS_PUBLIC if with_closed else ("active",)
    rows = (
        await session.scalars(
            select(Listing)
            .where(Listing.id.in_(wanted), Listing.status.in_(statuses))
            .options(selectinload(Listing.translations))
        )
    ).all()
    order = {listing_id: i for i, listing_id in enumerate(wanted)}
    return await public_cards(session, sorted(rows, key=lambda row: order[row.id]), lang)


@router.get("/suggest", response_model=SuggestResponse)
async def suggest(
    session: SessionDep,
    redis: RedisDep,
    q: Annotated[str, Query(min_length=2, max_length=100)],
    lang: Lang = "es",
) -> SuggestResponse:
    """Autocomplete from 2 characters; cached per (lang, prefix) for 10 minutes."""
    return await build_suggest(session, redis, q, lang)


@router.get("/search/understand")
async def understand_query(
    session: SessionDep,
    redis: RedisDep,
    q: Annotated[str, Query(min_length=1, max_length=200)],
    lang: Lang = "es",
    section: Annotated[str | None, Query(max_length=50)] = None,
) -> dict:
    """Debug view of query understanding: which profession/place were recognized and what is left."""
    u = understand(await get_dictionary(session, redis), q, section)
    return {
        "category": {"id": u.category.id, "slug": u.category.slug.get(lang), "key": u.category.slug["es"]}
        if u.category
        else None,
        "location": {"slug": u.place.slug, "level": u.place.level} if u.place else None,
        "rest_q": u.rest,
        "complete": u.complete,
    }
