from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.application import Messenger, normalize_phone
from app.schemas.common import Lang
from app.schemas.listing import ListingCard, LocationBrief


class NamedSlug(BaseModel):
    key: str
    slug: str
    name: str


class PlaceRef(BaseModel):
    slug: str
    level: str
    name: str
    parent_slug: str | None = None
    parent_name: str | None = None


class ResolveOut(BaseModel):
    type: Literal["list", "listing", "services", "service", "redirect", "not_found"] = Field(
        description="services: agency services catalog (sector = the chosen sector, if any); "
        "service: one service page (profession = the service, sector = its sector)"
    )
    redirect: str | None = Field(None, description="target path without the language prefix (301)")
    section: NamedSlug | None = None
    sector: NamedSlug | None = None
    profession: NamedSlug | None = None
    feature: str | None = None
    location: PlaceRef | None = None
    listing_id: int | None = None
    listing_state: Literal["active", "closed", "closed_noindex", "gone"] | None = None
    alternates: dict[str, str] = Field(default_factory=dict, description="lang -> path without prefix")
    tier: str | None = None
    indexable: bool = False
    count: int | None = None
    title_override: str | None = None
    description_override: str | None = None


class AttributeValue(BaseModel):
    key: str
    label: str
    values: list[str]
    group: Literal["tags", "category"] = Field(description="section tags or category-specific attribute")


class ListingPhotoOut(BaseModel):
    """A photo of the ad: the big one and the card-sized copy next to it."""

    path: str
    thumb: str
    width: int
    height: int


class SellerBrief(BaseModel):
    """Who is behind an ad a person posted themselves, and how other buyers rated them."""

    id: int
    name: str
    rating: float | None
    reviews_count: int


class ListingDetail(ListingCard):
    description: str
    photos: list[ListingPhotoOut] = Field(default_factory=list)
    seller: SellerBrief | None = None
    requirements: str | None
    conditions: str | None
    original_lang: str
    translations: list[str]
    schedule: list[str]
    contract: str | None
    salary_monthly_min: int | None
    vacancies: int | None
    start_date: date | None
    duration_months: int | None
    attributes: list[AttributeValue]
    questions: list[dict[str, Any]] = Field(
        default_factory=list,
        description="optional questions to the candidate: key, text, options[value, label]",
    )
    expires_at: datetime | None
    closed_at: datetime | None
    state: Literal["active", "closed", "closed_noindex", "gone"]
    section_slug: str
    section_name: str
    category_path: list[NamedSlug]
    location_detail: LocationBrief | None
    province: PlaceRef | None
    lat: float | None
    lon: float | None
    similar: list[ListingCard]


class SitemapEntry(BaseModel):
    path: str
    lastmod: datetime | None
    alternates: dict[str, str]


class SitemapPage(BaseModel):
    items: list[SitemapEntry]
    page: int
    pages: int


class ContentBlockOut(BaseModel):
    key: str
    lang: str
    title: str
    body: str
    data: dict[str, Any]
    updated_at: datetime


class EmployerRequestIn(BaseModel):
    company: str = Field(min_length=2, max_length=200)
    contact_name: str = Field(min_length=2, max_length=200)
    phone: str = Field(min_length=6, max_length=30)
    email: EmailStr | None = None
    messenger: Messenger = "phone"
    text: str = Field(min_length=10, max_length=3000)
    lang: Lang
    consent: bool
    website: str | None = Field(
        None, max_length=200, description="honeypot: hidden from people, bots fill it"
    )
    captcha: str | None = Field(None, max_length=2048, description="Cloudflare Turnstile token")

    @field_validator("phone")
    @classmethod
    def _phone(cls, value: str) -> str:
        return normalize_phone(value)

    @field_validator("consent")
    @classmethod
    def _consent(cls, value: bool) -> bool:
        if not value:
            raise ValueError("consent is required")
        return value
