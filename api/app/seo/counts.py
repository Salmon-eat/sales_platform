"""seo_pages recount (worker: hourly and after publishing/closing listings).

Every combination of section x {-, sector, profession} x {-, feature} x {-, municipio, provincia, comunidad}
that has active listings gets a row per language. Rows that lost all listings keep existing with count 0,
so the hysteresis in rules.next_index_state can take them out of the index after 14 days.
"""

from collections import Counter, defaultdict
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category, Listing, Location, Section
from app.models.pages import SeoPage
from app.seo.paths import FEATURES, LANGS
from app.seo.resolver import seo_path_key
from app.seo.rules import IndexState, next_index_state, threshold_of, tier_of

Key = tuple[str, str | None, str | None, str | None]  # section, category key, feature, location slug


async def recount_seo_pages(session: AsyncSession, now: datetime | None = None) -> dict[str, int]:
    now = now or datetime.now(UTC)
    # agency services are content pages, not listings with thresholds
    sections = {
        s.id: s.key for s in (await session.scalars(select(Section).where(Section.kind == "listings"))).all()
    }
    categories = {c.id: c for c in (await session.scalars(select(Category))).all()}

    rows = (
        await session.execute(
            select(
                Listing.section_id,
                Listing.category_id,
                Listing.location_id,
                Listing.location_scope,
                Listing.housing,
                func.count(),
                func.max(func.greatest(Listing.updated_at, Listing.published_at)),
            )
            .where(Listing.status == "active", Listing.section_id.in_(list(sections)))
            .group_by(
                Listing.section_id,
                Listing.category_id,
                Listing.location_id,
                Listing.location_scope,
                Listing.housing,
            )
        )
    ).all()

    municipio_ids = {r[2] for r in rows if r[2]}
    municipios = {
        m.id: m for m in (await session.scalars(select(Location).where(Location.id.in_(municipio_ids)))).all()
    }
    province_ids = {m.parent_id for m in municipios.values() if m.parent_id}
    provinces = {
        p.id: p for p in (await session.scalars(select(Location).where(Location.id.in_(province_ids)))).all()
    }
    community_ids = {p.parent_id for p in provinces.values() if p.parent_id}
    communities = {
        c.id: c for c in (await session.scalars(select(Location).where(Location.id.in_(community_ids)))).all()
    }

    counts: Counter[Key] = Counter()
    last_at: dict[Key, datetime] = {}
    level: dict[str, str] = {}

    for section_id, category_id, location_id, scope, housing, n, updated in rows:
        section = sections[section_id]
        category = categories[category_id]
        category_keys: list[str | None] = [None, category.slug["es"]]
        level[category.slug["es"]] = "profession" if category.parent_id else "sector"
        if category.parent_id:
            parent = categories[category.parent_id]
            category_keys.append(parent.slug["es"])
            level[parent.slug["es"]] = "sector"
        features: list[str | None] = [None] + (["housing"] if housing else [])

        places: list[str | None] = [None]
        if scope == "local" and location_id in municipios:
            m = municipios[location_id]
            places.append(m.slug)
            if (p := provinces.get(m.parent_id)) is not None:
                places.append(p.slug)
                if (c := communities.get(p.parent_id)) is not None:
                    places.append(c.slug)

        for cat in category_keys:
            for feature in features:
                for place in places:
                    key = (section, cat, feature, place)
                    counts[key] += n
                    if updated and (key not in last_at or updated > last_at[key]):
                        last_at[key] = updated

    existing = {p.path_key: p for p in (await session.scalars(select(SeoPage))).all()}
    values: list[dict[str, Any]] = []
    seen: set[str] = set()
    stats = defaultdict(int)

    def row_for(lang: str, key: Key, count: int, current: SeoPage | None) -> dict[str, Any]:
        section, cat, feature, place = key
        cat_level = level.get(cat) if cat else None
        threshold = threshold_of(cat_level, place is not None, feature is not None)
        state = next_index_state(
            IndexState(current.indexable, current.below_since) if current else IndexState(False, None),
            count,
            threshold,
            now,
        )
        stats["indexable" if state.indexable else "noindex"] += 1
        return {
            "path_key": seo_path_key(lang, section, cat, feature, place),
            "lang": lang,
            "section_key": section,
            "category_key": cat,
            "feature": feature,
            "location_slug": place,
            "tier": tier_of(cat_level, place is not None, feature is not None),
            "active_count": count,
            "threshold": threshold,
            "indexable": state.indexable,
            "below_since": state.below_since,
            "last_listing_at": last_at.get(key) or (current.last_listing_at if current else None),
            "recounted_at": now,
        }

    for key, count in counts.items():
        for lang in LANGS:
            path_key = seo_path_key(lang, *key)
            seen.add(path_key)
            values.append(row_for(lang, key, count, existing.get(path_key)))

    # pages that lost all their listings: count 0, hysteresis decides when they leave the index
    for path_key, page in existing.items():
        if path_key not in seen:
            key = (page.section_key, page.category_key, page.feature, page.location_slug)
            if page.category_key:
                level.setdefault(page.category_key, "profession" if page.tier.startswith("L3") else "sector")
            values.append(row_for(page.lang, key, 0, page))

    stmt = insert(SeoPage)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_seo_pages_path_key",
        set_={
            c: getattr(stmt.excluded, c)
            for c in (
                "tier",
                "active_count",
                "threshold",
                "indexable",
                "below_since",
                "last_listing_at",
                "recounted_at",
            )
        },
    )
    for start in range(0, len(values), 2000):
        await session.execute(stmt, values[start : start + 2000])
    await session.commit()
    stats["pages"] = len(values)
    return dict(stats)


_ = FEATURES
