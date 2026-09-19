import logging
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, not_, select
from sqlalchemy.orm import selectinload

from app.api.deps import AdminLang, CurrentUser, SessionDep, require_admin, require_staff
from app.models import (
    Application,
    ApplicationMessage,
    ApplicationNote,
    AttributeDefinition,
    Category,
    Listing,
    Location,
    Section,
)
from app.models.i18n import tr
from app.schemas.application import (
    AdminApplication,
    AdminApplicationDetail,
    AdminApplicationUpdate,
    AdminChatMessage,
    ApplicationNoteOut,
    ApplicationStatus,
    AppliedListing,
    BotInfo,
    ChatMessageIn,
)
from app.schemas.common import Page
from app.schemas.location import AdminLocation
from app.schemas.taxonomy import AdminSection
from app.services import telegram
from app.services.applications import chat_messages
from app.services.dashboard import STALE_AFTER
from app.services.gdpr import anonymize, export_person, person_applications
from app.services.locations import coords, search_condition, with_parent_name
from app.services.taxonomy import build_admin_taxonomy

router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger("admin")

MAX_LIMIT = 100
OPEN_STATUSES = ("new", "in_progress")


@router.get("/stats", dependencies=[Depends(require_staff)])
async def stats(session: SessionDep) -> dict[str, int]:
    async def count(model: type) -> int:
        return await session.scalar(select(func.count()).select_from(model)) or 0

    by_level = dict(
        (await session.execute(select(Location.level, func.count()).group_by(Location.level))).all()
    )
    return {
        "sections": await count(Section),
        "categories": await count(Category),
        "attributes": await count(AttributeDefinition),
        "comunidades": by_level.get("comunidad", 0),
        "provincias": by_level.get("provincia", 0),
        "municipios": by_level.get("municipio", 0),
        "localidades": by_level.get("localidad", 0),
        "listings_active": await session.scalar(
            select(func.count()).select_from(Listing).where(Listing.status == "active")
        )
        or 0,
        "applications_new": await session.scalar(
            select(func.count()).select_from(Application).where(Application.status == "new")
        )
        or 0,
    }


# read access for managers too (the listing form needs categories and attributes); editing is admin-only
@router.get("/taxonomy", response_model=list[AdminSection], dependencies=[Depends(require_staff)])
async def taxonomy(session: SessionDep) -> list[AdminSection]:
    return await build_admin_taxonomy(session)


@router.get("/locations", response_model=Page[AdminLocation], dependencies=[Depends(require_staff)])
async def locations(
    session: SessionDep,
    lang: AdminLang,
    q: Annotated[str | None, Query(max_length=100)] = None,
    level: Annotated[
        list[Literal["comunidad", "provincia", "municipio", "localidad"]] | None, Query()
    ] = None,
    missing: Annotated[
        Literal["en", "uk", "ru"] | None, Query(description="only rows without this name")
    ] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = 50,
) -> Page[AdminLocation]:
    conds = []
    if q:
        conds.append(search_condition(q))
    if level:
        conds.append(Location.level.in_(level))
    if missing:
        conds.append(not_(Location.names.has_key(missing)))

    total = await session.scalar(select(func.count()).select_from(Location).where(*conds)) or 0

    lat, lon = coords()
    stmt, parent = with_parent_name(select(Location, lat, lon))
    stmt = stmt.add_columns(parent.names.label("parent_names"))
    rows = await session.execute(
        stmt.where(*conds)
        .order_by(Location.population.desc().nulls_last(), Location.id)
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    items = [
        AdminLocation(
            id=loc.id,
            level=loc.level,
            slug=loc.slug,
            ine_code=loc.ine_code,
            names=loc.names,
            aliases=loc.aliases,
            population=loc.population,
            lat=lat_value,
            lon=lon_value,
            parent_name=tr(parent_names, lang),
        )
        for loc, lat_value, lon_value, parent_names in rows
    ]
    return Page(items=items, total=total, page=page, per_page=per_page)


# ---------- applications (stage 5 adds assignment, notes UI, CSV export) ----------


@router.get("/applications", response_model=Page[AdminApplication], dependencies=[Depends(require_staff)])
async def applications(
    session: SessionDep,
    lang: AdminLang,
    status_: Annotated[ApplicationStatus | None, Query(alias="status")] = None,
    stale: Annotated[bool, Query(description="new/in progress without changes for 48 h")] = False,
    origin: Annotated[
        Literal["site", "bot"], Query(description="the site's applications or the Telegram bot's")
    ] = "site",
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = 50,
) -> Page[AdminApplication]:
    conds = [Application.source == "bot" if origin == "bot" else Application.source != "bot"]
    if status_:
        conds.append(Application.status == status_)
    if stale:
        conds += [
            Application.status.in_(OPEN_STATUSES),
            Application.updated_at < datetime.now(UTC) - STALE_AFTER,
        ]
    total = await session.scalar(select(func.count()).select_from(Application).where(*conds)) or 0
    items = await _application_items(
        session,
        lang,
        conds,
        offset=(page - 1) * per_page,
        limit=per_page,
    )
    return Page(items=items, total=total, page=page, per_page=per_page)


@router.get(
    "/applications/{application_id}",
    response_model=AdminApplicationDetail,
    dependencies=[Depends(require_staff)],
)
async def application_detail(
    application_id: int, session: SessionDep, lang: AdminLang
) -> AdminApplicationDetail:
    application = await session.get(Application, application_id)
    if application is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")
    [item] = await _application_items(session, lang, [Application.id == application_id])
    history = (
        await _application_items(
            session,
            lang,
            [
                Application.phone == application.phone,
                Application.id != application_id,
                # site and bot applications are kept apart, each in its own tab
                (Application.source == "bot")
                if application.source == "bot"
                else (Application.source != "bot"),
            ],
        )
        if application.phone
        else []
    )
    notes = await session.scalars(
        select(ApplicationNote)
        .where(ApplicationNote.application_id == application_id)
        .order_by(ApplicationNote.created_at)
    )
    messages = await chat_messages(session, application_id)
    # opening the card is reading the conversation
    unread = [m for m in messages if m.author == "visitor" and m.read_at is None]
    if unread:
        now = datetime.now(UTC)
        for m in unread:
            m.read_at = now
        await session.commit()
    return AdminApplicationDetail(
        **item.model_dump(),
        utm=application.utm,
        history=history,
        notes=[ApplicationNoteOut(id=n.id, text=n.text, created_at=n.created_at) for n in notes],
        messages=[AdminChatMessage.model_validate(m, from_attributes=True) for m in messages],
        bot=BotInfo(app_id=application.bot_app_id, **_bot_fields(application.bot))
        if application.bot_app_id is not None
        else None,
        consent_at=application.consent_at,
        consent_version=application.consent_version,
        anonymized_at=application.anonymized_at,
        person_applications=len(history) + 1,
    )


# ---------- GDPR (admin only, admin spec §9): the person's data on request, erasure on request ----------


async def _site_application(session: SessionDep, application_id: int) -> Application:
    """GDPR requests cover the site's applications only: the bot's records follow the bot's own rules."""
    application = await session.get(Application, application_id)
    if application is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")
    if application.source == "bot":
        raise HTTPException(status.HTTP_409_CONFLICT, "Telegram bot applications are kept by the bot")
    return application


@router.get("/applications/{application_id}/person-data", dependencies=[Depends(require_admin)])
async def person_data(application_id: int, session: SessionDep) -> dict:
    """Everything about the person (same phone): the answer to an access / portability request."""
    application = await _site_application(session, application_id)
    logger.info("gdpr export of application %s", application_id)
    return await export_person(session, application)


@router.post("/applications/{application_id}/erase", dependencies=[Depends(require_admin)])
async def erase_person(application_id: int, session: SessionDep) -> dict[str, int]:
    """Erase the person's personal data in all their applications; the statistics stay."""
    application = await _site_application(session, application_id)
    count = await anonymize(session, await person_applications(session, application))
    logger.info("gdpr erasure: %s applications of application %s's person", count, application_id)
    return {"erased": count}


@router.post(
    "/applications/{application_id}/messages",
    response_model=list[AdminChatMessage],
    dependencies=[Depends(require_staff)],
)
async def reply_in_chat(
    application_id: int, body: ChatMessageIn, session: SessionDep, user: CurrentUser
) -> list[AdminChatMessage]:
    """A manager's reply: in the orange window on the site, or in Telegram for a bot application."""
    application = await session.get(Application, application_id)
    via_bot = application is not None and application.bot_app_id is not None
    open_chat = application is not None and (application.chat_token or via_bot)
    if not open_chat or application.anonymized_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No conversation for this application")
    message = ApplicationMessage(
        application_id=application_id,
        author="staff",
        author_id=user.id,
        # shown in the Telegram topic: who of the team answered from the site
        author_name=user.name or (user.email or "").split("@")[0] or None,
        text=body.text,
        delivery="pending" if via_bot else None,
    )
    session.add(message)
    await session.flush()
    if via_bot:
        telegram.queue_reply(session, application, message.id)
    if application.status == "new":
        application.status = "in_progress"
        if via_bot:
            telegram.queue_status(session, application)
    application.updated_at = datetime.now(UTC)
    await session.commit()
    return [
        AdminChatMessage.model_validate(m, from_attributes=True)
        for m in await chat_messages(session, application_id)
    ]


def _bot_fields(info: dict) -> dict:
    return {k: info.get(k) for k in ("title", "card", "username", "topic_url", "manager_name", "status")}


async def _application_items(
    session: SessionDep, lang: str, conds: list, offset: int = 0, limit: int = MAX_LIMIT
) -> list[AdminApplication]:
    notes = (
        select(func.count())
        .select_from(ApplicationNote)
        .where(ApplicationNote.application_id == Application.id)
        .scalar_subquery()
    )
    unread = (
        select(func.count())
        .select_from(ApplicationMessage)
        .where(
            ApplicationMessage.application_id == Application.id,
            ApplicationMessage.author == "visitor",
            ApplicationMessage.read_at.is_(None),
        )
        .scalar_subquery()
    )
    rows = (
        await session.execute(
            select(Application, Category.name, Location.names, notes, unread)
            .outerjoin(Category, Category.id == Application.category_id)
            .outerjoin(Location, Location.id == Application.location_id)
            .where(*conds)
            .order_by(Application.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    ).all()
    applied = await _applied_listings(session, {a.listing_id for a, *_ in rows if a.listing_id}, lang)
    stale_before = datetime.now(UTC) - STALE_AFTER
    items = []
    for a, category_name, location_names, notes_count, unread_count in rows:
        job = applied.get(a.listing_id) if a.listing_id else None
        items.append(
            AdminApplication(
                id=a.id,
                name=a.name,
                phone=a.phone,
                messenger=a.messenger,
                status=a.status,
                lang=a.lang,
                source=a.source,
                # a response to a job: its profession and city unless the candidate gave their own
                category_name=tr(category_name, lang) or (job[1] if job else None) or a.bot.get("title"),
                location_name=tr(location_names, lang) or (job[0].location_name if job else None),
                listing=job[0] if job else None,
                in_spain=a.answers.get("in_spain"),
                comment=a.answers.get("comment"),
                notes_count=notes_count,
                created_at=a.created_at,
                updated_at=a.updated_at,
                stale=a.status in OPEN_STATUSES and a.updated_at < stale_before,
                unread=unread_count,
            )
        )
    return items


async def _applied_listings(
    session: SessionDep, ids: set[int], lang: str
) -> dict[int, tuple[AppliedListing, str]]:
    """Jobs the candidates responded to: title in the admin language (else the fallback text)."""
    if not ids:
        return {}
    listings = (
        await session.scalars(
            select(Listing).where(Listing.id.in_(ids)).options(selectinload(Listing.translations))
        )
    ).all()
    categories = {
        c.id: c
        for c in await session.scalars(
            select(Category).where(Category.id.in_({x.category_id for x in listings}))
        )
    }
    places = {
        loc.id: loc
        for loc in await session.scalars(
            select(Location).where(Location.id.in_({x.location_id for x in listings if x.location_id}))
        )
    }
    out = {}
    for x in listings:
        texts = {t.lang: t for t in x.translations}
        text = texts.get(lang) or texts.get(x.original_lang) or next(iter(texts.values()), None)
        place = places.get(x.location_id) if x.location_id else None
        out[x.id] = (
            AppliedListing(
                id=x.id,
                title=text.title if text else f"#{x.id}",
                status=x.status,
                location_name=tr(place.names, lang) if place else None,
            ),
            tr(categories[x.category_id].name, lang),
        )
    return out


@router.patch("/applications/{application_id}", dependencies=[Depends(require_staff)])
async def update_application(
    application_id: int, body: AdminApplicationUpdate, session: SessionDep
) -> dict[str, str]:
    application = await session.get(Application, application_id)
    if application is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")
    changed = application.status != body.status
    application.status = body.status
    if changed and application.bot_app_id is not None:
        telegram.queue_status(session, application)  # the card in the Telegram group follows
    await session.commit()
    return {"status": application.status}
