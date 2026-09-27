"""SearchBackend contract. The API and pages depend only on this module, so the Postgres implementation
can be replaced by Meilisearch (spec §1: after ~50k active listings or facets p95 > 300 ms)."""

from dataclasses import dataclass, field
from typing import Protocol

from app.search.params import AttrSpec, Filters


@dataclass(frozen=True)
class PlaceRef:
    id: int
    level: str  # municipio | provincia | comunidad
    slug: str
    lat: float | None = None
    lon: float | None = None
    parent_id: int | None = None


@dataclass
class SearchQuery:
    lang: str
    section_id: int | None
    category_ids: tuple[int, ...]  # the chosen category + its children
    place: PlaceRef | None
    filters: Filters
    attr_specs: dict[str, AttrSpec] = field(default_factory=dict)
    per_page: int = 20
    # a "price from–to" filter in the facets: everywhere except the jobs, which have a salary instead
    price_filter: bool = False
    # Matching words that merely resemble the ones in the ads means reading every ad, which costs real
    # time once there are thousands. The caller turns it off for the first attempt and only pays for it
    # when the plain search and the spelling repair have both come back nearly empty.
    allow_fuzzy: bool = True


@dataclass
class Hit:
    listing_id: int
    distance_km: float | None = None


@dataclass
class SearchPage:
    hits: list[Hit]
    total: int
    used_fuzzy: bool = False  # FTS found < 5, trigram similarity was added
    # of the ads on this page, how many contain the typed words themselves rather than matching only
    # through the words of their category ("пилосос" -> every ad in "Дім і сад")
    own_words: int = 0


@dataclass
class Bucket:
    value: str
    count: int


@dataclass
class FacetResult:
    total: int
    groups: dict[str, list[Bucket]]  # tier 2/3: "housing", "schedule", "a.trailer_type", "radius", ...
    categories: list[Bucket]  # category id -> count (tier 1, without the category filter)
    places: list[Bucket]  # municipality id -> count (tier 1, without the location filter)
    spain_wide: int = 0
    # "from–to" filters ("price", "a.year"): the lowest and highest value the other filters leave
    ranges: dict[str, tuple[int | None, int | None]] = field(default_factory=dict)


class SearchBackend(Protocol):
    async def search(self, query: SearchQuery) -> SearchPage: ...

    async def facets(self, query: SearchQuery) -> FacetResult: ...

    async def count(self, query: SearchQuery) -> int: ...
