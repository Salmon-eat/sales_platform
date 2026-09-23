from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.application import normalize_phone
from app.schemas.common import Lang


class EmailIn(BaseModel):
    email: EmailStr
    lang: Lang = "es"


class CodeIn(EmailIn):
    code: str = Field(min_length=4, max_length=8, pattern=r"^\d+$")


class GoogleLoginIn(BaseModel):
    credential: str = Field(min_length=20, max_length=4096)
    lang: Lang = "es"


class TelegramLoginIn(BaseModel):
    """Exactly what Telegram's login widget sends, plus the page language."""

    id: int
    first_name: str | None = Field(None, max_length=200)
    last_name: str | None = Field(None, max_length=200)
    username: str | None = Field(None, max_length=64)
    photo_url: str | None = Field(None, max_length=500)
    auth_date: int
    hash: str = Field(min_length=64, max_length=64)
    lang: Lang = "es"


class AccountOut(BaseModel):
    id: int
    email: str | None
    name: str | None
    phone: str | None
    avatar: str | None
    lang: str
    role: str
    created_at: datetime


class AccountSession(BaseModel):
    token: str
    expires_at: datetime
    user: AccountOut


class AccountUpdate(BaseModel):
    name: str | None = Field(None, max_length=200)
    phone: str | None = Field(None, max_length=30)
    lang: Lang | None = None

    @field_validator("name")
    @classmethod
    def _strip(cls, value: str | None) -> str | None:
        return value.strip() if value else value

    @field_validator("phone")
    @classmethod
    def _phone(cls, value: str | None) -> str | None:
        value = (value or "").strip()
        return normalize_phone(value) if value else None


class FavoritesIn(BaseModel):
    ids: list[int] = Field(default_factory=list, max_length=200)
    replace: bool = Field(
        False, description="true: the account keeps exactly these; false: merge with what is saved"
    )
