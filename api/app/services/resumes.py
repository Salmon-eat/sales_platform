"""The candidate's CV and applying with it in one press.

The point of the whole thing: somebody looking for work fills this in once, and afterwards answering a
vacancy is a single button. What the manager sees in the admin does not change at all — the application
arrives the same way it always did, with the file attached.
"""

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import (
    Application,
    ApplicationFile,
    ApplicationNote,
    Listing,
    Location,
    Resume,
    User,
)
from app.models.i18n import tr
from app.schemas.resume import ApplyIn, ApplyOut, ResumeIn, ResumeOut
from app.services import cv, questions

# applying twice to the same job in a day is the same application, not a second one
DUPLICATE_WINDOW = timedelta(hours=24)
# a job a person can still answer
OPEN_STATUSES = ("active",)


async def get(session: AsyncSession, user: User) -> Resume | None:
    return await session.scalar(select(Resume).where(Resume.user_id == user.id))


async def save(session: AsyncSession, user: User, data: ResumeIn) -> Resume:
    if data.city_id is not None:
        city = await session.get(Location, data.city_id)
        if city is None or city.level not in ("municipio", "localidad"):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "city_not_found")

    resume = await get(session, user)
    if resume is None:
        resume = Resume(user_id=user.id, title=data.title)
        session.add(resume)

    for field, value in data.model_dump().items():
        setattr(resume, field, value)
    await session.commit()
    await session.refresh(resume)
    return resume


async def attach_file(session: AsyncSession, resume: Resume, data: bytes, filename: str | None) -> Resume:
    """Same rules as a CV sent with an application: real PDF/Word/image, up to 5 MB, by content."""
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "empty_file")
    if len(data) > cv.MAX_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "file_too_large")
    content_type, ext = cv.detect(data)
    resume.file_name = cv.safe_name(filename, ext)
    resume.file_type = content_type
    resume.file_size = len(data)
    resume.file_data = data
    await session.commit()
    await session.refresh(resume)
    return resume


async def drop_file(session: AsyncSession, resume: Resume) -> None:
    resume.file_name = resume.file_type = None
    resume.file_size = resume.file_data = None
    await session.commit()


async def remove(session: AsyncSession, resume: Resume) -> None:
    await session.delete(resume)
    await session.commit()


async def apply(session: AsyncSession, user: User, resume: Resume, data: ApplyIn) -> ApplyOut:
    """Answer a vacancy with what is already in the account."""
    listing = await session.get(Listing, data.listing_id)
    if listing is None or listing.status not in OPEN_STATUSES:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "listing_not_found")
    if not user.phone:
        # a manager has to be able to call back; the account page asks for the number first
        raise HTTPException(status.HTTP_409_CONFLICT, "phone_required")

    now = datetime.now(UTC)
    answers = {"in_spain": True} if resume.work_permit else {}
    if data.comment:
        answers["comment"] = data.comment
    if data.questions:
        answers["questions"] = questions.answers_for(listing.questions or [], data.questions)

    existing = await session.scalar(
        select(Application)
        .where(
            Application.user_id == user.id,
            Application.listing_id == data.listing_id,
            Application.created_at > now - DUPLICATE_WINDOW,
        )
        .order_by(Application.created_at.desc())
        .limit(1)
    )
    if existing is not None:
        session.add(
            ApplicationNote(application_id=existing.id, text="Повторний відгук із кабінету кандидата")
        )
        await session.commit()
        return ApplyOut(application_id=existing.id, duplicate=True, with_file=resume.has_file)

    application = Application(
        listing_id=listing.id,
        category_id=listing.category_id,
        location_id=listing.location_id,
        user_id=user.id,
        name=user.name or resume.title,
        phone=user.phone,
        messenger="phone",
        answers=answers,
        lang=user.lang,
        source="site",
        consent_at=now,
        consent_version=settings.privacy_policy_version,
    )
    session.add(application)
    await session.flush()

    if resume.has_file:
        # the bytes are a deferred column: fetch them with an await, never by touching the attribute
        file_data = await session.scalar(select(Resume.file_data).where(Resume.id == resume.id))
        if file_data:
            # a copy, so editing the CV later does not change what the manager already read
            session.add(
                ApplicationFile(
                    application_id=application.id,
                    filename=resume.file_name or "cv.pdf",
                    content_type=resume.file_type or "application/pdf",
                    size=resume.file_size or len(file_data),
                    data=file_data,
                )
            )
    await session.commit()
    return ApplyOut(application_id=application.id, duplicate=False, with_file=resume.has_file)


async def out(session: AsyncSession, resume: Resume, lang: str) -> ResumeOut:
    city = await session.get(Location, resume.city_id) if resume.city_id else None
    return ResumeOut(
        id=resume.id,
        title=resume.title,
        about=resume.about,
        city_id=resume.city_id,
        city_name=tr(city.names, lang) if city else None,
        relocate=resume.relocate,
        experience_years=resume.experience_years,
        languages=resume.languages or {},
        licences=resume.licences or [],
        has_car=resume.has_car,
        work_permit=resume.work_permit,
        schedule=resume.schedule or [],
        salary_min=resume.salary_min,
        salary_period=resume.salary_period,
        is_public=resume.is_public,
        file_name=resume.file_name,
        file_size=resume.file_size,
        updated_at=resume.updated_at,
    )
