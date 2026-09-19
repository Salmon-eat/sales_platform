from pydantic import BaseModel, Field

from app.schemas.listing import ListingCard


class FacetValue(BaseModel):
    value: str
    count: int
    label: str | None = None


class FacetGroup(BaseModel):
    key: str = Field(description="query key: housing, schedule, a.trailer_type, radius, ...")
    tier: int = Field(description="2 = common filters, 3 = attributes of the selected category")
    label: str | None = None
    type: str = Field(description="bool | multi | single")
    values: list[FacetValue]


class CategoryFacet(BaseModel):
    id: int
    slug: str
    key: str
    name: str
    count: int
    selected: bool


class PlaceFacet(BaseModel):
    slug: str
    name: str
    count: int
    selected: bool


class SelectedCategory(BaseModel):
    id: int
    key: str
    slug: str
    slugs: dict[str, str]
    name: str
    parent: "SelectedCategory | None" = None


class SelectedPlace(BaseModel):
    slug: str
    level: str
    name: str
    parent_slug: str | None = None
    parent_name: str | None = None


class Relaxation(BaseModel):
    kind: str = Field(description="attributes | radius | province | spain")
    count: int
    query: str = Field(description="canonical query string to apply")
    location: str | None = Field(None, description="location slug to apply (None = keep / remove)")
    label_value: str | None = None


class Understood(BaseModel):
    category: SelectedCategory | None
    location: SelectedPlace | None
    rest_q: str
    complete: bool


class ListingCardWithDistance(ListingCard):
    distance_km: float | None = None


class SearchResponse(BaseModel):
    items: list[ListingCardWithDistance]
    total: int
    page: int
    per_page: int
    pages: int
    canonical_query: str
    sort: str
    category: SelectedCategory | None
    location: SelectedPlace | None
    categories: list[CategoryFacet]
    places: list[PlaceFacet]
    spain_wide: int
    facets: list[FacetGroup]
    understood: Understood | None = None
    relaxations: list[Relaxation] = Field(default_factory=list)
    fuzzy: bool = False


class SuggestProfession(BaseModel):
    slug: str
    key: str
    section_key: str
    name: str
    count: int


class SuggestPlace(BaseModel):
    slug: str
    level: str
    name: str
    parent_name: str | None
    count: int


class SuggestCombo(BaseModel):
    category: SuggestProfession
    place: SuggestPlace
    count: int


class SuggestResponse(BaseModel):
    professions: list[SuggestProfession]
    places: list[SuggestPlace]
    combos: list[SuggestCombo]
