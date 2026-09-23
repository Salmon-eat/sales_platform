"""GET /v1/resolve: URL path -> section, category chain, feature, location or listing; redirects; alternates.

Rules (spec §6):
1. The first segment is the section by its localized slug.
2. The last segment is checked against locations (incl. provincia-/comunidad- prefixes).
3. Segments in between form a valid sector -> profession chain; a profession without its sector -> 301.
4. A slug from slug_history -> 301 to the current one; an unknown segment -> 404.
Slugs of another language are redirected to the slugs of the requested language.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Category, Listing, Location, Section, SlugHistory
from app.models.pages import SeoPage
from app.seo.paths import (
    FEATURES,
    LANGS,
    feature_by_slug,
    list_path,
    listing_path,
    offer_word_lang,
    parse_listing_tail,
)
from app.seo.rules import closed_state, threshold_of, tier_of


@dataclass
class Resolved:
    type: str  # list | listing | services | service | redirect | not_found
    redirect: str | None = None
    section: Section | None = None
    sector: Category | None = None
    profession: Category | None = None
    feature: str | None = None
    location: Location | None = None
    listing: Listing | None = None
    alternates: dict[str, str] = field(default_factory=dict)
    tier: str | None = None
    indexable: bool = False
    count: int | None = None
    title_override: str | None = None
    description_override: str | None = None
    listing_state: str | None = None


def seo_path_key(
    lang: str, section: str, category: str | None, feature: str | None, location: str | None
) -> str:
    return "|".join([lang, section, category or "-", feature or "-", location or "-"])


def build_list_path(
    lang: str,
    section: Section,
    sector: Category | None,
    profession: Category | None,
    feature: str | None,
    location: Location | None,
) -> str:
    return list_path(
        section.slug[lang],
        sector.slug[lang] if sector else None,
        profession.slug[lang] if profession else None,
        FEATURES[feature][lang] if feature else None,
        location.slug if location else None,
    )


async def _section(session: AsyncSession, lang: str, slug: str) -> tuple[Section | None, bool]:
    """-> (section, needs_redirect)."""
    sections = (await session.scalars(select(Section).where(Section.is_enabled))).all()
    for s in sections:
        if s.slug[lang] == slug:
            return s, False
    for s in sections:
        if slug in s.slug.values():
            return s, True
    old = await session.scalar(
        select(SlugHistory.entity_id).where(
            SlugHistory.entity_type == "section", SlugHistory.old_slug == slug
        )
    )
    section = next((s for s in sections if s.id == old), None)
    return section, section is not None


async def _category(
    session: AsyncSession, section: Section, lang: str, slug: str
) -> tuple[Category | None, bool]:
    categories = (
        await session.scalars(select(Category).where(Category.section_id == section.id, Category.is_enabled))
    ).all()
    for c in categories:
        if c.slug[lang] == slug:
            return c, False
    for c in categories:
        if slug in c.slug.values():
            return c, True
    old = await session.scalar(
        select(SlugHistory.entity_id).where(
            SlugHistory.entity_type == "category", SlugHistory.old_slug == slug
        )
    )
    category = next((c for c in categories if c.id == old), None)
    return category, category is not None


async def _location(session: AsyncSession, slug: str) -> tuple[Location | None, bool]:
    levels = ["municipio", "provincia", "comunidad"]
    location = await session.scalar(select(Location).where(Location.slug == slug, Location.level.in_(levels)))
    if location:
        return location, False
    old = await session.scalar(
        select(SlugHistory.entity_id).where(
            SlugHistory.entity_type == "location", SlugHistory.old_slug == slug
        )
    )
    if old:
        location = await session.scalar(
            select(Location).where(Location.id == old, Location.level.in_(levels))
        )
        return location, location is not None
    return None, False


async def _seo(session: AsyncSession, resolved: Resolved, lang: str) -> None:
    level = "profession" if resolved.profession else "sector" if resolved.sector else None
    has_location, has_feature = resolved.location is not None, resolved.feature is not None
    resolved.tier = tier_of(level, has_location, has_feature)
    category = resolved.profession or resolved.sector
    row = await session.scalar(
        select(SeoPage).where(
            SeoPage.path_key
            == seo_path_key(
                lang,
                resolved.section.key,  # type: ignore[union-attr]
                category.slug["es"] if category else None,
                resolved.feature,
                resolved.location.slug if resolved.location else None,
            )
        )
    )
    if row:
        resolved.indexable, resolved.count = row.indexable, row.active_count
        resolved.title_override, resolved.description_override = row.title_override, row.description_override
    # L1 without location is always indexed; other pages only once the worker counted them above the threshold
    if threshold_of(level, has_location, has_feature) == 0:
        resolved.indexable = True


async def resolve_path(session: AsyncSession, lang: str, path: str) -> Resolved:
    segments = [s for s in path.strip("/").lower().split("/") if s]
    if not segments:
        return Resolved(type="not_found")

    section, redirect = await _section(session, lang, segments[0])
    if section is None:
        return Resolved(type="not_found")
    rest = segments[1:]

    # ---- L4: /{section}/{offer word}/{slug}-{id}
    if len(rest) == 2 and offer_word_lang(rest[0]):
        return await _resolve_listing(session, lang, section, rest, path)

    if section.kind == "services":
        return await _resolve_services(session, lang, section, rest, redirect, segments)

    location = None
    if rest:
        location, moved = await _location(session, rest[-1])
        if location:
            rest = rest[:-1]
            redirect = redirect or moved

    feature = None
    if rest and (found := feature_by_slug(rest[-1])):
        feature, feature_lang = found
        rest = rest[:-1]
        redirect = redirect or feature_lang != lang

    sector = profession = None
    if len(rest) > 2:
        return Resolved(type="not_found")
    for slug in rest:
        category, moved = await _category(session, section, lang, slug)
        if category is None:
            return Resolved(type="not_found")
        redirect = redirect or moved
        if category.parent_id is None:
            if sector or profession:
                return Resolved(type="not_found")
            sector = category
        else:
            if profession:
                return Resolved(type="not_found")
            profession = category
    if profession:
        parent = await session.get(Category, profession.parent_id)
        if sector is None or sector.id != parent.id:  # a profession without (or with a wrong) sector -> 301
            sector, redirect = parent, True

    resolved = Resolved(
        type="list", section=section, sector=sector, profession=profession, feature=feature, location=location
    )
    canonical = build_list_path(lang, section, sector, profession, feature, location)
    if redirect or canonical != "/".join(segments):
        return Resolved(type="redirect", redirect=canonical)

    resolved.alternates = {
        code: build_list_path(code, section, sector, profession, feature, location) for code in LANGS
    }
    await _seo(session, resolved, lang)
    return resolved


def services_path(lang: str, section: Section, node: Category | None) -> str:
    """Agency services are flat: /{section}, /{section}/{sector}, /{section}/{service}."""
    return "/".join([section.slug[lang], *([node.slug[lang]] if node else [])])


async def _resolve_services(
    session: AsyncSession,
    lang: str,
    section: Section,
    rest: list[str],
    redirect: bool,
    segments: list[str],
) -> Resolved:
    """A section of permanent agency services (documents, training): catalog, sector, service page.
    Always indexed: the pages are content, not listings with thresholds."""
    if len(rest) > 2:
        return Resolved(type="not_found")
    node = None
    for slug in rest:
        category, moved = await _category(session, section, lang, slug)
        if category is None:
            return Resolved(type="not_found")
        redirect = redirect or moved
        node = category
    if len(rest) == 2:
        # /{section}/{sector}/{service} of the old list pages -> the flat service page
        sector = await _category(session, section, lang, rest[0])
        if sector[0] is None or node is None or node.parent_id != sector[0].id:
            return Resolved(type="not_found")
        redirect = True

    canonical = services_path(lang, section, node)
    if redirect or canonical != "/".join(segments):
        return Resolved(type="redirect", redirect=canonical)

    parent = await session.get(Category, node.parent_id) if node and node.parent_id else None
    return Resolved(
        type="service" if parent else "services",
        section=section,
        sector=parent or node,
        profession=node if parent else None,
        alternates={code: services_path(code, section, node) for code in LANGS},
        indexable=True,
    )


async def _resolve_listing(
    session: AsyncSession, lang: str, section: Section, rest: list[str], path: str
) -> Resolved:
    parsed = parse_listing_tail(rest[1])
    if parsed is None:
        return Resolved(type="not_found")
    listing = await session.scalar(
        select(Listing).where(Listing.id == parsed[1]).options(selectinload(Listing.translations))
    )
    if listing is None or listing.status not in {"active", "expired", "closed"}:
        return Resolved(type="not_found")

    listing_section = (
        section if listing.section_id == section.id else await session.get(Section, listing.section_id)
    )
    by_lang = {t.lang: t for t in listing.translations}
    text = by_lang.get(lang) or by_lang[listing.original_lang]
    canonical = listing_path(
        listing_section.slug[lang], lang, text.slug, listing.id, listing_section.key
    )
    if canonical != path.strip("/").lower():
        return Resolved(type="redirect", redirect=canonical)

    state = "active"
    if listing.status != "active":
        closed_at = listing.closed_at if listing.status == "closed" else listing.expires_at
        state = closed_state(closed_at, datetime.now(UTC))

    # a card is indexed only in the languages it has a text for (spec §2)
    translated = lang in by_lang
    return Resolved(
        type="listing",
        section=listing_section,
        listing=listing,
        listing_state=state,
        indexable=translated and state in {"active", "closed"},
        alternates={
            code: listing_path(
                listing_section.slug[code], code, by_lang[code].slug, listing.id, listing_section.key
            )
            for code in LANGS
            if code in by_lang
        },
    )
