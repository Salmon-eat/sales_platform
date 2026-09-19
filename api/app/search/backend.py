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


@dataclass
class Hit:
    listing_id: int
    distance_km: float | None = None


@dataclass
class SearchPage:
    hits: list[Hit]
    total: int
    used_fuzzy: bool = False  # FTS found < 5, trigram similarity was added


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


class SearchBackend(Protocol):
    async def search(self, query: SearchQuery) -> SearchPage: ...

    async def facets(self, query: SearchQuery) -> FacetResult: ...

    async def count(self, query: SearchQuery) -> int: ...
