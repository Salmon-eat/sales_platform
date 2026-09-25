"""What a firm sends about itself and what the catalogue shows."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.company import MAX_ABOUT, MAX_CATEGORIES
from app.schemas.application import normalize_phone

CompanyStatus = Literal["draft", "pending", "active", "rejected", "hidden"]


class CompanyIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    lang: Literal["es", "en", "uk", "ru"] = "es"
    about: str = Field("", max_length=MAX_ABOUT)
    city_id: int | None = None
    address: str | None = Field(None, max_length=200)
    hours: str | None = Field(None, max_length=200, description="«Пн–Пт 9:00–18:00», free text")
    category_ids: list[int] = Field(default_factory=list, max_length=MAX_CATEGORIES)
    phone: str | None = Field(None, max_length=30)
    whatsapp: str | None = Field(None, max_length=30)
    telegram: str | None = Field(None, max_length=64, pattern=r"^@?[A-Za-z0-9_]{3,64}$")
    email: EmailStr | None = None
    site: str | None = Field(None, max_length=200)

    @field_validator("name", "about", "address", "hours", "site")
    @classmethod
    def _strip(cls, value: str | None) -> str | None:
        return (value or "").strip() or None if value is not None else None

    @field_validator("phone", "whatsapp")
    @classmethod
    def _phone(cls, value: str | None) -> str | None:
        value = (value or "").strip()
        return normalize_phone(value) if value else None

    @field_validator("category_ids")
    @classmethod
    def _unique(cls, value: list[int]) -> list[int]:
        return sorted(set(value))

    @field_validator("site")
    @classmethod
    def _site(cls, value: str | None) -> str | None:
        """A bare domain is what people type; make it a link the browser can follow."""
        if not value:
            return None
        return value if value.startswith(("http://", "https://")) else f"https://{value}"


class CompanyCard(BaseModel):
    """A row in the catalogue."""

    id: int
    slug: str
    name: str
    about: str
    lang: str
    city_name: str | None
    categories: list[str]
    logo: str | None
    is_verified: bool
    rating: float | None
    reviews_count: int
    listings_count: int


class CompanyOut(CompanyCard):
    """The firm's own page."""

    owner_id: int
    address: str | None
    hours: str | None
    site: str | None
    # contacts are handed over on a press, like a seller's phone
    created_at: datetime


class MyCompanyOut(CompanyOut):
    """What the owner sees about their own firm, including what is not public yet."""

    status: CompanyStatus
    reject_reason: str | None
    reject_note: str | None
    category_ids: list[int]
    city_id: int | None
    phone: str | None
    whatsapp: str | None
    telegram: str | None
    email: str | None
    updated_at: datetime


class CompanyContactOut(BaseModel):
    phone: str | None
    whatsapp: str | None
    telegram: str | None
    email: str | None


class CompanyActionIn(BaseModel):
    action: Literal["submit", "hide", "reopen"]


class CompanyRejectIn(BaseModel):
    reason: str = Field(max_length=40)
    note: str | None = Field(None, max_length=500)
