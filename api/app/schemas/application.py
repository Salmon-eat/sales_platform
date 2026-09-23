from datetime import datetime
from typing import Literal

import phonenumbers
from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.common import Lang

Messenger = Literal["phone", "telegram", "whatsapp", "viber"]
ApplicationStatus = Literal["new", "in_progress", "done", "rejected"]


def normalize_phone(value: str) -> str:
    """Any common format -> E.164. Numbers without a country code are treated as Spanish."""
    try:
        number = phonenumbers.parse(value, "ES")
    except phonenumbers.NumberParseException as exc:
        raise ValueError("invalid phone number") from exc
    if not phonenumbers.is_valid_number(number):
        raise ValueError("invalid phone number")
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)


class ApplicationIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    phone: str | None = Field(None, max_length=30, description="required except for a site chat message")
    messenger: Messenger = "phone"
    lang: Lang
    category_id: int | None = None
    location_slug: str | None = Field(None, max_length=120, pattern=r"^[a-z0-9-]+$")
    listing_id: int | None = None
    in_spain: bool | None = None
    comment: str | None = Field(None, max_length=1000)
    consent: bool
    utm: dict[str, str] = Field(default_factory=dict)
    channel: Literal["form", "chat"] = Field("form", description="chat: a message from the site chat window")
    questions: dict[str, str] = Field(
        default_factory=dict,
        max_length=10,
        description="answers to the listing's optional questions: key -> value",
    )
    website: str | None = Field(
        None, max_length=200, description="honeypot: hidden from people, bots fill it"
    )
    captcha: str | None = Field(None, max_length=2048, description="Cloudflare Turnstile token")

    @field_validator("name", "comment")
    @classmethod
    def _strip(cls, value: str | None) -> str | None:
        return value.strip() if value else value

    @field_validator("phone")
    @classmethod
    def _phone(cls, value: str | None) -> str | None:
        value = (value or "").strip()
        return normalize_phone(value) if value else None

    @model_validator(mode="after")
    def _contact(self) -> "ApplicationIn":
        # the chat can answer in the window; a form request needs a number to call back
        if self.phone is None and self.channel != "chat":
            raise ValueError("phone is required")
        if self.channel == "chat" and not self.comment:
            raise ValueError("message is required")
        return self

    @field_validator("consent")
    @classmethod
    def _consent(cls, value: bool) -> bool:
        if not value:
            raise ValueError("consent is required")
        return value

    @field_validator("utm")
    @classmethod
    def _utm(cls, value: dict[str, str]) -> dict[str, str]:
        return {k[:40]: v[:200] for k, v in value.items() if k.startswith("utm_")}

    @field_validator("questions")
    @classmethod
    def _questions(cls, value: dict[str, str]) -> dict[str, str]:
        return {k[:20]: v[:20] for k, v in value.items() if isinstance(v, str)}


class ApplicationCreated(BaseModel):
    id: int
    duplicate: bool = Field(description="same phone + same listing/category within 24h: a note was added")
    chat_token: str | None = Field(None, description="site chat: the browser keeps it to read the replies")
    cv_token: str | None = Field(None, description="one-time key to attach a CV within an hour (optional)")


class ChatMessageOut(BaseModel):
    id: int
    author: Literal["visitor", "staff"]
    text: str
    created_at: datetime


class AdminChatMessage(BaseModel):
    """A message as the team sees it: the site chat or the Telegram bot conversation."""

    id: int
    author: Literal["visitor", "staff", "note"]
    author_name: str | None = Field(None, description="a manager who wrote in Telegram, or the admin user")
    text: str
    content_type: str | None = Field(None, description="Telegram: text, photo, voice, document...")
    delivery: Literal["pending", "delivered", "failed"] | None = Field(
        None, description="Telegram: did the reply reach the client"
    )
    created_at: datetime


class BotInfo(BaseModel):
    """What the Telegram bot knows about its application."""

    app_id: int
    title: str | None = None
    card: str | None = None
    username: str | None = None
    topic_url: str | None = None
    manager_name: str | None = None
    status: str | None = None


class ChatMessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=1000)

    @field_validator("text")
    @classmethod
    def _strip(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("empty message")
        return value


class AppliedListing(BaseModel):
    id: int
    title: str
    status: str
    location_name: str | None


class AdminApplication(BaseModel):
    id: int
    name: str
    phone: str | None
    messenger: Messenger
    status: ApplicationStatus
    lang: str
    source: str
    category_name: str | None
    location_name: str | None
    listing: AppliedListing | None = Field(None, description="the job the candidate responded to")
    in_spain: bool | None
    comment: str | None
    notes_count: int
    created_at: datetime
    updated_at: datetime
    stale: bool = Field(False, description="new/in progress without changes for 48 h")
    unread: int = Field(0, description="site chat / bot messages staff has not read yet")
    has_cv: bool = Field(False, description="the candidate attached a CV")


class ApplicationFileOut(BaseModel):
    id: int
    filename: str
    size: int
    created_at: datetime


class ApplicationNoteOut(BaseModel):
    id: int
    text: str
    created_at: datetime


class AdminApplicationDetail(AdminApplication):
    utm: dict[str, str]
    history: list[AdminApplication] = Field(description="other applications from the same phone")
    notes: list[ApplicationNoteOut]
    messages: list[AdminChatMessage] = Field(
        default_factory=list, description="site chat or Telegram bot conversation"
    )
    bot: BotInfo | None = Field(None, description="an application from the Telegram bot")
    answers: list[dict[str, str]] = Field(
        default_factory=list,
        description="answers to the listing's questions: question, answer (admin language)",
    )
    files: list[ApplicationFileOut] = Field(default_factory=list, description="the candidate's CV")
    consent_at: datetime
    consent_version: str
    anonymized_at: datetime | None = Field(description="personal data erased (GDPR)")
    person_applications: int = Field(1, description="applications of this person (same phone) incl. this one")


class AdminApplicationUpdate(BaseModel):
    status: ApplicationStatus
