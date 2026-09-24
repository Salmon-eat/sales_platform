"""Buyer and seller talking about one ad.

One conversation per (ad, buyer). The unread counters live on the conversation so the header badge and
the list cost one query, not one per thread.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

MAX_MESSAGE = 2000


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (UniqueConstraint("listing_id", "buyer_id", name="uq_conversations_listing_buyer"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"))
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_message_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    buyer_unread: Mapped[int] = mapped_column(default=0, server_default="0")
    seller_unread: Mapped[int] = mapped_column(default=0, server_default="0")
    buyer_hidden: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    seller_hidden: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    messages: Mapped[list["ConversationMessage"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="ConversationMessage.id"
    )

    def is_seller(self, user_id: int) -> bool:
        return self.seller_id == user_id

    def unread_for(self, user_id: int) -> int:
        return self.seller_unread if self.is_seller(user_id) else self.buyer_unread

    def other_side(self, user_id: int) -> int:
        return self.buyer_id if self.is_seller(user_id) else self.seller_id


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"))
    # null after the person deletes their account: the text stays, the author is gone
    sender_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
