"""Pure listing rules (no database): salary normalization, attribute validation, status machine, slugs."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from app.core.slug import slugify

# spec §5: hour × 160, day × 21.7, week × 4.33
MONTHLY_FACTOR = {"hour": 160, "day": 21.7, "week": 4.33, "month": 1}
DEFAULT_LIFETIME = timedelta(days=30)

SPAIN_WIDE_SLUG = {"es": "toda-espana", "en": "all-spain", "uk": "vsia-ispaniia", "ru": "vsya-ispaniya"}


def monthly_min(salary_min: int | None, salary_max: int | None, period: str | None) -> int | None:
    """Lower bound per month; a listing without salary drops out of `salary_min` filters."""
    base = salary_min if salary_min is not None else salary_max
    if base is None or period is None:
        return None
    return round(base * MONTHLY_FACTOR[period])


# ---------------------------------------------------------------------------- attributes


@dataclass(frozen=True)
class AttributeSpec:
    key: str
    type: str  # bool | enum | multi_enum | int_range | int
    options: tuple[str, ...]
    required: bool


def validate_attributes(
    specs: list[AttributeSpec], values: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    """Returns the cleaned attributes and a list of error codes "code:attribute_key" (the admin UI
    translates them into its language)."""
    by_key = {s.key: s for s in specs}
    errors: list[str] = []
    clean: dict[str, Any] = {}

    for key in values:
        if key not in by_key:
            errors.append(f"attr_foreign:{key}")

    for spec in specs:
        value = values.get(spec.key)
        empty = value is None or value == [] or value == "" or value == {}
        if empty:
            if spec.required:
                errors.append(f"attr_required:{spec.key}")
            continue

        if spec.type == "bool":
            if not isinstance(value, bool):
                errors.append(f"attr_bool:{spec.key}")
                continue
            if value:  # false == not set; keeps the JSONB small and filters simple
                clean[spec.key] = True
        elif spec.type == "enum":
            if value not in spec.options:
                errors.append(f"attr_value:{spec.key}")
                continue
            clean[spec.key] = value
        elif spec.type == "multi_enum":
            if not isinstance(value, list) or any(v not in spec.options for v in value):
                errors.append(f"attr_value:{spec.key}")
                continue
            clean[spec.key] = sorted(set(value), key=spec.options.index)
        elif spec.type == "int_range":
            lo, hi = (value.get("min"), value.get("max")) if isinstance(value, dict) else (None, None)
            if not all(v is None or (isinstance(v, int) and not isinstance(v, bool)) for v in (lo, hi)):
                errors.append(f"attr_range:{spec.key}")
                continue
            if lo is not None and hi is not None and hi < lo:
                errors.append(f"attr_range:{spec.key}")
                continue
            clean[spec.key] = {k: v for k, v in (("min", lo), ("max", hi)) if v is not None}
        elif spec.type == "int":
            # a year, kilometres, horsepower: a whole number, never negative
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 100_000_000:
                errors.append(f"attr_number:{spec.key}")
                continue
            clean[spec.key] = value

    return clean, errors


# ---------------------------------------------------------------------------- status machine

ACTIONS = ("publish", "pause", "resume", "close", "extend")


class TransitionError(ValueError):
    pass


@dataclass
class StatusChange:
    status: str
    published_at: datetime | None
    expires_at: datetime | None
    closed_at: datetime | None


def apply_action(
    action: str,
    *,
    status: str,
    published_at: datetime | None,
    expires_at: datetime | None,
    closed_at: datetime | None,
    now: datetime,
    days: int = 30,
) -> StatusChange:
    """draft -> active -> paused <-> active; active -> expired (worker) -> active (extend); -> closed."""
    change = StatusChange(status, published_at, expires_at, closed_at)
    lifetime = timedelta(days=days)

    if action == "publish":
        if status not in {"draft", "pending", "rejected"}:
            raise TransitionError("publish_only_draft")
        change.status = "active"
        change.published_at = published_at or now
        if expires_at is None or expires_at <= now:
            change.expires_at = now + lifetime
    elif action == "pause":
        if status != "active":
            raise TransitionError("pause_only_active")
        change.status = "paused"
    elif action == "resume":
        if status != "paused":
            raise TransitionError("resume_only_paused")
        if expires_at is not None and expires_at <= now:
            raise TransitionError("expired_use_extend")
        change.status = "active"
    elif action == "close":
        if status not in {"active", "paused", "expired"}:
            raise TransitionError("close_only_published")
        change.status = "closed"
        change.closed_at = now
    elif action == "extend":
        if status not in {"active", "expired", "paused"}:
            raise TransitionError("extend_not_allowed")
        start = expires_at if expires_at and expires_at > now else now
        change.expires_at = start + lifetime
        if status == "expired":
            change.status = "active"
    else:
        raise TransitionError("unknown_action")
    return change


# ---------------------------------------------------------------------------- slugs


def listing_slug(title: str, lang: str, location_slug: str | None) -> str:
    """conductor-ce-frigorifico-madrid; the public URL appends -{id}."""
    title_part = slugify(title, lang)[:90].rstrip("-")
    place = location_slug or SPAIN_WIDE_SLUG[lang]
    return f"{title_part}-{place}"[:150].rstrip("-")
