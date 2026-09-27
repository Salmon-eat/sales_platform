"""Words the site learned, and the ones it is not sure enough about.

The nightly job adds a word on its own only when many separate visits point at the same category.
Everything weaker lands here, because a wrong synonym attaches itself to every ad in the category and
is worse than a missing one.
"""

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select

from app.api.deps import AdminLang, RedisDep, SessionDep, require_staff
from app.models import Category, Section, SynonymProposal, User
from app.models.i18n import tr
from app.services import synonyms, wikidata
from app.services.cache import bump_cache_version

router = APIRouter(prefix="/admin/search-words", tags=["admin: search words"])

Staff = Annotated[User, Depends(require_staff)]


class DecideIn(BaseModel):
    action: Literal["add", "ignore"]
    # the person may know better than the guess
    category_id: int | None = None
    # the same thing in the other languages, as a Wikidata lookup returned it
    words: dict[str, list[str]] | None = None


@router.get("/proposals")
async def proposals(
    session: SessionDep,
    user: Staff,
    lang: AdminLang,
    status: Annotated[Literal["new", "added", "ignored"], Query()] = "new",
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[dict]:
    rows = (
        await session.execute(
            select(SynonymProposal, Category, Section)
            .outerjoin(Category, Category.id == SynonymProposal.category_id)
            .outerjoin(Section, Section.id == Category.section_id)
            .where(SynonymProposal.status == status)
            .order_by(SynonymProposal.opened.desc(), SynonymProposal.searches.desc())
            .limit(limit)
        )
    ).all()
    return [
        {
            "id": p.id,
            "word": p.word,
            "lang": p.lang,
            "searches": p.searches,
            "opened": p.opened,
            "status": p.status,
            "category_id": p.category_id,
            "category": tr(c.name, lang) if c else None,
            "section": tr(s.name, lang) if s else None,
        }
        for p, c, s in rows
    ]


@router.get("/count")
async def count(session: SessionDep, user: Staff) -> dict[str, int]:
    waiting = await session.scalar(
        select(func.count()).select_from(SynonymProposal).where(SynonymProposal.status == "new")
    )
    return {"waiting": waiting or 0}


@router.post("/proposals/{proposal_id}", status_code=204)
async def decide(
    proposal_id: int, body: DecideIn, session: SessionDep, redis: RedisDep, user: Staff
) -> None:
    await synonyms.decide(
        session,
        proposal_id,
        accept=body.action == "add",
        category_id=body.category_id,
        user_id=user.id,
        words=body.words,
    )
    # the ads of that category carry a new word now
    await bump_cache_version(redis, taxonomy=True)


@router.get("/lookup")
async def lookup(
    session: SessionDep,
    redis: RedisDep,
    user: Staff,
    proposal_id: Annotated[int, Query()],
) -> dict[str, Any]:
    """What this word means, in all four languages, so one "yes" teaches the site all of them."""
    proposal = await session.get(SynonymProposal, proposal_id)
    if proposal is None:
        return {"found": None}
    found = await wikidata.look_up(redis, proposal.word, proposal.lang)
    return {"found": found.model_dump() if found else None}


@router.post("/collect")
async def collect_now(session: SessionDep, redis: RedisDep, user: Staff) -> dict[str, int]:
    """Run the nightly job by hand, for when somebody wants to see it work."""
    written, applied = await synonyms.collect(session)
    await bump_cache_version(redis, taxonomy=True)
    return {"proposals": written, "applied": applied}
