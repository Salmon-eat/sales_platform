"""Query understanding, a light version of the Navtiro intent resolver (spec §7).

"водій се мадрид" -> profession conductor-ce + municipality madrid, nothing left -> redirect to the path.
Phrases (names + synonyms of categories in all languages, names + aliases of places) are matched
greedily, longest first. The dictionary lives in process memory and is rebuilt when the cache version
changes (seed-taxonomy / import-locations bump it; listing edits don't) or every 10 minutes.
"""

import time
from collections import defaultdict
from dataclasses import dataclass

from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category, Location, Section
from app.search.text import latin_lookalike, normalize
from app.services.cache import TAXONOMY_VERSION_KEY

MAX_NGRAM = 5
MIN_PLACE_TOKEN = 3
REFRESH_SECONDS = 600

# words that don't change the meaning once a profession or a place is recognised
STOPWORDS = {
    "в", "у", "на", "з", "із", "по", "робота", "роботу", "вакансія", "вакансії", "вакансия", "вакансии",
    "работа", "работу", "во", "trabajo", "empleo", "oferta", "ofertas", "de", "en", "el", "la",
    "job", "jobs", "work", "in", "at", "spain", "espana", "іспанія", "іспанії", "испания", "испании",
}  # fmt: skip


@dataclass(frozen=True)
class CategoryEntry:
    id: int
    section_id: int
    section_key: str
    parent_id: int | None
    slug: dict[str, str]
    name: dict[str, str]
    is_name: bool  # matched a name (stronger) or a synonym


@dataclass(frozen=True)
class PlaceEntry:
    id: int
    level: str
    slug: str
    names: dict[str, str]
    population: int


@dataclass
class Understood:
    category: CategoryEntry | None
    place: PlaceEntry | None
    rest: str  # the part of the query that is not a profession/place (goes to FTS)

    @property
    def complete(self) -> bool:
        return (self.category is not None or self.place is not None) and not self.rest


@dataclass
class Dictionary:
    categories: dict[str, list[CategoryEntry]]
    places: dict[str, PlaceEntry]
    by_category_id: dict[int, CategoryEntry]
    version: str
    built_at: float


_cache: Dictionary | None = None


async def _version(redis: Redis) -> str:
    try:
        return await redis.get(TAXONOMY_VERSION_KEY) or "0"
    except RedisError:
        return "?"


async def get_dictionary(session: AsyncSession, redis: Redis) -> Dictionary:
    global _cache
    version = await _version(redis)
    if _cache and _cache.version == version and time.monotonic() - _cache.built_at < REFRESH_SECONDS:
        return _cache

    sections = {s.id: s for s in (await session.scalars(select(Section))).all()}
    categories: dict[str, list[CategoryEntry]] = defaultdict(list)
    by_id: dict[int, CategoryEntry] = {}
    for c in (await session.scalars(select(Category).where(Category.is_enabled))).all():
        section = sections[c.section_id]
        if not section.is_enabled:
            continue
        base = dict(
            id=c.id,
            section_id=c.section_id,
            section_key=section.key,
            parent_id=c.parent_id,
            slug=c.slug,
            name=c.name,
        )
        by_id[c.id] = CategoryEntry(**base, is_name=True)
        for phrase in {normalize(n) for n in c.name.values()}:
            categories[phrase].append(CategoryEntry(**base, is_name=True))
        for phrase in {normalize(s) for words in c.synonyms.values() for s in words}:
            categories[phrase].append(CategoryEntry(**base, is_name=False))

    places: dict[str, PlaceEntry] = {}
    rows = await session.execute(
        select(
            Location.id, Location.level, Location.slug, Location.names, Location.aliases, Location.population
        ).where(Location.level.in_(["municipio", "provincia", "comunidad"]))
    )
    level_rank = {"municipio": 2, "provincia": 1, "comunidad": 0}
    for id_, level, slug, names, aliases, population in rows:
        entry = PlaceEntry(id_, level, slug, names, population or 0)
        for phrase in {normalize(n) for n in [*names.values(), *aliases]}:
            if not phrase:
                continue
            current = places.get(phrase)
            # a city beats a province with the same name (Valencia); a bigger city beats a smaller one
            if current is None or (level_rank[level], entry.population) > (
                level_rank[current.level],
                current.population,
            ):
                places[phrase] = entry

    _cache = Dictionary(categories, places, by_id, version, time.monotonic())
    return _cache


def _best_category(entries: list[CategoryEntry], section_key: str | None) -> CategoryEntry | None:
    candidates = [e for e in entries if section_key is None or e.section_key == section_key] or entries
    # a name beats a synonym; a profession beats a sector
    return min(candidates, key=lambda e: (not e.is_name, e.parent_id is None, e.id), default=None)


def understand(dictionary: Dictionary, q: str, section_key: str | None = None) -> Understood:
    words = normalize(q).split()
    category: CategoryEntry | None = None
    place: PlaceEntry | None = None
    rest: list[str] = []

    i = 0
    while i < len(words):
        matched = False
        for n in range(min(MAX_NGRAM, len(words) - i), 0, -1):
            chunk = words[i : i + n]
            variants = {" ".join(chunk), " ".join(latin_lookalike(w) or w for w in chunk)}
            if category is None:
                entries = [e for v in variants for e in dictionary.categories.get(v, [])]
                if entries and (found := _best_category(entries, section_key)):
                    category, i, matched = found, i + n, True
                    break
            if place is None and (n > 1 or len(chunk[0]) >= MIN_PLACE_TOKEN):
                found_place = next((dictionary.places[v] for v in variants if v in dictionary.places), None)
                if found_place:
                    place, i, matched = found_place, i + n, True
                    break
        if not matched:
            rest.append(words[i])
            i += 1

    if category or place:
        rest = [w for w in rest if w not in STOPWORDS]
    return Understood(category=category, place=place, rest=" ".join(rest))
