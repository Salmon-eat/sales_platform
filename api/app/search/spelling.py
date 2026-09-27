"""Repairing a typed word against the words the site actually contains.

Postgres can stem Spanish and English; for Ukrainian and Russian it has nothing. Rather than hunting
for a dictionary per language, the site keeps its own vocabulary — every word that appears in a live
ad — and compares an unknown word against it by trigrams.

That one mechanism covers both cases people care about:
    "дiвани"  (a slip)          -> "диван"
    "coches"  (another ending)  -> "coche"
and it works the same in all four languages, because the vocabulary is the content, not a language.

A word is only ever replaced by one that is really on the site, so a correction always leads to results.
"""

import logging

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.search import SearchWord
from app.search.text import close_by_edits, normalize, one_alphabet

log = logging.getLogger("bazarcito.spelling")

MIN_LENGTH = 4
# how alike two words must be; trigram similarity, 1.0 is identical
SIMILAR_ENOUGH = 0.42
# a word from a single ad is a weak suggestion; prefer the ones many ads use
CANDIDATES = 5


async def known(session: AsyncSession, words: list[str]) -> set[str]:
    if not words:
        return set()
    rows = await session.scalars(select(SearchWord.word).where(SearchWord.word.in_(words)))
    return set(rows.all())


async def repair(session: AsyncSession, query: str) -> tuple[str, list[tuple[str, str]]]:
    """Returns the query to search with, and what was changed in it.

    Words the site knows are left exactly as they are — the correction never touches a word that
    already finds something.
    """
    words = normalize(query).split()
    if not words:
        return query, []

    # a word typed on two keyboard layouts is first put back into one alphabet, and only then looked up
    one_script = {word: one_alphabet(word) for word in words}
    seen = await known(session, words + [w for w in one_script.values() if w])
    fixed: list[str] = []
    changes: list[tuple[str, str]] = []
    for word in words:
        if word in seen or len(word) < MIN_LENGTH or word.isdigit():
            fixed.append(word)
            continue
        same_script = one_script[word]
        if same_script and same_script in seen:
            fixed.append(same_script)
            changes.append((word, same_script))
            continue
        better = await _closest(session, same_script or word)
        if better:
            fixed.append(better)
            changes.append((word, better))
        else:
            fixed.append(word)
    return " ".join(fixed), changes


async def _closest(session: AsyncSession, word: str) -> str | None:
    """The most-used word on the site that is close enough to this one."""
    similarity = func.similarity(SearchWord.word, word)
    rows = await session.execute(
        select(SearchWord.word, SearchWord.hits, similarity.label("score"))
        # the trigram index answers `%` quickly; the threshold below is the real filter
        .where(SearchWord.word.op("%")(word))
        .order_by(similarity.desc(), SearchWord.hits.desc())
        .limit(CANDIDATES)
    )
    # close by trigrams, or simply one keystroke away: the second catches "leptop" -> "laptop",
    # which shares too few trigrams to pass a threshold that is safe for everything else
    best = [
        (w, hits, score)
        for w, hits, score in rows.all()
        if score >= SIMILAR_ENOUGH or close_by_edits(word, w)
    ]
    if not best:
        return None
    # among equally close words, the one more ads use
    best.sort(key=lambda row: (round(row[2], 2), row[1]), reverse=True)
    return best[0][0]


COLLECT_SQL = """
SELECT word, ndoc
  FROM ts_stat('SELECT tsv_all FROM listing_search')
 WHERE length(word) BETWEEN 3 AND 60 AND word !~ '^[0-9]+$'
"""

# words from ads that are gone: nothing on the site contains them any more
PRUNE_SQL = "DELETE FROM search_words WHERE updated_at < now() - interval '2 days'"


async def refresh(session: AsyncSession) -> int:
    """Rebuild the vocabulary from the live ads (worker job, and a CLI command).

    Words are stored the way a typed query is normalized — otherwise "розкладний" in an ad and
    "розкладнии" from the search box would look like two different words, and the site would keep
    "correcting" a word that was right in the first place.
    """
    counted: dict[str, int] = {}
    for word, ndoc in (await session.execute(text(COLLECT_SQL))).all():
        same = normalize(word)
        if len(same) < 3 or same.isdigit():
            continue
        counted[same] = counted.get(same, 0) + int(ndoc)

    if counted:
        await session.execute(
            text(
                "INSERT INTO search_words (word, hits, updated_at) VALUES (:word, :hits, now()) "
                "ON CONFLICT (word) DO UPDATE SET hits = EXCLUDED.hits, updated_at = now()"
            ),
            [{"word": word, "hits": hits} for word, hits in counted.items()],
        )
    await session.execute(text(PRUNE_SQL))
    await session.commit()
    return await session.scalar(select(func.count()).select_from(SearchWord)) or 0
