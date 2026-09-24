"""Rules of a buyer↔seller conversation that do not need a database to hold."""

from datetime import UTC, datetime

from app.models import Conversation, ConversationMessage
from app.services.chat_notify import _short, pending_messages  # noqa: F401  (import guard)


def a_chat(buyer: int = 2, seller: int = 3) -> Conversation:
    return Conversation(id=1, listing_id=10, buyer_id=buyer, seller_id=seller)


def test_each_side_sees_their_own_unread_count() -> None:
    chat = a_chat()
    chat.buyer_unread, chat.seller_unread = 4, 1
    assert chat.unread_for(2) == 4
    assert chat.unread_for(3) == 1


def test_the_other_side_is_whoever_is_not_asking() -> None:
    chat = a_chat()
    assert chat.other_side(2) == 3
    assert chat.other_side(3) == 2
    assert chat.is_seller(3) and not chat.is_seller(2)


def test_a_long_message_is_cut_for_the_letter() -> None:
    assert _short("одне  два\nтри") == "одне два три"
    long = "а" * 200
    assert len(_short(long)) == 120
    assert _short(long).endswith("…")


def test_a_message_starts_unread_and_unannounced() -> None:
    message = ConversationMessage(conversation_id=1, sender_id=2, text="Ще актуально?")
    assert message.read_at is None
    assert message.notified_at is None
    # the timestamp is set by the database, not by us
    assert getattr(message, "created_at", None) is None or isinstance(message.created_at, datetime)
    assert datetime.now(UTC).tzinfo is UTC
