"""Autocomplete GET /v1/suggest (spec §7): professions, cities, "profession in city" with counts."""

from redis.asyncio import Redis
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Listing, Location
from app.models.i18n import tr
from app.schemas.search import (
    SuggestCombo,
    SuggestPlace,
    SuggestProfession,
    SuggestResponse,
    SuggestWord,
)
from app.search.text import normalize
from app.search.understanding import CategoryEntry, Dictionary, get_dictionary, understand
from app.services.cache import cached

LIMIT = 5
COMBOS = 3


def _profession(entry: CategoryEntry, lang: str, count: int) -> SuggestProfession:
    return SuggestProfession(
        slug=entry.slug[lang],
        key=entry.slug["es"],
        section_key=entry.section_key,
        name=tr(entry.name, lang),
        count=count,
    )


async def _category_counts(session: AsyncSession) -> dict[int, int]:
    rows = await session.execute(
        select(Listing.category_id, func.count())
        .where(Listing.status == "active")
        .group_by(Listing.category_id)
    )
    return dict(rows.all())


def _match_professions(d: Dictionary, prefix: str, counts: dict[int, int]) -> list[tuple[CategoryEntry, int]]:
    best: dict[int, tuple[int, CategoryEntry]] = {}
    for phrase, entries in d.categories.items():
        if phrase.startswith(prefix):
            score = 3
        elif f" {prefix}" in f" {phrase}":
            score = 2
        else:
            continue
        for entry in entries:
            score_e = score + (1 if entry.is_name else 0)
            if entry.id not in best or best[entry.id][0] < score_e:
                best[entry.id] = (score_e, d.by_category_id.get(entry.id, entry))

    def total(entry: CategoryEntry) -> int:
        own = counts.get(entry.id, 0)
        children = sum(counts.get(e.id, 0) for e in d.by_category_id.values() if e.parent_id == entry.id)
        return own + children

    ranked = sorted(best.values(), key=lambda s: (-s[0], -total(s[1]), s[1].parent_id is None))
    return [(entry, total(entry)) for _, entry in ranked[:LIMIT]]


WORDS = 8


def _words(d: Dictionary, prefix: str, counts: dict[int, int], lang: str) -> list[SuggestWord]:
    """Finish the word somebody is typing, and say where it belongs.

    A board answers "ноут" with "ноутбук", not with the name of a section — the visitor is halfway
    through a word, and what they want is the rest of it. Every phrase the site knows is a candidate:
    category names and all their synonyms, which is where the slang lives.
    """
    if not prefix:
        return []
    found: dict[str, tuple[int, CategoryEntry]] = {}
    for phrase, entries in d.categories.items():
        if phrase == prefix:
            continue  # they have typed it already; finishing it with itself helps nobody
        if phrase.startswith(prefix):
            rank = 0
        elif f" {prefix}" in f" {phrase}":  # a later word of the phrase starts with it
            rank = 1
        else:
            continue
        # a word of another language still counts (a Ukrainian may well type "piso"), but after ours
        if lang not in d.phrase_langs.get(phrase, {lang}):
            rank += 2
        for entry in entries:
            best = found.get(phrase)
            if best is None or rank < best[0]:
                found[phrase] = (rank, entry)

    def total(entry: CategoryEntry) -> int:
        return counts.get(entry.id, 0) + sum(
            counts.get(e.id, 0) for e in d.by_category_id.values() if e.parent_id == entry.id
        )

    ordered = sorted(
        found.items(), key=lambda kv: (kv[1][0], -total(kv[1][1]), d.phrase_order.get(kv[0], 0))
    )
    out: list[SuggestWord] = []
    for phrase, (_, entry) in ordered:
        section = d.sections.get(entry.section_id)
        # the agency's own pages are not a place to send somebody looking for ads
        if section is None or section.kind != "listings":
            continue
        if len(out) >= WORDS:
            break
        out.append(
            SuggestWord(
                text=d.display.get(phrase, phrase),
                category=tr(entry.name, lang),
                section=tr(section.name, lang),
                section_slug=section.slug.get(lang, section.slug["es"]),
                category_slug=entry.slug.get(lang, entry.slug["es"]),
                count=total(entry),
            )
        )
    return out


async def _places(
    session: AsyncSession, prefix: str, lang: str, category_ids: list[int] | None = None
) -> list[SuggestPlace]:
    counts = (
        select(Listing.location_id.label("location_id"), func.count().label("n"))
        .where(Listing.status == "active", *([Listing.category_id.in_(category_ids)] if category_ids else []))
        .group_by(Listing.location_id)
        .subquery()
    )
    stmt = (
        select(Location, func.coalesce(counts.c.n, 0))
        .outerjoin(counts, counts.c.location_id == Location.id)
        .where(Location.level == "municipio")
    )
    if prefix:
        stmt = stmt.where(
            or_(Location.search_text.like(f"{prefix}%"), Location.search_text.like(f"% {prefix}%"))
        )
    else:
        stmt = stmt.where(counts.c.n > 0)
    rows = (
        await session.execute(
            stmt.order_by(func.coalesce(counts.c.n, 0).desc(), Location.population.desc().nulls_last()).limit(
                LIMIT
            )
        )
    ).all()
    parents = {
        p.id: p
        for p in (
            await session.scalars(select(Location).where(Location.id.in_({loc.parent_id for loc, _ in rows})))
        ).all()
    }
    return [
        SuggestPlace(
            slug=loc.slug,
            level=loc.level,
            name=tr(loc.names, lang),
            parent_name=tr(parents[loc.parent_id].names, lang) if loc.parent_id in parents else None,
            count=n,
        )
        for loc, n in rows
    ]


async def build_suggestions(session: AsyncSession, redis: Redis, q: str, lang: str) -> SuggestResponse:
    d = await get_dictionary(session, redis)
    counts = await _category_counts(session)
    text = normalize(q)
    last = text.split()[-1] if text else ""

    understood = understand(d, q)
    professions = _match_professions(d, text, counts)
    if not professions and understood.category:
        entry = d.by_category_id.get(understood.category.id, understood.category)
        professions = [(entry, counts.get(entry.id, 0))]

    places = await _places(session, text, lang)
    if not places and last and last != text:
        places = await _places(session, last, lang)

    combos: list[SuggestCombo] = []
    top = (
        d.by_category_id.get(understood.category.id)
        if understood.category
        else (professions[0][0] if professions else None)
    )
    if top is not None:
        ids = [top.id] + [e.id for e in d.by_category_id.values() if e.parent_id == top.id]
        profession = _profession(top, lang, sum(counts.get(i, 0) for i in ids))
        if understood.place and understood.place.level == "municipio":
            chosen = await _places(session, normalize(tr(understood.place.names, "es")), lang, ids)
            candidates = [p for p in chosen if p.slug == understood.place.slug][:1]
        else:
            candidates = [p for p in await _places(session, "", lang, ids) if p.count > 0][:COMBOS]
        combos = [SuggestCombo(category=profession, place=p, count=p.count) for p in candidates]

    return SuggestResponse(
        professions=[_profession(e, lang, n) for e, n in professions],
        places=places,
        combos=combos,
        words=_words(d, text, counts, lang),
    )


async def suggest(session: AsyncSession, redis: Redis, q: str, lang: str) -> SuggestResponse:
    return await cached(
        redis,
        "suggest",
        {"lang": lang, "q": normalize(q)},
        settings.suggest_cache_ttl,
        SuggestResponse,
        lambda: build_suggestions(session, redis, q, lang),
    )
