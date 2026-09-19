from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models import UserRole


class GoogleLoginIn(BaseModel):
    credential: str = Field(min_length=20, max_length=5000, description="ID token from Google Sign-In")


class DevLoginIn(BaseModel):
    email: EmailStr


class UserOut(BaseModel):
    id: int
    email: str | None
    name: str | None
    avatar: str | None
    lang: str
    role: UserRole


class SessionOut(BaseModel):
    token: str = Field(description="goes into an httpOnly cookie; send it back as `Authorization: Bearer`")
    expires_at: datetime
    user: UserOut


class AuthConfig(BaseModel):
    google_client_id: str | None
    dev_login: bool
