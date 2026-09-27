"""Query understanding, a light version of the Navtiro intent resolver (spec §7).

"водій се мадрид" -> profession conductor-ce + municipality madrid, nothing left -> redirect to the path.
Phrases (names + synonyms of categories in all languages, names + aliases of places) are matched
greedily, longest first. The dictionary lives in process memory and is rebuilt when the cache version
changes (seed-taxonomy / import-locations bump it; listing edits don't) or every 10 minutes.
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field

from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category, Location, Section
from app.search.text import STEM, STOPWORDS, close_enough, latin_lookalike, normalize, one_alphabet
from app.services.cache import TAXONOMY_VERSION_KEY

MAX_NGRAM = 5
MIN_PLACE_TOKEN = 3
REFRESH_SECONDS = 600

# the same words the text search skips: they don't change the meaning once a profession or a place
# is recognised either


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
class SectionEntry:
    id: int
    key: str
    slug: dict[str, str]
    name: dict[str, str]
    kind: str = "listings"  # "services" sections are agency pages, they hold no ads


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
    # phrases are stored stripped of accents for matching; this gives back the spelling to show
    # somebody who is typing ("portatil" -> "portátil")
    display: dict[str, str] = field(default_factory=dict)
    # which languages a phrase was written in, so a Ukrainian is not offered Russian words first
    phrase_langs: dict[str, set[str]] = field(default_factory=dict)
    # the order words were written in the seed files: the common word comes before the slang for it
    phrase_order: dict[str, int] = field(default_factory=dict)
    sections: dict[int, SectionEntry] = field(default_factory=dict)
    # the same words grouped by their first letters, so a word with a different ending can be found
    # without walking the whole dictionary: {"вале": ["валencia", "valencia"…]}
    places_by_stem: dict[str, list[str]] = field(default_factory=dict)
    categories_by_stem: dict[str, list[str]] = field(default_factory=dict)


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
    display: dict[str, str] = {}
    phrase_langs: dict[str, set[str]] = {}
    phrase_order: dict[str, int] = {}
    for c in (await session.scalars(select(Category).where(Category.is_enabled))).all():
        section = sections[c.section_id]
        if not section.is_enabled:
            continue
        written_in: list[tuple[str, str]] = [(lang, text) for lang, text in c.name.items()]
        written_in += [(lang, w) for lang, words in c.synonyms.items() for w in words]
        for lang, written in written_in:
            phrase = normalize(written)
            display.setdefault(phrase, written)
            phrase_langs.setdefault(phrase, set()).add(lang)
            phrase_order.setdefault(phrase, len(phrase_order))
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

    _cache = Dictionary(
        categories,
        places,
        by_id,
        version,
        time.monotonic(),
        display=display,
        phrase_langs=phrase_langs,
        phrase_order=phrase_order,
        sections={
            s.id: SectionEntry(s.id, s.key, s.slug, s.name, s.kind)
            for s in sections.values()
            if s.is_enabled
        },
        places_by_stem=_by_stem(places, FUZZY_MIN_POPULATION),
        categories_by_stem=_by_stem(categories),
    )
    return _cache


# Spain has thousands of villages, and one of them is called Remondo — close enough to "ремонт" to
# swallow the word. Only towns people actually search for are matched by a changed ending.
FUZZY_MIN_POPULATION = 20_000


def _by_stem(phrases: dict, min_population: int = 0) -> dict[str, list[str]]:
    """One-word entries grouped by their first letters; phrases of two words keep their exact form."""
    grouped: dict[str, list[str]] = defaultdict(list)
    for phrase, entry in phrases.items():
        if " " in phrase or len(phrase) < STEM + 1:
            continue
        if min_population and getattr(entry, "population", 0) < min_population:
            continue
        grouped[phrase[:STEM]].append(phrase)
    return grouped


def _similar(word: str, grouped: dict[str, list[str]]) -> str | None:
    """The dictionary word this one is a form of: "валенсії" -> "валенсія"."""
    if len(word) < STEM + 1:
        return None
    for candidate in grouped.get(word[:STEM], ()):
        if close_enough(word, candidate):
            return candidate
    return None


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
            variants = {
                " ".join(chunk),
                " ".join(latin_lookalike(w) or w for w in chunk),
                " ".join(one_alphabet(w) or w for w in chunk),
            }
            # one word written with a different ending ("у Валенсії", "ремонту") still counts
            if n == 1:
                same_place = _similar(chunk[0], dictionary.places_by_stem)
                if same_place:
                    variants.add(same_place)
                same_category = _similar(chunk[0], dictionary.categories_by_stem)
                if same_category:
                    variants.add(same_category)
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
