"""Paid "top" ads to look at locally: one to three in every section of the board.

Nothing is created: the command picks ads that are already there (the hand-written demo ones before the
load-test filler, newest first) and gives them the same `promoted_until` a paid order would. Run it again
and it only tops up a section that has fewer than its share.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Listing, Section

DAYS = 14


async def seed_demo_top(session: AsyncSession) -> dict[str, int]:
    """Section key -> how many of its ads are on top now."""
    now = datetime.now(UTC)
    sections = (
        await session.scalars(
            select(Section)
            .where(Section.is_enabled.is_(True), Section.kind == "listings")
            .order_by(Section.sort)
        )
    ).all()
    active = Listing.status == "active"
    on_top = Listing.promoted_until > now
    filler = Listing.contact.contains({"_loadtest": True})

    result: dict[str, int] = {}
    for index, section in enumerate(sections):
        share = index % 3 + 1  # 1, 2, 3, 1, 2, 3...: sections look different, as on a real board
        have = (
            await session.scalar(
                select(func.count()).where(Listing.section_id == section.id, active, on_top)
            )
            or 0
        )
        if have < share:
            ids = (
                await session.scalars(
                    select(Listing.id)
                    .where(
                        Listing.section_id == section.id,
                        active,
                        or_(Listing.promoted_until.is_(None), Listing.promoted_until <= now),
                    )
                    .order_by(filler.asc(), Listing.published_at.desc())
                    .limit(share - have)
                )
            ).all()
            if ids:
                await session.execute(
                    update(Listing).where(Listing.id.in_(ids)).values(promoted_until=now + timedelta(days=DAYS))
                )
            have += len(ids)
        result[section.key] = have
    await session.commit()
    return result
