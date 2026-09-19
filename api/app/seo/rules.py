"""Index thresholds and hysteresis (spec §6), without database access."""

from dataclasses import dataclass
from datetime import datetime, timedelta

HYSTERESIS = timedelta(days=14)
CLOSED_NOINDEX_AFTER = timedelta(days=30)
CLOSED_GONE_AFTER = timedelta(days=90)


def tier_of(category_level: str | None, has_location: bool, has_feature: bool) -> str:
    """category_level: None (section), 'sector', 'profession'."""
    base = {None: "L1", "sector": "L2", "profession": "L3"}[category_level]
    return base + ("+feature" if has_feature else "") + ("+loc" if has_location else "")


def threshold_of(category_level: str | None, has_location: bool, has_feature: bool) -> int:
    """Active listings needed to index a page. L1: always; +location: 3; L2/L3: 1; +location: 3.
    A page with a feature segment (with housing) needs 3 as well."""
    if has_location or has_feature:
        return 3
    return 0 if category_level is None else 1


@dataclass(frozen=True)
class IndexState:
    indexable: bool
    below_since: datetime | None


def next_index_state(current: IndexState, count: int, threshold: int, now: datetime) -> IndexState:
    """Above the threshold -> indexable. Below it an indexed page stays indexed for 14 days, so pages don't
    flip in and out of the index when a couple of listings close."""
    if count >= threshold:
        return IndexState(True, None)
    if not current.indexable:
        return IndexState(False, current.below_since)
    if current.below_since is None:
        return IndexState(True, now)
    if now - current.below_since >= HYSTERESIS:
        return IndexState(False, current.below_since)
    return current


def closed_state(closed_at: datetime | None, now: datetime) -> str:
    """A closed/expired card: 200 with a "closed" badge -> noindex after 30 days -> 410 after 90 days."""
    if closed_at is None:
        return "closed"
    age = now - closed_at
    if age >= CLOSED_GONE_AFTER:
        return "gone"
    if age >= CLOSED_NOINDEX_AFTER:
        return "closed_noindex"
    return "closed"
