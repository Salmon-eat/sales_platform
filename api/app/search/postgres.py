"""SearchBackend on PostgreSQL: FTS (tsvector) + pg_trgm fallback + PostGIS radius + disjunctive facets."""

from datetime import timedelta
from typing import Any

from geoalchemy2 import Geography
from sqlalchemy import ColumnElement, and_, case, cast, func, literal, or_, select, true
from sqlalchemy.dialects.postgresql import ARRAY, TSQUERY
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import Integer, Text

from app.models import Listing, ListingSearch, Location
from app.search.backend import Bucket, FacetResult, Hit, PlaceRef, SearchPage, SearchQuery
from app.search.params import (
    BOOL_KEYS,
    CONTRACTS,
    EXPLICIT_SORTS,
    POSTED_DAYS,
    RADII,
    SCHEDULES,
    Filters,
    Range,
)
from app.search.text import latin_lookalike, meaningful, normalize, one_alphabet, tokens

FUZZY_BELOW = 5  # spec §7: if FTS gives < 5 results, add trigram similarity
# spec says similarity() > 0.3; word_similarity() (substring-aware, fits long texts) needs a higher bar
FUZZY_THRESHOLD = 0.5  # keep in sync with pg_trgm.word_similarity_threshold (migration 0006)
FRESH_DAYS = 14
SALARY_BUCKETS = (1000, 1500, 2000, 2500, 3000)
TOP_PLACES = 20

LS = ListingSearch


def ts_query(q: str) -> ColumnElement[Any]:
    """Every token in spanish/english (stemmed) or simple (exact); the last one also as a prefix."""
    words = meaningful(q)
    query: ColumnElement[Any] | None = None
    for i, word in enumerate(words):
        last = i == len(words) - 1
        variants = [word]
        for alternative in (latin_lookalike(word), one_alphabet(word)):
            if alternative:
                variants.append(alternative)
        alternatives: ColumnElement[Any] | None = None
        for v in variants:
            for expr in (
                func.to_tsquery("simple", v + (":*" if last else ""), type_=TSQUERY),
                func.to_tsquery("spanish", v, type_=TSQUERY),
                func.to_tsquery("english", v, type_=TSQUERY),
            ):
                alternatives = (
                    expr if alternatives is None else alternatives.op("||", return_type=TSQUERY)(expr)
                )
        query = alternatives if query is None else query.op("&&", return_type=TSQUERY)(alternatives)
    return query if query is not None else func.to_tsquery("simple", "", type_=TSQUERY)


def geo_point(place: PlaceRef) -> ColumnElement[Any]:
    return cast(func.ST_SetSRID(func.ST_MakePoint(place.lon, place.lat), 4326), Geography)


def place_condition(place: PlaceRef, radius: int | None) -> ColumnElement[bool]:
    """Local listings of the place (or within the radius) + spain_wide listings (shown after local ones)."""
    if place.level == "municipio":
        if radius and place.lat is not None:
            local = func.ST_DWithin(Listing.geog, geo_point(place), radius * 1000)
        else:
            local = Listing.location_id == place.id
    elif place.level == "provincia":
        local = Listing.location_id.in_(select(Location.id).where(Location.parent_id == place.id))
    else:  # comunidad
        provinces = select(Location.id).where(Location.parent_id == place.id)
        local = Listing.location_id.in_(select(Location.id).where(Location.parent_id.in_(provinces)))
    return or_(local, Listing.location_scope == "spain_wide")


def attr_condition(key: str, value: tuple[str, ...] | bool) -> ColumnElement[bool]:
    if value is True:
        return Listing.attributes.contains({key: True})
    # enum: {"route_scope": "nacional"}; multi_enum: {"trailer_type": ["frigorifico"]}; OR inside a filter
    return or_(
        *(or_(Listing.attributes.contains({key: v}), Listing.attributes.contains({key: [v]})) for v in value)
    )


def range_value(group: str) -> ColumnElement[Any]:
    """What a "from–to" filter compares: the price, or a number attribute out of the JSONB ("a.year")."""
    if group == "price":
        return Listing.price
    return cast(Listing.attributes[group[2:]].astext, Integer)


def range_condition(group: str, bounds: Range) -> ColumnElement[bool]:
    value, (lo, hi) = range_value(group), bounds
    parts = [value.is_not(None)]
    if lo is not None:
        parts.append(value >= lo)
    if hi is not None:
        parts.append(value <= hi)
    return and_(*parts)


def filter_groups(query: SearchQuery, f: Filters) -> dict[str, ColumnElement[bool]]:
    """Applied filters by group; AND between groups, OR inside a multi-value group (spec §5)."""
    groups: dict[str, ColumnElement[bool]] = {}
    if f.salary_min:
        groups["salary_min"] = Listing.salary_monthly_min >= f.salary_min
    for key in BOOL_KEYS:
        if getattr(f, key):
            groups[key] = getattr(Listing, key).is_(True)
    if f.schedule:
        groups["schedule"] = Listing.schedule.op("&&")(cast(list(f.schedule), ARRAY(Text)))
    if f.contract:
        groups["contract"] = Listing.contract.in_(f.contract)
    if f.posted:
        groups["posted"] = Listing.published_at >= func.now() - timedelta(days=POSTED_DAYS[f.posted])
    if query.place:
        groups["place"] = place_condition(query.place, f.radius)
    for key, value in f.attrs.items():
        groups[f"a.{key}"] = attr_condition(key, value)
    for group, bounds in f.ranges.items():
        groups[group] = range_condition(group, bounds)
    return groups


class PostgresSearchBackend:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._fuzzy: dict[int, bool] = {}
        self._fts_total: dict[int, int] = {}

    # ---------------------------------------------------------------- building blocks

    def _base(self, query: SearchQuery, with_category: bool = True) -> list[ColumnElement[bool]]:
        conds: list[ColumnElement[bool]] = [Listing.status == "active"]
        if query.section_id:
            conds.append(Listing.section_id == query.section_id)
        if with_category and query.category_ids:
            conds.append(Listing.category_id.in_(query.category_ids))
        return conds

    async def _text(self, query: SearchQuery) -> list[ColumnElement[bool]]:
        q = query.filters.q
        if not q or not tokens(q):
            return []
        fts = LS.tsv_all.op("@@")(ts_query(q))
        key = id(query)
        if not query.allow_fuzzy:
            # no trigram pass, and no counting query to decide about one
            self._fuzzy[key] = False
            return [fts]
        if key not in self._fuzzy:
            conds = self._base(query) + list(filter_groups(query, query.filters).values()) + [fts]
            found = await self.session.scalar(
                select(func.count()).select_from(Listing).join(LS, LS.listing_id == Listing.id).where(*conds)
            )
            self._fuzzy[key] = (found or 0) < FUZZY_BELOW
            self._fts_total[key] = found or 0
        if self._fuzzy[key]:
            # `trgm_text %> q` == word_similarity(q, trgm_text) > pg_trgm.word_similarity_threshold
            # (FUZZY_THRESHOLD, set for the database in migration 0006); unlike the function it uses the index
            return [or_(fts, LS.trgm_text.op("%>")(" ".join(meaningful(q))))]
        return [fts]

    def _select(self, *columns: Any) -> Any:
        return select(*columns).select_from(Listing).join(LS, LS.listing_id == Listing.id)

    # ---------------------------------------------------------------- SearchBackend

    async def count(self, query: SearchQuery) -> int:
        conds = (
            self._base(query) + await self._text(query) + list(filter_groups(query, query.filters).values())
        )
        return await self.session.scalar(self._select(func.count()).where(*conds)) or 0

    async def search(self, query: SearchQuery) -> SearchPage:
        f = query.filters
        text = await self._text(query)
        conds = self._base(query) + text + list(filter_groups(query, f).values())
        counted = self._fts_total.get(id(query))
        if text and not self._fuzzy[id(query)] and counted is not None:
            total = counted  # the same conditions were just counted
        else:
            total = await self.session.scalar(self._select(func.count()).where(*conds)) or 0

        distance = None
        place = query.place
        if place and place.level == "municipio" and place.lat is not None:
            distance = case(
                (
                    Listing.location_scope == "local",
                    func.ST_Distance(Listing.geog, geo_point(place)) / 1000.0,
                ),
                else_=None,
            )

        order: list[Any] = []
        if place:
            order.append((Listing.location_scope == "spain_wide").asc())  # local first
        sort = f.effective_sort
        if sort not in EXPLICIT_SORTS:
            # paid ads come first, as on other boards (the card carries a "top" mark); a visitor who
            # sorted by salary or price gets exactly that order
            order.append(func.coalesce(Listing.promoted_until > func.now(), False).desc())
        if sort == "relevance" and f.q:
            age_days = func.extract("epoch", func.now() - Listing.published_at) / 86400.0
            rank = (
                func.ts_rank_cd(LS.tsv_all, ts_query(f.q))
                + func.greatest(0, 1 - age_days / FRESH_DAYS) * 0.1
                + case((Listing.is_pinned, 0.2), else_=0)
            )
            if self._fuzzy.get(id(query)):
                # ranking only touches the page candidates, the function form is fine here
                rank = rank + func.word_similarity(" ".join(meaningful(f.q)), LS.trgm_text) * 0.5
            order.append(rank.desc())
            if distance is not None and f.radius:
                order.append(distance.asc())
        elif sort == "salary":
            order.append(Listing.salary_monthly_min.desc().nulls_last())
        elif sort in {"price_asc", "price_desc"}:
            # "free" costs nothing; an ad without a price ("negotiable") goes to the end either way
            price = case((Listing.price_kind == "free", 0), else_=Listing.price)
            order.append(price.asc().nulls_last() if sort == "price_asc" else price.desc().nulls_last())
        else:  # new: pinned first, then newest (spec §7)
            order.append(Listing.is_pinned.desc())
        order += [Listing.published_at.desc(), Listing.id.desc()]

        rows = await self.session.execute(
            self._select(Listing.id, distance if distance is not None else literal(None))
            .where(*conds)
            .order_by(*order)
            .offset((f.page - 1) * query.per_page)
            .limit(query.per_page)
        )
        hits = [Hit(listing_id=i, distance_km=round(d, 1) if d is not None else None) for i, d in rows]
        return SearchPage(
            hits=hits,
            total=total,
            used_fuzzy=self._fuzzy.get(id(query), False),
            own_words=await self._own_words(f.q, [h.listing_id for h in hits]),
        )

    async def _own_words(self, q: str | None, ids: list[int]) -> int:
        """Of the ads on this page, how many carry the typed words themselves?

        "пилосос" is a word of the category "Дім і сад", so it brings back every ad in it. That is the
        right answer when no vacuum is for sale — but the visitor has to be told, or the page looks
        like it found three hundred vacuum cleaners. Only the ids already on the page are looked at,
        by primary key, so this costs nothing.
        """
        if not q or not ids or not meaningful(q):
            return 0
        own = LS.tsv_title.op("||")(LS.tsv_body).op("@@")(ts_query(q))
        found = await self.session.scalar(
            select(func.count()).select_from(LS).where(LS.listing_id.in_(ids), own)
        )
        return found or 0

    async def facets(self, query: SearchQuery) -> FacetResult:
        f = query.filters
        text = await self._text(query)
        applied = filter_groups(query, f)

        def others(group: str) -> list[ColumnElement[bool]]:
            return [c for g, c in applied.items() if g != group]

        def counter(group: str, value_cond: ColumnElement[bool]) -> Any:
            return func.count().filter(and_(true(), *others(group), value_cond))

        columns: list[tuple[str, str, Any]] = []
        if query.rules.jobs:
            for key in BOOL_KEYS:
                columns.append((key, "1", counter(key, getattr(Listing, key).is_(True))))
            for value in SCHEDULES:
                columns.append(("schedule", value, counter("schedule", Listing.schedule.any(value))))
            for value in CONTRACTS:
                columns.append(("contract", value, counter("contract", Listing.contract == value)))
            for amount in SALARY_BUCKETS:
                columns.append(
                    ("salary_min", str(amount), counter("salary_min", Listing.salary_monthly_min >= amount))
                )
        for value, days in POSTED_DAYS.items():
            cond = Listing.published_at >= func.now() - timedelta(days=days)
            columns.append(("posted", value, counter("posted", cond)))
        if query.place and query.place.level == "municipio" and query.place.lat is not None:
            for radius in RADII:
                columns.append(
                    ("radius", str(radius), counter("place", place_condition(query.place, radius)))
                )
        for spec in query.attr_specs.values():
            group = f"a.{spec.key}"
            if spec.type == "bool":
                columns.append((group, "1", counter(group, attr_condition(spec.key, True))))
            elif spec.type in {"enum", "multi_enum"}:
                for option in spec.options:
                    columns.append((group, option, counter(group, attr_condition(spec.key, (option,)))))

        # "from–to" filters: the lowest and highest value the other filters leave, as hints in the inputs
        range_groups = [f"a.{s.key}" for s in query.attr_specs.values() if s.type == "int"]
        if query.rules.price:
            range_groups.insert(0, "price")
        range_columns: list[Any] = []
        for group in range_groups:
            value = range_value(group)
            scope = and_(true(), *others(group))
            range_columns += [func.min(value).filter(scope), func.max(value).filter(scope)]

        # narrow the scanned rows to the place; for a municipality keep the widest radius (radius facet)
        narrow: list[ColumnElement[bool]] = []
        place = query.place
        if place and place.level == "municipio" and place.lat is not None:
            narrow.append(
                or_(
                    func.ST_DWithin(Listing.geog, geo_point(place), max(RADII) * 1000),
                    Listing.location_scope == "spain_wide",
                    Listing.location_id == place.id,
                )
            )
        elif place:
            narrow.append(place_condition(place, None))

        total_col = func.count().filter(and_(true(), *applied.values()))
        row = (
            await self.session.execute(
                self._select(total_col, *(c for _, _, c in columns), *range_columns).where(
                    *self._base(query), *text, *narrow
                )
            )
        ).one()

        groups: dict[str, list[Bucket]] = {}
        counts = row[1 : 1 + len(columns)]
        for (group, value, _), count in zip(columns, counts, strict=True):
            groups.setdefault(group, []).append(Bucket(value, count))
        bounds = row[1 + len(columns) :]
        ranges = {group: (bounds[2 * i], bounds[2 * i + 1]) for i, group in enumerate(range_groups)}

        # tier 1: categories without the category filter, places without the place filter
        category_rows = await self.session.execute(
            self._select(Listing.category_id, func.count())
            .where(*self._base(query, with_category=False), *text, *applied.values())
            .group_by(Listing.category_id)
        )
        place_filters = [c for g, c in applied.items() if g != "place"]
        place_rows = await self.session.execute(
            self._select(Listing.location_id, func.count())
            .where(*self._base(query), *text, *place_filters, Listing.location_scope == "local")
            .group_by(Listing.location_id)
            .order_by(func.count().desc())
            .limit(TOP_PLACES)
        )
        spain_wide = await self.session.scalar(
            self._select(func.count()).where(
                *self._base(query), *text, *place_filters, Listing.location_scope == "spain_wide"
            )
        )
        return FacetResult(
            total=row[0],
            groups=groups,
            categories=[Bucket(str(c), n) for c, n in category_rows],
            places=[Bucket(str(p), n) for p, n in place_rows],
            spain_wide=spain_wide or 0,
            ranges=ranges,
        )
