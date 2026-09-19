import re
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

EventType = Literal[
    "page_view", "page_leave", "listing_view", "apply_open", "apply_sent", "search", "contact_click"
]
Channel = Literal[
    "blogger", "instagram", "tiktok", "facebook", "telegram", "youtube", "google", "partner", "other"
]

_ID = r"^[A-Za-z0-9_-]{8,32}$"
_SLUG = r"^[a-z0-9][a-z0-9-]{1,58}[a-z0-9]$"


class EventIn(BaseModel):
    type: EventType
    path: str = Field("", max_length=300)
    listing_id: int | None = Field(None, ge=1)
    duration_ms: int | None = Field(None, ge=0)
    props: dict[str, Any] = Field(default_factory=dict)

    @field_validator("duration_ms")
    @classmethod
    def _cap(cls, value: int | None) -> int | None:
        # a tab left open overnight is not "time on the site"
        return min(value, 30 * 60 * 1000) if value is not None else None

    @field_validator("props")
    @classmethod
    def _props(cls, value: dict[str, Any]) -> dict[str, Any]:
        out = {}
        for k, v in list(value.items())[:8]:
            if isinstance(v, str):
                out[k[:30]] = v[:120]
            elif isinstance(v, int | float | bool) or v is None:
                out[k[:30]] = v
        return out


class EventsIn(BaseModel):
    visitor: str = Field(pattern=_ID)
    session: str = Field(pattern=_ID)
    lang: Literal["es", "en", "uk", "ru"] | None = None
    source: str = Field("direct", max_length=40)
    campaign: str | None = Field(None, max_length=60)
    mobile: bool | None = Field(None, description="viewport width < 768 px")
    tablet: bool | None = None
    events: list[EventIn] = Field(min_length=1, max_length=20)


class GoOut(BaseModel):
    target: str
    channel: str
    code: str


class TrackedLinkIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    code: str | None = Field(None, max_length=60, description="empty: made from the nickname, e.g. olen27")
    channel: Channel
    target_path: str = Field(max_length=300)
    cost: Decimal | None = Field(None, ge=0, max_digits=10, decimal_places=2)
    notes: str | None = Field(None, max_length=2000)

    @field_validator("target_path")
    @classmethod
    def _path(cls, value: str) -> str:
        value = value.strip()
        # only pages of this site: no scheme, no host, no protocol-relative //evil.example
        if not value.startswith("/") or value.startswith("//") or "\\" in value:
            raise ValueError("link_bad_target")
        return value

    @field_validator("code")
    @classmethod
    def _code(cls, value: str | None) -> str | None:
        value = (value or "").strip().lower()
        if not value:
            return None
        if not re.fullmatch(_SLUG, value):
            raise ValueError("link_code_format")
        return value

    @field_validator("name", "notes")
    @classmethod
    def _strip(cls, value: str | None) -> str | None:
        return value.strip() or None if value else value


class TrackedLinkOut(BaseModel):
    id: int
    code: str
    name: str
    channel: str
    target_path: str
    cost: Decimal | None
    notes: str | None
    is_active: bool = Field(description="false: closed, shown in the history")
    closed_at: datetime | None
    created_at: datetime
    clicks: int = 0
    visitors: int = 0
    applications: int = 0
    last_click_at: datetime | None = None
