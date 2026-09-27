"""Looking a word up in Wikidata, so one decision teaches the site four languages at once.

Somebody searched for "пилосос" and found nothing. A person in the admin can see what it is and which
category it belongs to — but they would be adding one Ukrainian word, and the Spanish visitor typing
"aspiradora" would still find nothing.

Wikidata knows the same thing in every language, with the everyday names people use for it:

    Q101674  пилосос | пилосмок, пилотяг   пылесос   aspiradora | aspirador   vacuum cleaner | hoover, vac

It is free (CC0), needs no account and no key. Nothing is added by itself: the lookup only shows what
it found, with the description, so the person can see it is the right thing before agreeing.
"""

import asyncio
import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from pydantic import BaseModel
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.models.i18n import LANGS
from app.search.text import normalize

log = logging.getLogger("bazarcito.wikidata")

API = "https://www.wikidata.org/w/api.php"
# Wikimedia asks every caller to say who it is; an anonymous script can be refused
USER_AGENT = "Citobazar/1.0 (https://citobazar.com; search dictionary) python-urllib"
TIMEOUT = 8
CACHE_TTL = 7 * 24 * 3600
# a concept nobody would ever look for on a classifieds board
MAX_WORDS_PER_LANG = 6


class WikidataLookup(BaseModel):
    """What was found, in the visitor's four languages, for a person to agree with or reject."""

    id: str
    title: str
    description: str = ""
    url: str
    # language -> the usual name first, then the other names people use for the same thing
    words: dict[str, list[str]]


def _get(params: dict[str, str]) -> dict:
    url = f"{API}?{urllib.parse.urlencode({**params, 'format': 'json'})}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310 (fixed https URL)
        return json.loads(response.read().decode())


def _search(word: str, lang: str) -> str | None:
    found = _get(
        {"action": "wbsearchentities", "search": word, "language": lang, "uselang": lang,
         "type": "item", "limit": "1"}
    ).get("search") or []
    return found[0]["id"] if found else None


def _entity(entity_id: str) -> dict:
    languages = "|".join(LANGS)
    return _get(
        {"action": "wbgetentities", "ids": entity_id, "props": "labels|aliases|descriptions",
         "languages": languages}
    )["entities"][entity_id]


def _words_of(entity: dict) -> dict[str, list[str]]:
    """The label first, then the aliases: the usual name before the ones people also say."""
    out: dict[str, list[str]] = {}
    for lang in LANGS:
        names: list[str] = []
        label = (entity.get("labels") or {}).get(lang, {}).get("value")
        if label:
            names.append(label)
        for alias in (entity.get("aliases") or {}).get(lang, []):
            if alias["value"] not in names:
                names.append(alias["value"])
        kept = [name for name in names if len(name) <= 60][:MAX_WORDS_PER_LANG]
        if kept:
            out[lang] = kept
    return out


def _fetch(word: str, lang: str) -> WikidataLookup | None:
    entity_id = _search(word, lang)
    if entity_id is None:
        return None
    entity = _entity(entity_id)
    words = _words_of(entity)
    if not words:
        return None
    return WikidataLookup(
        id=entity_id,
        title=(entity.get("labels") or {}).get(lang, {}).get("value") or word,
        description=(entity.get("descriptions") or {}).get(lang, {}).get("value") or "",
        url=f"https://www.wikidata.org/wiki/{entity_id}",
        words=words,
    )


async def look_up(redis: Redis, word: str, lang: str) -> WikidataLookup | None:
    """One word, four languages. Cached for a week: what a thing is called does not change."""
    word = normalize(word)
    if not word:
        return None
    key = f"wikidata:{lang}:{word}"
    try:
        if (hit := await redis.get(key)) is not None:
            return WikidataLookup.model_validate_json(hit) if hit != "-" else None
    except RedisError:
        pass  # a missing cache is not a reason to refuse

    try:
        found = await asyncio.to_thread(_fetch, word, lang)
    except (OSError, urllib.error.HTTPError, KeyError, ValueError) as error:
        log.warning("wikidata lookup of %r failed: %r", word, error)
        return None

    try:
        await redis.set(key, found.model_dump_json() if found else "-", ex=CACHE_TTL)
    except RedisError:
        pass
    return found
