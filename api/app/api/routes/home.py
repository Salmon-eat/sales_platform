"""Everything the home page shows, in one request: the sections and the newest ads. Paid ads have no
block here: like on other boards, they come first in their section and in the search."""

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import RedisDep, SessionDep
from app.models import Category, Listing, Section
from app.models.i18n import tr
from app.schemas.common import Lang
from app.schemas.home import HomeOut, HomeSection, HomeTotals
from app.services.cache import cached
from app.services.listings import public_cards

router = APIRouter(tags=["home"])

FRESH = 12
CATEGORY_HINTS = 4
CACHE_TTL = 60


@router.get("/home", response_model=HomeOut)
async def home(session: SessionDep, redis: RedisDep, lang: Annotated[Lang, Query()] = "es") -> HomeOut:
    """Cached for a minute: the page is the same for everyone who speaks the same language."""
    return await cached(redis, "home", {"lang": lang}, CACHE_TTL, HomeOut, lambda: _build(session, lang))


async def _build(session: SessionDep, lang: str) -> HomeOut:
    active = Listing.status == "active"
    today = datetime.now(UTC) - timedelta(days=1)

    total = await session.scalar(select(func.count()).select_from(Listing).where(active)) or 0
    fresh_count = (
        await session.scalar(
            select(func.count()).select_from(Listing).where(active, Listing.published_at >= today)
        )
        or 0
    )

    counts = dict(
        (
            await session.execute(
                select(Listing.section_id, func.count()).where(active).group_by(Listing.section_id)
            )
        ).all()
    )
    # only the board's own sections; the agency's service pages are not a pile of listings to count
    sections = (
        await session.scalars(
            select(Section)
            .where(Section.is_enabled.is_(True), Section.kind == "listings")
            .order_by(Section.sort)
        )
    ).all()
    top_categories = (
        await session.scalars(
            select(Category).where(Category.parent_id.is_(None)).order_by(Category.sort, Category.id)
        )
    ).all()

    blocks = [
        HomeSection(
            key=section.key,
            slug=section.slug[lang],
            name=tr(section.name, lang),
            count=counts.get(section.id, 0),
            categories=[
                {"slug": c.slug[lang], "name": tr(c.name, lang)}
                for c in top_categories
                if c.section_id == section.id
            ][:CATEGORY_HINTS],
        )
        for section in sections
    ]

    fresh_rows = (
        await session.scalars(
            _cards_query()
            .where(active)
            .order_by(func.coalesce(Listing.bumped_at, Listing.published_at).desc(), Listing.id.desc())
            .limit(FRESH)
        )
    ).all()

    return HomeOut(
        totals=HomeTotals(listings=total, today=fresh_count, sections=len(blocks)),
        sections=blocks,
        fresh=await public_cards(session, list(fresh_rows), lang),
    )


def _cards_query():
    return select(Listing).options(selectinload(Listing.translations))
