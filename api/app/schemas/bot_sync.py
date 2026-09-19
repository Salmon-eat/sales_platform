from typing import Literal

from pydantic import BaseModel, Field


class BotApplicationIn(BaseModel):
    id: int
    client_id: int
    title: str | None = Field(None, max_length=300)
    card: str | None = Field(None, max_length=10000, description="the questionnaire card as plain text")
    name: str = Field(max_length=200)
    phone: str | None = Field(None, max_length=40)
    username: str | None = Field(None, max_length=64)
    lang: str = Field(max_length=10)
    status: str = Field(max_length=20)
    manager_name: str | None = Field(None, max_length=200)
    created_at: str = Field(description="UTC, 2026-09-19T10:00:00")
    updated_at: str


class BotMessageIn(BaseModel):
    id: int
    client_id: int
    app_id: int | None
    direction: Literal["client", "manager", "note"]
    sender_name: str | None = Field(None, max_length=200)
    content_type: str = Field(max_length=40)
    text: str | None = Field(None, max_length=10000)
    delivery: str = Field(max_length=20)
    created_at: str
    site_message_id: int | None = Field(None, description="a reply from the admin, now logged by the bot")


class BotSyncIn(BaseModel):
    applications: list[BotApplicationIn] = Field(default_factory=list, max_length=500)
    messages: list[BotMessageIn] = Field(default_factory=list, max_length=500)
    topics: dict[str, str] = Field(default_factory=dict, description="bot client id -> Telegram topic link")


class BotSyncOut(BaseModel):
    applications: int
    messages: int


class BotOutgoingItem(BaseModel):
    id: int
    kind: Literal["message", "status"]
    app_id: int = Field(description="the application number in the bot")
    message_id: int | None = None
    text: str | None = None
    sender_name: str | None = None
    status: str | None = None
