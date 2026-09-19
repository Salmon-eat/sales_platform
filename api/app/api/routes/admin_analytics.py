"""Dashboard and ad links (staff)."""

import re
import secrets
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import AdminLang, CurrentUser, SessionDep, require_staff
from app.core.slug import transliterate
from app.models import AnalyticsEvent, TrackedLink
from app.schemas.analytics import TrackedLinkIn, TrackedLinkOut
from app.services.dashboard import build_dashboard

PERIODS = (1, 7, 30, 90)

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_staff)])


@router.get("/dashboard")
async def dashboard(
    session: SessionDep,
    lang: AdminLang,
    days: Annotated[int, Query(description="1 (today), 7, 30 or 90")] = 7,
) -> dict[str, Any]:
    if days not in PERIODS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "days must be 1, 7, 30 or 90")
    return await build_dashboard(session, days, lang)


def _link_out(link: TrackedLink, stats: dict[str, Any] | None = None) -> TrackedLinkOut:
    return TrackedLinkOut.model_validate(
        {**{c: getattr(link, c) for c in TrackedLinkOut.model_fields if hasattr(link, c)}, **(stats or {})}
    )


@router.get("/links", response_model=list[TrackedLinkOut])
async def links(session: SessionDep) -> list[TrackedLinkOut]:
    """All ad links with their all-time numbers (cost per application needs the whole life of a link)."""
    rows = (
        await session.scalars(
            select(TrackedLink).order_by(TrackedLink.is_active.desc(), TrackedLink.id.desc())
        )
    ).all()
    clicks = dict(
        (
            await session.execute(
                select(AnalyticsEvent.campaign, func.count())
                .where(AnalyticsEvent.type == "link_click")
                .group_by(AnalyticsEvent.campaign)
            )
        ).all()
    )
    last_click = dict(
        (
            await session.execute(
                select(AnalyticsEvent.campaign, func.max(AnalyticsEvent.created_at))
                .where(AnalyticsEvent.type == "link_click")
                .group_by(AnalyticsEvent.campaign)
            )
        ).all()
    )
    visits = {
        campaign: (visitors, applications)
        for campaign, visitors, applications in await session.execute(
            select(
                AnalyticsEvent.campaign,
                func.count(AnalyticsEvent.visitor.distinct()),
                func.count(AnalyticsEvent.session.distinct()).filter(AnalyticsEvent.type == "apply_sent"),
            )
            .where(AnalyticsEvent.campaign.is_not(None), AnalyticsEvent.type != "link_click")
            .group_by(AnalyticsEvent.campaign)
        )
    }
    return [
        _link_out(
            link,
            {
                "clicks": clicks.get(link.code, 0),
                "visitors": visits.get(link.code, (0, 0))[0],
                "applications": visits.get(link.code, (0, 0))[1],
                "last_click_at": last_click.get(link.code),
            },
        )
        for link in rows
    ]


def _short_code(name: str, taken: set[str]) -> str:
    """A short code from the nickname: 4 letters + 2 digits (@olena_travel -> olen27)."""
    words = name.split()
    nick = next((w for w in words if w.startswith("@")), words[0] if words else "")
    letters = re.sub(r"[^a-z0-9]", "", transliterate(nick, "uk"))[:4] or "link"
    for attempt in range(60):
        digits = 2 if attempt < 30 else 4  # 90 two-digit codes per nickname, then longer ones
        code = f"{letters}{secrets.randbelow(9 * 10 ** (digits - 1)) + 10 ** (digits - 1)}"
        if code not in taken:
            return code
    return f"{letters}{secrets.token_hex(4)}"


@router.post("/links", response_model=TrackedLinkOut, status_code=status.HTTP_201_CREATED)
async def create_link(body: TrackedLinkIn, session: SessionDep, user: CurrentUser) -> TrackedLinkOut:
    data = body.model_dump()
    if not data["code"]:
        taken = set((await session.scalars(select(TrackedLink.code))).all())
        data["code"] = _short_code(body.name, taken)
    link = TrackedLink(**data, created_by_id=user.id)
    session.add(link)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "link_code_taken") from None
    await session.refresh(link)
    return _link_out(link)


@router.put("/links/{link_id}", response_model=TrackedLinkOut)
async def update_link(link_id: int, body: TrackedLinkIn, session: SessionDep) -> TrackedLinkOut:
    link = await session.get(TrackedLink, link_id)
    if link is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Link not found")
    if not link.is_active:
        raise HTTPException(status.HTTP_409_CONFLICT, "link_closed")
    if body.code and body.code != link.code:
        # the code is already printed in a blogger's post; changing it would break their link
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "link_code_fixed")
    for key, value in body.model_dump(exclude={"code"}).items():
        setattr(link, key, value)
    await session.commit()
    await session.refresh(link)
    return _link_out(link)


@router.post("/links/{link_id}/close", response_model=TrackedLinkOut)
async def close_link(link_id: int, session: SessionDep) -> TrackedLinkOut:
    """The campaign is over: the link stops counting (it leads to the home page) and goes to the history,
    where its numbers stay."""
    link = await session.get(TrackedLink, link_id)
    if link is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Link not found")
    if link.is_active:
        link.is_active = False
        link.closed_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(link)
    return _link_out(link)
