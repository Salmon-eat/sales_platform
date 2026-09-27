"""Tier 2/3 filters and service params in the query string (spec §5).

The parser drops unknown keys and values and builds a canonical query string: keys sorted, values
sorted, defaults omitted. When the incoming query differs from the canonical one the page answers
with a permanent redirect, so every filter combination has exactly one URL.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from urllib.parse import quote

from app.search.text import normalize

BOOL_KEYS = ("housing", "no_experience", "no_language")
SCHEDULES = ("full", "part", "weekends", "shifts")
CONTRACTS = ("fijo_discontinuo", "indefinido", "temporal")
POSTED_DAYS = {"3d": 3}  # one "new" switch instead of day / week / month
RADII = (10, 25, 50, 100)
SORTS = ("new", "relevance", "salary", "price_asc", "price_desc")
# a visitor who picked one of these asked for exactly that order: no paid ads pushed on top of it
EXPLICIT_SORTS = ("salary", "price_asc", "price_desc")
MAX_PAGE = 100
MAX_Q = 200


@dataclass(frozen=True)
class AttrSpec:
    key: str
    type: str  # bool | enum | multi_enum | int_range
    options: tuple[str, ...]


@dataclass
class Filters:
    q: str | None = None
    salary_min: int | None = None
    housing: bool = False
    no_language: bool = False
    no_experience: bool = False
    schedule: tuple[str, ...] = ()
    contract: tuple[str, ...] = ()
    posted: str | None = None
    radius: int | None = None
    attrs: dict[str, tuple[str, ...] | bool] = field(default_factory=dict)
    sort: str | None = None  # None = default: relevance with q, otherwise new
    page: int = 1

    @property
    def effective_sort(self) -> str:
        return self.sort or ("relevance" if self.q else "new")

    def without(self, *groups: str) -> "Filters":
        """Copy with some filter groups removed (relaxations, disjunctive facets)."""
        copy = Filters(**{**self.__dict__, "attrs": dict(self.attrs)})
        for group in groups:
            if group == "attrs":
                copy.attrs = {}
            elif group.startswith("a."):
                copy.attrs.pop(group[2:], None)
            elif group in BOOL_KEYS:
                setattr(copy, group, False)
            elif group in {"schedule", "contract"}:
                setattr(copy, group, ())
            else:
                setattr(copy, group, None)
        copy.page = 1
        return copy


def _values(raw: str | Iterable[str] | None) -> list[str]:
    if raw is None:
        return []
    items = [raw] if isinstance(raw, str) else list(raw)
    return [v.strip() for item in items for v in item.split(",") if v.strip()]


def parse_filters(
    raw: Mapping[str, str | list[str]],
    attr_specs: Mapping[str, AttrSpec] | None = None,
    radius_allowed: bool = False,
) -> Filters:
    specs = attr_specs or {}
    f = Filters()

    if q := " ".join(" ".join(_values(raw.get("q"))).split())[:MAX_Q].strip():
        f.q = q
    if (vals := _values(raw.get("salary_min"))) and vals[0].isdigit() and 0 < int(vals[0]) <= 100_000:
        f.salary_min = int(vals[0])
    for key in BOOL_KEYS:
        setattr(f, key, "1" in _values(raw.get(key)))
    f.schedule = tuple(sorted({v for v in _values(raw.get("schedule")) if v in SCHEDULES}))
    f.contract = tuple(sorted({v for v in _values(raw.get("contract")) if v in CONTRACTS}))
    if (vals := _values(raw.get("posted"))) and vals[0] in POSTED_DAYS:
        f.posted = vals[0]
    if (
        radius_allowed
        and (vals := _values(raw.get("radius")))
        and vals[0].isdigit()
        and int(vals[0]) in RADII
    ):
        f.radius = int(vals[0])
    if (vals := _values(raw.get("sort"))) and vals[0] in SORTS:
        default = "relevance" if f.q else "new"
        f.sort = None if vals[0] == default else vals[0]
    if (vals := _values(raw.get("page"))) and vals[0].isdigit():
        f.page = max(1, min(int(vals[0]), MAX_PAGE))

    # tier 3: a.<key>, only for attributes of the selected category
    for name, value in raw.items():
        if not name.startswith("a.") or (spec := specs.get(name[2:])) is None:
            continue
        vals = _values(value)
        if spec.type == "bool":
            if "1" in vals:
                f.attrs[spec.key] = True
        elif spec.type in {"enum", "multi_enum"}:
            chosen = tuple(sorted({v for v in vals if v in spec.options}))
            if chosen:
                f.attrs[spec.key] = chosen
    return f


def canonical_query(f: Filters) -> str:
    pairs: list[tuple[str, str]] = []
    for key, value in sorted(f.attrs.items()):
        pairs.append((f"a.{key}", "1" if value is True else ",".join(value)))  # type: ignore[arg-type]
    pairs += [(key, "1") for key in BOOL_KEYS if getattr(f, key)]
    if f.schedule:
        pairs.append(("schedule", ",".join(f.schedule)))
    if f.contract:
        pairs.append(("contract", ",".join(f.contract)))
    if f.posted:
        pairs.append(("posted", f.posted))
    if f.radius:
        pairs.append(("radius", str(f.radius)))
    if f.salary_min:
        pairs.append(("salary_min", str(f.salary_min)))
    if f.q:
        pairs.append(("q", f.q))
    if f.sort:
        pairs.append(("sort", f.sort))
    if f.page > 1:
        pairs.append(("page", str(f.page)))
    pairs.sort(key=lambda kv: kv[0])
    return "&".join(f"{k}={quote(v, safe=',')}" for k, v in pairs)


def cache_params(f: Filters) -> dict[str, object]:
    """Stable dict for cache keys (page and sort don't change facet counts)."""
    return {
        **{k: v for k, v in f.__dict__.items() if k not in {"page", "sort", "attrs", "q"}},
        "q": normalize(f.q) if f.q else None,
        "attrs": {k: v for k, v in sorted(f.attrs.items())},
    }
