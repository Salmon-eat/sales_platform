"""What a visitor sends and sees about their own ads.

Deliberately smaller than the admin's form: a person posting a sofa chooses a category, a town, a price
and writes a title and a text in their own language. Everything about hiring (contracts, schedules,
salary ranges) belongs to the jobs form, not here.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.common import Lang
from app.schemas.listing import ContactIn, ListingStatus, PriceKind, SalaryPeriod

MyAction = Literal["submit", "close", "reopen", "extend"]


class MyListingIn(BaseModel):
    category_id: int
    location_id: int = Field(description="the town the thing is in")
    lang: Lang = Field(description="the language the person writes in; the text is not translated")
    title: str = Field(min_length=5, max_length=120)
    description: str = Field(min_length=20, max_length=5_000)
    price: int | None = Field(None, ge=0, le=100_000_000)
    price_period: SalaryPeriod | None = Field(None, description="null = one price, month = rent…")
    price_kind: PriceKind = "fixed"
    attributes: dict[str, Any] = Field(default_factory=dict)
    contact: ContactIn = Field(default_factory=ContactIn)

    @field_validator("title", "description")
    @classmethod
    def _strip(cls, value: str) -> str:
        cleaned = " ".join(value.split()) if "\n" not in value else value.strip()
        if not cleaned:
            raise ValueError("empty")
        return cleaned

    @model_validator(mode="after")
    def _price(self) -> "MyListingIn":
        if self.price_kind == "free":
            self.price, self.price_period = None, None
        elif self.price is None and self.price_kind != "negotiable":
            self.price_period = None
        return self


class PhotoOut(BaseModel):
    id: int
    path: str
    thumb: str
    width: int
    height: int


class MyListingItem(BaseModel):
    """A row in "my ads"."""

    id: int
    status: ListingStatus
    title: str
    lang: str
    path: str | None = Field(None, description="address on the site; only once it is published")
    photo: str | None
    price: int | None
    price_period: SalaryPeriod | None
    price_kind: PriceKind
    category_name: str
    location_name: str | None
    published_at: datetime | None
    expires_at: datetime | None
    reject_reason: str | None
    reject_note: str | None
    photos_count: int
    updated_at: datetime


class MyListingOut(MyListingItem):
    """Everything needed to open the ad in the form again."""

    category_id: int
    location_id: int | None
    description: str
    attributes: dict[str, Any]
    contact: dict[str, Any]
    photos: list[PhotoOut]


class MyActionIn(BaseModel):
    action: MyAction
