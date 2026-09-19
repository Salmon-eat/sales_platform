from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.schemas.listing import ListingIn
from app.services.listing_rules import (
    AttributeSpec,
    TransitionError,
    apply_action,
    listing_slug,
    monthly_min,
    validate_attributes,
)

NOW = datetime(2026, 9, 17, 12, tzinfo=UTC)

CE_SPECS = [
    AttributeSpec("trailer_type", "multi_enum", ("lona", "frigorifico", "portacoches", "cisterna"), False),
    AttributeSpec("adr", "bool", (), False),
    AttributeSpec("route_scope", "enum", ("nacional", "internacional"), True),
    AttributeSpec("km", "int_range", (), False),
]


@pytest.mark.parametrize(
    ("salary_min", "salary_max", "period", "expected"),
    [
        (16, 18, "hour", 2560),  # × 160
        (90, None, "day", 1953),  # × 21.7
        (400, None, "week", 1732),  # × 4.33
        (None, 2000, "month", 2000),  # only max given
        (None, None, None, None),
    ],
)
def test_monthly_salary_normalization(salary_min, salary_max, period, expected) -> None:  # noqa: ANN001
    assert monthly_min(salary_min, salary_max, period) == expected


def test_attributes_are_cleaned() -> None:
    clean, errors = validate_attributes(
        CE_SPECS,
        {
            "trailer_type": ["cisterna", "lona", "lona"],
            "adr": False,
            "route_scope": "nacional",
            "km": {"min": 5},
        },
    )
    assert errors == []
    assert clean == {"trailer_type": ["lona", "cisterna"], "route_scope": "nacional", "km": {"min": 5}}


def test_attribute_errors() -> None:
    _, errors = validate_attributes(
        CE_SPECS,
        {"trailer_type": ["boat"], "adr": "yes", "housing_pets": True, "km": {"min": 10, "max": 1}},
    )
    joined = " | ".join(errors)
    assert "housing_pets" in joined  # unknown key
    assert "route_scope" in joined  # required
    assert "trailer_type" in joined and "adr" in joined and "km" in joined
    assert len(errors) == 5


def test_status_flow() -> None:
    published = apply_action(
        "publish", status="draft", published_at=None, expires_at=None, closed_at=None, now=NOW
    )
    assert published.status == "active"
    assert published.published_at == NOW
    assert published.expires_at == NOW + timedelta(days=30)

    paused = apply_action("pause", status="active", published_at=NOW, expires_at=NOW, closed_at=None, now=NOW)
    assert paused.status == "paused"

    extended = apply_action(
        "extend",
        status="expired",
        published_at=NOW,
        expires_at=NOW - timedelta(days=1),
        closed_at=None,
        now=NOW,
    )
    assert extended.status == "active"
    assert extended.expires_at == NOW + timedelta(days=30)

    closed = apply_action(
        "close", status="active", published_at=NOW, expires_at=None, closed_at=None, now=NOW
    )
    assert closed.status == "closed" and closed.closed_at == NOW


def test_extend_adds_to_a_future_expiry() -> None:
    later = NOW + timedelta(days=5)
    change = apply_action(
        "extend", status="active", published_at=NOW, expires_at=later, closed_at=None, now=NOW, days=10
    )
    assert change.expires_at == later + timedelta(days=10)


@pytest.mark.parametrize(
    ("action", "status"),
    [
        ("publish", "active"),
        ("pause", "draft"),
        ("resume", "active"),
        ("close", "draft"),
        ("extend", "closed"),
    ],
)
def test_invalid_transitions(action: str, status: str) -> None:
    with pytest.raises(TransitionError):
        apply_action(action, status=status, published_at=None, expires_at=None, closed_at=None, now=NOW)


def test_resume_after_expiry_requires_extend() -> None:
    with pytest.raises(TransitionError):
        apply_action(
            "resume",
            status="paused",
            published_at=NOW,
            expires_at=NOW - timedelta(hours=1),
            closed_at=None,
            now=NOW,
        )


def test_slug() -> None:
    assert listing_slug("Conductor CE, frigorífico", "es", "madrid") == "conductor-ce-frigorifico-madrid"
    assert listing_slug("Водій CE", "uk", None) == "vodii-ce-vsia-ispaniia"


BASE = {"category_id": 1, "location_id": 5, "translations": [
    {"lang": "uk", "title": "Водій CE", "description": "Опис вакансії достатньої довжини"}
]}  # fmt: skip


def test_listing_in_one_text_per_language() -> None:
    with pytest.raises(ValidationError, match="duplicate_language"):
        ListingIn(**{**BASE, "translations": BASE["translations"] * 2})


def test_listing_in_salary_needs_period() -> None:
    with pytest.raises(ValidationError, match="salary_period_required"):
        ListingIn(**BASE, salary_min=1500)


def test_listing_in_spain_wide_drops_location() -> None:
    data = ListingIn(**{**BASE, "location_scope": "spain_wide"})
    assert data.location_id is None


def test_listing_in_partner_needs_company() -> None:
    with pytest.raises(ValidationError, match="employer_required"):
        ListingIn(**BASE, source="partner")
