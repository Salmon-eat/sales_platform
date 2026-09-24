"""The candidate's CV as the account page sends and reads it."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.models.resume import MAX_ABOUT
from app.schemas.listing import SalaryPeriod, Schedule

LanguageLevel = Literal["a1", "a2", "b1", "b2", "c1", "native"]
Licence = Literal["b", "c", "ce", "d", "code95", "adr", "forklift", "crane"]
Lang = Literal["es", "en", "uk", "ru"]


class ResumeIn(BaseModel):
    title: str = Field(min_length=3, max_length=120, description="what they do: «Водій категорії CE»")
    about: str = Field("", max_length=MAX_ABOUT)
    city_id: int | None = None
    relocate: bool = False
    experience_years: int | None = Field(None, ge=0, le=60)
    languages: dict[Lang, LanguageLevel] = Field(default_factory=dict)
    licences: list[Licence] = Field(default_factory=list, max_length=8)
    has_car: bool = False
    work_permit: bool = False
    schedule: list[Schedule] = Field(default_factory=list)
    salary_min: int | None = Field(None, ge=0, le=1_000_000)
    salary_period: SalaryPeriod | None = None
    is_public: bool = True

    @field_validator("title", "about")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()

    @field_validator("licences", "schedule")
    @classmethod
    def _unique(cls, value: list[str]) -> list[str]:
        return sorted(set(value))


class ResumeOut(ResumeIn):
    id: int
    city_name: str | None = None
    file_name: str | None = None
    file_size: int | None = None
    updated_at: datetime


class ApplyIn(BaseModel):
    """Applying to a job with the CV already in the account."""

    listing_id: int
    comment: str | None = Field(None, max_length=1000)
    questions: dict[str, str] = Field(default_factory=dict, max_length=10)


class ApplyOut(BaseModel):
    application_id: int
    duplicate: bool = Field(description="already applied to this job in the last day")
    with_file: bool
