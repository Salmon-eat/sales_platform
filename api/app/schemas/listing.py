from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.schemas.application import normalize_phone
from app.schemas.common import Lang

ListingStatus = Literal["draft", "pending", "active", "paused", "expired", "closed", "rejected"]
SalaryPeriod = Literal["hour", "day", "week", "month"]
Schedule = Literal["full", "part", "weekends", "shifts"]
Contract = Literal["indefinido", "temporal", "fijo_discontinuo"]
Source = Literal["agency", "partner", "employer", "private"]
PriceKind = Literal["fixed", "negotiable", "free", "from"]
LocationScope = Literal["local", "spain_wide"]
ListingAction = Literal["publish", "pause", "resume", "close", "extend"]


class TranslationIn(BaseModel):
    lang: Lang
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=10_000)
    requirements: str | None = Field(None, max_length=5_000)
    conditions: str | None = Field(None, max_length=5_000)

    @field_validator("title", "description", "requirements", "conditions")
    @classmethod
    def _strip(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class ContactIn(BaseModel):
    name: str | None = Field(None, max_length=200)
    phone: str | None = None
    whatsapp: str | None = None
    telegram: str | None = Field(None, max_length=64, pattern=r"^@?[A-Za-z0-9_]{3,64}$")
    email: EmailStr | None = None

    @field_validator("phone", "whatsapp")
    @classmethod
    def _phone(cls, value: str | None) -> str | None:
        return normalize_phone(value) if value else None


class QuestionIn(BaseModel):
    """A ready-made question by key, or an own yes/no question (custom1/2) with its text per language."""

    key: str = Field(max_length=20)
    text: dict[str, str] | None = Field(None, description="own question: lang -> text")


class PointIn(BaseModel):
    lat: float = Field(ge=27, le=44)  # Spain incl. Canary Islands
    lon: float = Field(ge=-19, le=5)


class ListingIn(BaseModel):
    category_id: int
    location_scope: LocationScope = "local"
    location_id: int | None = Field(None, description="municipality or locality (village) id")
    point: PointIn | None = Field(None, description="own point, e.g. a warehouse; default: the location")
    salary_min: int | None = Field(None, ge=0, le=1_000_000)
    salary_max: int | None = Field(None, ge=0, le=1_000_000)
    salary_period: SalaryPeriod | None = None
    # outside the jobs section: what the thing costs
    price: int | None = Field(None, ge=0, le=100_000_000)
    price_period: SalaryPeriod | None = Field(None, description="null = one-off; month for rent, etc.")
    price_kind: PriceKind = "fixed"
    housing: bool = False
    no_language: bool = False
    no_experience: bool = False
    schedule: list[Schedule] = Field(default_factory=list)
    contract: Contract | None = None
    vacancies: int | None = Field(None, ge=1, le=999, description="number of places")
    start_date: date | None = None
    is_urgent: bool = False
    duration_months: int | None = Field(None, ge=1, le=36, description="for seasonal/temporary work")
    attributes: dict[str, Any] = Field(default_factory=dict)
    contact: ContactIn = Field(default_factory=ContactIn)
    questions: list[QuestionIn] = Field(
        default_factory=list, max_length=6, description="optional, to the candidate"
    )
    source: Source = "agency"
    employer_name: str | None = Field(None, max_length=200)
    is_pinned: bool = False
    expires_at: datetime | None = None
    translations: list[TranslationIn] = Field(min_length=1, max_length=4)

    @model_validator(mode="after")
    def _consistency(self) -> "ListingIn":
        langs = [t.lang for t in self.translations]
        if len(set(langs)) != len(langs):
            raise ValueError("duplicate_language")
        if self.location_scope == "local" and self.location_id is None:
            raise ValueError("location_required")
        if self.location_scope == "spain_wide":
            self.location_id = None
        has_salary = self.salary_min is not None or self.salary_max is not None
        if has_salary and self.salary_period is None:
            raise ValueError("salary_period_required")
        if not has_salary:
            self.salary_period = None
        if self.salary_min is not None and self.salary_max is not None and self.salary_max < self.salary_min:
            raise ValueError("salary_range")
        if self.source != "agency" and not self.employer_name:
            raise ValueError("employer_required")
        if self.price_kind == "free":
            self.price, self.price_period = None, None
        elif self.price is None and self.price_kind != "negotiable":
            self.price_period = None
        self.schedule = sorted(set(self.schedule))
        return self


class ListingActionIn(BaseModel):
    action: ListingAction
    days: int = Field(30, ge=1, le=180)


# ---------------------------------------------------------------------------- admin output


class TranslationOut(BaseModel):
    lang: str
    title: str
    description: str
    requirements: str | None
    conditions: str | None
    slug: str
    is_machine: bool


class LocationBrief(BaseModel):
    id: int
    level: str
    slug: str
    name: str
    parent_name: str | None = None


class AdminListingItem(BaseModel):
    id: int
    status: ListingStatus
    title: str
    langs: list[str]
    original_lang: str
    category_name: str
    sector_name: str | None
    location: LocationBrief | None
    location_scope: LocationScope
    salary_min: int | None
    salary_max: int | None
    salary_period: SalaryPeriod | None
    is_pinned: bool
    published_at: datetime | None
    expires_at: datetime | None
    created_by_email: str | None
    updated_at: datetime
    can_edit: bool


class AdminListingDetail(BaseModel):
    id: int
    status: ListingStatus
    section_id: int
    category_id: int
    location_scope: LocationScope
    location: LocationBrief | None
    point: PointIn | None
    original_lang: str
    salary_min: int | None
    salary_max: int | None
    salary_period: SalaryPeriod | None
    salary_monthly_min: int | None
    price: int | None = None
    price_period: SalaryPeriod | None = None
    price_kind: PriceKind = "fixed"
    housing: bool
    no_language: bool
    no_experience: bool
    schedule: list[str]
    contract: Contract | None
    vacancies: int | None
    start_date: date | None
    is_urgent: bool
    duration_months: int | None
    attributes: dict[str, Any]
    contact: dict[str, Any]
    questions: list[dict[str, Any]] = Field(default_factory=list)
    source: Source
    employer_name: str | None
    is_pinned: bool
    published_at: datetime | None
    expires_at: datetime | None
    closed_at: datetime | None
    created_by_email: str | None
    created_at: datetime
    updated_at: datetime
    translations: list[TranslationOut]
    can_edit: bool


# ---------------------------------------------------------------------------- public output


class ListingCategoryRef(BaseModel):
    key: str = Field(description="stable key = Spanish slug")
    slug: str
    name: str
    icon: str | None


class CardTag(BaseModel):
    """A short feature shown on the card, already in the page language (from the attribute dictionary)."""

    key: str
    label: str
    kind: Literal["lang", "doc", "ok", "perk", "info"] = Field(
        description="colour group: languages, documents, official/good, employer perks, other"
    )


class ListingCard(BaseModel):
    id: int
    slug: str
    path: str = Field(
        description="card URL path without the language prefix: {section}/{offer word}/{slug}-{id}"
    )
    lang: str = Field(description="language of the text shown (the original if no translation)")
    is_translated: bool
    title: str
    section_key: str
    category: ListingCategoryRef
    sector: ListingCategoryRef | None
    location: LocationBrief | None
    location_scope: LocationScope
    salary_min: int | None
    salary_max: int | None
    salary_period: SalaryPeriod | None
    # everything outside the jobs section: the price people see first on the card
    price: int | None = None
    price_period: SalaryPeriod | None = Field(None, description="null = one-off, else per month/day/hour")
    price_kind: PriceKind = "fixed"
    photo: str | None = Field(None, description="path of the first photo, e.g. /media/2026/09/ab12.jpg")
    promoted: bool = Field(False, description="paid placement: shown in the top block")
    housing: bool
    no_language: bool
    no_experience: bool
    source: Source
    employer_name: str | None = Field(description="null for agency listings")
    is_urgent: bool
    is_pinned: bool
    published_at: datetime | None
    schedule: list[str] = Field(default_factory=list)
    contract: str | None = None
    vacancies: int | None = None
    tags: list[CardTag] = Field(default_factory=list, description="features from the listing's attributes")


class ListingStats(BaseModel):
    total: int
    today: int
