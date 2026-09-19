"""Anonymous site analytics and ad links (/go/<code>)."""

import re

from fastapi import APIRouter, HTTPException, Request, Response, status
from redis.exceptions import RedisError
from sqlalchemy import select

from app.api.deps import RedisDep, SessionDep
from app.models import AnalyticsEvent, TrackedLink
from app.schemas.analytics import EventsIn, GoOut

router = APIRouter(tags=["analytics"])

BOT_RE = re.compile(r"bot|crawl|spider|slurp|preview|lighthouse|headless|curl|python|wget", re.I)
EVENTS_PER_SESSION_PER_HOUR = 600
SOURCE_RE = re.compile(r"[^a-z0-9._-]")


def _clean_source(value: str) -> str:
    return SOURCE_RE.sub("", value.lower())[:40] or "direct"


async def _over_limit(redis: RedisDep, session_id: str, count: int) -> bool:
    key = f"rl:events:{session_id}"
    try:
        total = await redis.incrby(key, count)
        if total == count:
            await redis.expire(key, 3600)
    except RedisError:
        return False
    return total > EVENTS_PER_SESSION_PER_HOUR


@router.post("/events", status_code=status.HTTP_204_NO_CONTENT)
async def collect_events(body: EventsIn, request: Request, session: SessionDep, redis: RedisDep) -> Response:
    """Batch of page views, time on page, form opens etc. from the site. Always 204: the browser does
    not care, and a dropped event must never break a page."""
    if BOT_RE.search(request.headers.get("user-agent", "")) or await _over_limit(
        redis, body.session, len(body.events)
    ):
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    device = "tablet" if body.tablet else "mobile" if body.mobile else "desktop"
    source = _clean_source(body.source)
    campaign = body.campaign.strip().lower()[:60] if body.campaign else None
    for e in body.events:
        session.add(
            AnalyticsEvent(
                visitor=body.visitor,
                session=body.session,
                type=e.type,
                path=e.path.split("?")[0][:300],
                lang=body.lang,
                device=device,
                source=source,
                campaign=campaign,
                listing_id=e.listing_id,
                duration_ms=e.duration_ms,
                props=e.props,
            )
        )
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/go/{code}", response_model=GoOut)
async def follow_link(code: str, request: Request, session: SessionDep) -> GoOut:
    """The web /go/<code> route asks where to send the visitor and the click is counted here."""
    link = await session.scalar(select(TrackedLink).where(TrackedLink.code == code.lower()))
    if link is None or not link.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Link not found")
    if not BOT_RE.search(request.headers.get("user-agent", "")):
        session.add(
            AnalyticsEvent(
                visitor="",
                session="",
                type="link_click",
                path=link.target_path[:300],
                source=link.channel,
                campaign=link.code,
            )
        )
        await session.commit()
    return GoOut(target=link.target_path, channel=link.channel, code=link.code)
