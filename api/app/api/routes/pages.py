"""Public pages API: path resolver, listing card, sitemaps, content blocks, employer requests (spec §9)."""

from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, Request, status
from redis.exceptions import RedisError
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import RedisDep, SessionDep
from app.core.config import settings
from app.models import Category, Listing, ListingTranslation, Location, Section
from app.models.i18n import tr
from app.models.pages import ContentBlock, EmployerRequest, SeoPage
from app.schemas.common import Lang
from app.schemas.pages import (
    ContentBlockOut,
    EmployerRequestIn,
    ListingDetail,
    NamedSlug,
    PlaceRef,
    ResolveOut,
    SitemapEntry,
    SitemapPage,
)
from app.seo.listing_page import build_listing_detail, get_public_listing, listing_state
from app.seo.paths import FEATURES, LANGS, list_path, listing_path
from app.seo.resolver import resolve_path
from app.services import antibot

router = APIRouter(tags=["pages"])

SITEMAP_PAGE = 40_000


@router.get("/resolve", response_model=ResolveOut)
async def resolve(
    session: SessionDep, lang: Lang, path: Annotated[str, Query(min_length=1, max_length=500)]
) -> ResolveOut:
    """Path without the language prefix, e.g. `empleo/transporte/conductor-ce/madrid`."""
    r = await resolve_path(session, lang, path)
    if r.type in {"not_found", "redirect"}:
        return ResolveOut(type=r.type, redirect=r.redirect)

    def named(c: Category | None) -> NamedSlug | None:
        return NamedSlug(key=c.slug["es"], slug=c.slug[lang], name=tr(c.name, lang)) if c else None

    location = None
    if r.location:
        parent = await session.get(Location, r.location.parent_id) if r.location.parent_id else None
        location = PlaceRef(
            slug=r.location.slug,
            level=r.location.level,
            name=tr(r.location.names, lang),
            parent_slug=parent.slug if parent else None,
            parent_name=tr(parent.names, lang) if parent else None,
        )
    return ResolveOut(
        type=r.type,
        section=NamedSlug(key=r.section.key, slug=r.section.slug[lang], name=tr(r.section.name, lang)),
        sector=named(r.sector),
        profession=named(r.profession),
        feature=r.feature,
        location=location,
        listing_id=r.listing.id if r.listing else None,
        listing_state=r.listing_state,
        alternates=r.alternates,
        tier=r.tier,
        indexable=r.indexable,
        count=r.count,
        title_override=r.title_override,
        description_override=r.description_override,
    )


@router.get("/listings/{listing_id}", response_model=ListingDetail)
async def listing_card(listing_id: int, session: SessionDep, lang: Lang = "es") -> ListingDetail:
    """Card, similar listings and everything needed for JobPosting JSON-LD."""
    return await build_listing_detail(session, await get_public_listing(session, listing_id), lang)


@router.get("/listings/{listing_id}/state")
async def listing_card_state(listing_id: int, session: SessionDep) -> dict[str, str]:
    """Cheap check for the web proxy: `gone` -> 410 (closed more than 90 days ago)."""
    listing = await session.scalar(select(Listing).where(Listing.id == listing_id))
    if listing is None or listing.status not in {"active", "expired", "closed"}:
        return {"state": "missing"}
    return {"state": listing_state(listing, datetime.now(UTC))}


# ---------------------------------------------------------------------------- sitemaps


@router.get("/sitemaps/index")
async def sitemap_index(session: SessionDep) -> dict[str, dict[str, int]]:
    """Page counts per language for the sitemap index: {"es": {"lists": 1, "listings": 1}}."""
    lists = dict(
        (
            await session.execute(
                select(SeoPage.lang, func.count()).where(SeoPage.indexable).group_by(SeoPage.lang)
            )
        ).all()
    )
    listings = dict(
        (
            await session.execute(
                select(ListingTranslation.lang, func.count())
                .join(Listing, Listing.id == ListingTranslation.listing_id)
                .where(Listing.status == "active")
                .group_by(ListingTranslation.lang)
            )
        ).all()
    )

    def pages(n: int) -> int:
        return max(1, -(-n // SITEMAP_PAGE))

    return {
        code: {"lists": pages(lists.get(code, 0)), "listings": pages(listings.get(code, 0))} for code in LANGS
    }


@router.get("/sitemaps/{lang}/{kind}", response_model=SitemapPage)
async def sitemap(
    lang: Lang, kind: Literal["lists", "listings"], session: SessionDep, page: Annotated[int, Query(ge=1)] = 1
) -> SitemapPage:
    """Indexable list pages or listing cards of one language, with hreflang alternates (spec §6)."""
    if kind == "lists":
        return await _lists_sitemap(session, lang, page)
    return await _listings_sitemap(session, lang, page)


async def _lists_sitemap(session, lang: str, page: int) -> SitemapPage:  # noqa: ANN001
    conds = [SeoPage.lang == lang, SeoPage.indexable]
    total = await session.scalar(select(func.count()).select_from(SeoPage).where(*conds)) or 0
    rows = (
        await session.scalars(
            select(SeoPage)
            .where(*conds)
            .order_by(SeoPage.id)
            .offset((page - 1) * SITEMAP_PAGE)
            .limit(SITEMAP_PAGE)
        )
    ).all()
    sections = {s.key: s for s in (await session.scalars(select(Section))).all()}
    categories = {c.slug["es"]: c for c in (await session.scalars(select(Category))).all()}
    by_id = {c.id: c for c in categories.values()}

    def path(row: SeoPage, target: str) -> str:
        category = categories.get(row.category_key) if row.category_key else None
        sector = by_id.get(category.parent_id) if category and category.parent_id else None
        profession = category if category and category.parent_id else None
        if category and not category.parent_id:
            sector = category
        return list_path(
            sections[row.section_key].slug[target],
            sector.slug[target] if sector else None,
            profession.slug[target] if profession else None,
            FEATURES[row.feature][target] if row.feature else None,
            row.location_slug,
        )

    items = [
        SitemapEntry(
            path=path(r, lang), lastmod=r.last_listing_at, alternates={code: path(r, code) for code in LANGS}
        )
        for r in rows
        if r.section_key in sections
    ]
    return SitemapPage(items=items, page=page, pages=max(1, -(-total // SITEMAP_PAGE)))


async def _listings_sitemap(session, lang: str, page: int) -> SitemapPage:  # noqa: ANN001
    has_text = select(ListingTranslation.listing_id).where(ListingTranslation.lang == lang)
    conds = [Listing.status == "active", Listing.id.in_(has_text)]
    total = await session.scalar(select(func.count()).select_from(Listing).where(*conds)) or 0
    rows = (
        await session.scalars(
            select(Listing)
            .where(*conds)
            .options(selectinload(Listing.translations))
            .order_by(Listing.id)
            .offset((page - 1) * SITEMAP_PAGE)
            .limit(SITEMAP_PAGE)
        )
    ).all()
    sections = {s.id: s for s in (await session.scalars(select(Section))).all()}
    items = []
    for listing in rows:
        texts = {t.lang: t for t in listing.translations}
        section = sections[listing.section_id]
        alternates = {
            code: listing_path(section.slug[code], code, texts[code].slug, listing.id)
            for code in LANGS
            if code in texts
        }
        items.append(SitemapEntry(path=alternates[lang], lastmod=listing.updated_at, alternates=alternates))
    return SitemapPage(items=items, page=page, pages=max(1, -(-total // SITEMAP_PAGE)))


# ---------------------------------------------------------------------------- content and forms


@router.get("/content/{key}", response_model=ContentBlockOut)
async def content(key: str, session: SessionDep, lang: Lang = "es") -> ContentBlockOut:
    """Static texts; a missing translation falls back to Spanish (spec §2)."""
    rows = {
        b.lang: b
        for b in (
            await session.scalars(
                select(ContentBlock).where(ContentBlock.key == key, ContentBlock.lang.in_([lang, "es"]))
            )
        ).all()
    }
    block = rows.get(lang) or rows.get("es")
    if block is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Content not found")
    return ContentBlockOut.model_validate(block, from_attributes=True)


@router.post("/employer-requests", status_code=status.HTTP_201_CREATED)
async def employer_request(
    body: EmployerRequestIn, request: Request, session: SessionDep, redis: RedisDep
) -> dict[str, int]:
    ip = request.client.host if request.client else None
    if antibot.is_honeypot(body.website):
        antibot.log.info("honeypot: employer request from %s dropped", ip)
        return {"id": 0}
    await antibot.require_human(body.captcha, ip)
    if ip:
        try:
            key = f"rl:employer:{ip}"
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, 3600)
            if count > settings.applications_per_ip_per_hour:
                raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many requests, try again later")
        except RedisError:
            pass
    row = EmployerRequest(
        **body.model_dump(exclude={"consent", "website", "captcha"}),
        consent_at=datetime.now(UTC),
        consent_version=settings.privacy_policy_version,
        ip=ip,
    )
    session.add(row)
    await session.commit()
    return {"id": row.id}
