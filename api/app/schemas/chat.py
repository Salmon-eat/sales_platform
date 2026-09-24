"""What the two sides of a conversation send and see."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.chat import MAX_MESSAGE


class MessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_MESSAGE)

    @field_validator("text")
    @classmethod
    def _clean(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("empty")
        return cleaned


class StartChatIn(MessageIn):
    listing_id: int


class MessageOut(BaseModel):
    id: int
    mine: bool = Field(description="written by the person reading this")
    text: str
    created_at: datetime
    read_at: datetime | None


class ChatItem(BaseModel):
    """A row in "my messages"."""

    id: int
    listing_id: int
    listing_title: str
    listing_path: str | None
    listing_photo: str | None
    # who is on the other side, from the point of view of the person asking
    other_name: str
    selling: bool = Field(description="true when I am the one who posted the ad")
    last_text: str
    last_at: datetime
    unread: int


class ChatOut(ChatItem):
    messages: list[MessageOut]


class ContactOut(BaseModel):
    """The seller's contacts, handed over only when someone asks for them."""

    name: str | None
    phone: str | None
    whatsapp: str | None
    telegram: str | None
    email: str | None
    can_chat: bool = Field(description="the ad has an owner with an account, so a chat is possible")
