import pytest
from pydantic import ValidationError

from app.schemas.application import ApplicationIn

BASE = {"name": "Olena", "lang": "uk", "consent": True}


def test_chat_message_may_come_without_a_phone():
    data = ApplicationIn(**BASE, channel="chat", comment="Hello")
    assert data.phone is None


def test_form_request_needs_a_phone():
    with pytest.raises(ValidationError, match="phone is required"):
        ApplicationIn(**BASE)


def test_chat_needs_a_message():
    with pytest.raises(ValidationError, match="message is required"):
        ApplicationIn(**BASE, channel="chat")


def test_phone_is_normalised_when_given_in_chat():
    data = ApplicationIn(**BASE, channel="chat", comment="Hi", phone="612 345 678")
    assert data.phone == "+34612345678"
