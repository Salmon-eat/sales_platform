import pytest
from pydantic import ValidationError

from app.schemas.application import ApplicationIn

BASE = {"name": "Taras", "lang": "uk", "consent": True}


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("612 345 678", "+34612345678"),  # Spanish mobile without a country code
        ("+380 67 123 45 67", "+380671234567"),
        ("0034 612-345-678", "+34612345678"),
    ],
)
def test_phone_is_normalized_to_e164(raw: str, expected: str) -> None:
    assert ApplicationIn(**BASE, phone=raw).phone == expected


def test_invalid_phone_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ApplicationIn(**BASE, phone="123456")


def test_consent_is_required() -> None:
    with pytest.raises(ValidationError):
        ApplicationIn(**{**BASE, "consent": False}, phone="+34612345678")


def test_only_utm_keys_are_kept() -> None:
    data = ApplicationIn(**BASE, phone="+34612345678", utm={"utm_source": "tg", "gclid": "x"})
    assert data.utm == {"utm_source": "tg"}
