"""Answers to the vacancies a person posted themselves.

The whole file is one rule: somebody sees an application only if it came to a listing they own. The
listing id travels with every query as a condition, never as something we trust from the request.
"""

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, undefer

from fastapi import HTTPException, status

from app.models import (
    Application,
    ApplicationFile,
    ApplicationNote,
    Listing,
    ListingTranslation,
    Resume,
    User,
)
from app.schemas.employer import CandidateNote, CandidateOut
from app.services import questions


def _mine(user: User):
    """The listings this person owns; every query starts here."""
    return select(Listing.id).where(Listing.owner_id == user.id)


async def get_application(session: AsyncSession, user: User, application_id: int) -> Application:
    application = await session.scalar(
        select(Application).where(
            Application.id == application_id,
            Application.listing_id.in_(_mine(user)),
        )
    )
    if application is None:
        # the same answer whether it is somebody else's or does not exist
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found")
    return application


async def count_new(session: AsyncSession, user: User) -> int:
    return (
        await session.scalar(
            select(func.count())
            .select_from(Application)
            .where(Application.listing_id.in_(_mine(user)), Application.status == "new")
        )
        or 0
    )


async def candidates(
    session: AsyncSession, user: User, lang: str, listing_id: int | None = None
) -> list[CandidateOut]:
    conds = [Application.listing_id.in_(_mine(user))]
    if listing_id is not None:
        conds.append(Application.listing_id == listing_id)
    rows = (
        await session.scalars(
            select(Application).where(*conds).order_by(Application.created_at.desc()).limit(200)
        )
    ).all()
    return [await _out(session, row, lang) for row in rows]


async def set_status(session: AsyncSession, application: Application, value: str) -> None:
    application.status = value
    await session.commit()


async def add_note(
    session: AsyncSession, application: Application, user: User, text: str
) -> ApplicationNote:
    note = ApplicationNote(application_id=application.id, author_id=user.id, text=text)
    session.add(note)
    await session.commit()
    await session.refresh(note)
    return note


async def cv_file(session: AsyncSession, application: Application) -> ApplicationFile:
    """The bytes are a deferred column: ask for them now, not by touching the attribute later."""
    row = await session.scalar(
        select(ApplicationFile)
        .options(undefer(ApplicationFile.data))
        .where(ApplicationFile.application_id == application.id)
        .order_by(ApplicationFile.id.desc())
        .limit(1)
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no_file")
    return row


# ---------------------------------------------------------------------------- output


async def _title(session: AsyncSession, listing_id: int | None, lang: str) -> str:
    if listing_id is None:
        return "—"
    listing = await session.scalar(
        select(Listing).where(Listing.id == listing_id).options(selectinload(Listing.translations))
    )
    if listing is None:
        return "—"
    by_lang = {t.lang: t for t in listing.translations}
    text = by_lang.get(lang) or by_lang.get(listing.original_lang) or next(iter(by_lang.values()), None)
    return text.title if text else "—"


async def out(session: AsyncSession, application: Application, lang: str) -> CandidateOut:
    """One candidate as the employer sees them."""
    return await _out(session, application, lang)


async def _out(session: AsyncSession, application: Application, lang: str) -> CandidateOut:
    answers = application.answers or {}
    asked = answers.get("questions") or []
    notes = (
        await session.scalars(
            select(ApplicationNote)
            .where(ApplicationNote.application_id == application.id)
            .order_by(ApplicationNote.created_at)
        )
    ).all()
    has_cv = bool(
        await session.scalar(
            select(exists().where(ApplicationFile.application_id == application.id))
        )
    )

    resume = (
        await session.scalar(select(Resume).where(Resume.user_id == application.user_id))
        if application.user_id
        else None
    )
    note_names = {}
    for note in notes:
        if note.author_id and note.author_id not in note_names:
            author = await session.get(User, note.author_id)
            note_names[note.author_id] = (author.name if author else None) or "—"

    return CandidateOut(
        id=application.id,
        listing_id=application.listing_id,
        listing_title=await _title(session, application.listing_id, lang),
        name=application.name,
        phone=application.phone,
        status=application.status,
        lang=application.lang,
        comment=answers.get("comment"),
        answers=[questions.describe(a, lang) for a in asked if isinstance(a, dict)],
        has_cv=has_cv,
        headline=resume.title if resume else None,
        experience_years=resume.experience_years if resume else None,
        licences=list(resume.licences or []) if resume else [],
        languages=dict(resume.languages or {}) if resume else {},
        notes=[
            CandidateNote(
                text=note.text,
                author=note_names.get(note.author_id or 0),
                created_at=note.created_at,
            )
            for note in notes
        ],
        created_at=application.created_at,
    )
