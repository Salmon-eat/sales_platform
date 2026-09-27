"""The dictionary that grows by itself.

Two things already run without anybody: the site's vocabulary (what a typo is repaired against) is
rebuilt from the live ads every half hour, and zero-result queries are recorded as they happen.

What could not be automated is meaning: no machine knows that "холодильник" belongs in "Дім і сад".
But the visitors do know, and they show it — they search a word, find nothing, and then open an ad
anyway. This job watches exactly that:

    searched "холодильник", found nothing, then opened an ad in Дім і сад
    ... 7 different sessions did the same
    -> "холодильник" is a word of Дім і сад

Evidence that strong is applied on its own. Anything weaker waits for a person, because a wrong
synonym is worse than a missing one: it attaches itself to every ad in the category.

Approved words go into categories.extra_synonyms, never into the seed file, so seeding the taxonomy
cannot wipe what the site has learned.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category, SynonymProposal
from app.search.text import normalize

log = logging.getLogger("bazarcito.synonyms")

# a word one person typed once is noise; this many separate visits make it a question worth asking
MIN_SEARCHES = 3
# ...and this many of them ending in the same category make it an answer
AUTO_SEARCHES = 6
AUTO_SHARE = 0.6
LOOK_BACK_DAYS = 30
MAX_WORD = 60

# What was typed, what was opened right afterwards, in the same visit. The listing id on the
# listing_view event gives the category; nothing here reads anything personal.
EVIDENCE_SQL = """
WITH searches AS (
    SELECT session, lang, created_at,
           lower(btrim(props ->> 'q')) AS q,
           coalesce((props ->> 'found')::int, -1) AS found
      FROM analytics_events
     WHERE type = 'search'
       AND created_at >= now() - make_interval(days => :days)
       AND props ? 'q'
), empty AS (
    SELECT * FROM searches WHERE found = 0 AND length(q) BETWEEN 3 AND :max_word
), opened AS (
    SELECT e.session, e.created_at, l.category_id
      FROM analytics_events e
      JOIN listings l ON l.id = e.listing_id
     WHERE e.type = 'listing_view'
       AND e.created_at >= now() - make_interval(days => :days)
)
SELECT empty.q AS word,
       empty.lang AS lang,
       opened.category_id AS category_id,
       count(DISTINCT empty.session) AS sessions
  FROM empty
  LEFT JOIN opened
         ON opened.session = empty.session
        AND opened.created_at BETWEEN empty.created_at AND empty.created_at + interval '15 minutes'
 WHERE empty.lang IS NOT NULL
 GROUP BY 1, 2, 3
"""


async def collect(session: AsyncSession) -> tuple[int, int]:
    """Look at the last month and write down what the site could learn. Returns (proposals, applied)."""
    rows = (
        await session.execute(text(EVIDENCE_SQL), {"days": LOOK_BACK_DAYS, "max_word": MAX_WORD})
    ).all()

    # per (word, language): how often it was searched at all, and where people went afterwards
    totals: dict[tuple[str, str], int] = {}
    by_category: dict[tuple[str, str], dict[int, int]] = {}
    for row in rows:
        word = normalize(row.word)
        if not word or " " in word or len(word) < 3:
            continue  # a whole phrase is not a synonym of one category
        key = (word, row.lang)
        totals[key] = totals.get(key, 0) + row.sessions
        if row.category_id is not None:
            by_category.setdefault(key, {})
            by_category[key][row.category_id] = by_category[key].get(row.category_id, 0) + row.sessions

    written = applied = 0
    for (word, lang), searches in totals.items():
        if searches < MIN_SEARCHES:
            continue
        winner, opened = max(by_category.get((word, lang), {}).items(), key=lambda kv: kv[1], default=(None, 0))
        # nothing to propose if that category already knows the word (the search failed for some
        # other reason — the ads it would match are simply not there)
        if winner is not None:
            category = await session.get(Category, winner)
            if category is not None and knows(category, lang, word):
                continue
        proposal = await session.scalar(
            select(SynonymProposal).where(SynonymProposal.word == word, SynonymProposal.lang == lang)
        )
        if proposal is None:
            proposal = SynonymProposal(word=word, lang=lang)
            session.add(proposal)
            written += 1
        elif proposal.status != "new":
            continue  # already decided; do not ask again
        proposal.category_id = winner
        proposal.searches = searches
        proposal.opened = opened

        sure = winner is not None and opened >= AUTO_SEARCHES and opened >= searches * AUTO_SHARE
        if sure and await add_word(session, winner, lang, word):
            proposal.status = "added"
            proposal.decided_at = datetime.now(UTC)
            applied += 1
    await session.commit()
    return written, applied


def knows(category: Category, lang: str, word: str) -> bool:
    """Is this word already one of the category's, from the seed file or learned earlier?"""
    return word in (category.synonyms or {}).get(lang, []) or word in (category.extra_synonyms or {}).get(
        lang, []
    )


async def add_word(session: AsyncSession, category_id: int, lang: str, word: str) -> bool:
    """Teach a category a word. The search documents of its ads are rebuilt by the database trigger."""
    category = await session.get(Category, category_id)
    if category is None or knows(category, lang, word):
        return False
    learned = dict(category.extra_synonyms or {})
    words = [*learned.get(lang, []), word]
    learned[lang] = words
    category.extra_synonyms = learned  # a new dict, so SQLAlchemy sees the change
    log.info("category %s learned %r (%s)", category_id, word, lang)
    return True


async def decide(
    session: AsyncSession, proposal_id: int, *, accept: bool, category_id: int | None, user_id: int | None
) -> SynonymProposal | None:
    """A person says yes or no. "Yes" may point at a different category than the one guessed."""
    proposal = await session.get(SynonymProposal, proposal_id)
    if proposal is None or proposal.status != "new":
        return proposal
    if accept:
        target = category_id or proposal.category_id
        if target is None:
            return proposal
        await add_word(session, target, proposal.lang, proposal.word)
        proposal.category_id = target
        proposal.status = "added"
    else:
        proposal.status = "ignored"
    proposal.decided_at = datetime.now(UTC)
    proposal.decided_by = user_id
    await session.commit()
    return proposal
