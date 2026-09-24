"""What the person who posted a vacancy sees about the people who answered it."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.application import ApplicationStatus


class CandidateNote(BaseModel):
    text: str
    author: str | None
    created_at: datetime


class CandidateOut(BaseModel):
    id: int
    listing_id: int | None
    listing_title: str
    name: str
    phone: str | None
    status: ApplicationStatus
    lang: str
    comment: str | None
    # the answers to the vacancy's own questions, already in words
    answers: list[dict[str, str]] = Field(default_factory=list)
    has_cv: bool
    # what the candidate says about themselves, when they applied from their account
    headline: str | None = None
    experience_years: int | None = None
    licences: list[str] = Field(default_factory=list)
    languages: dict[str, str] = Field(default_factory=dict)
    notes: list[CandidateNote] = Field(default_factory=list)
    created_at: datetime


class StatusIn(BaseModel):
    status: ApplicationStatus


class NoteIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)

    @field_validator("text")
    @classmethod
    def _clean(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("empty")
        return cleaned
