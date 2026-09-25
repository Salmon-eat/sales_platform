"""Complaints about ads, and what the team does with them.

A report changes nothing on the site by itself — it only puts the ad in front of a person. The same
visitor reporting the same ad twice is one report, so a single annoyed reader cannot make a queue.
"""

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Listing, ListingReport, Section, User
from app.models.i18n import tr

# the same ad reported again from the same place within this window is the same complaint
SAME_WINDOW = timedelta(days=7)
REPORTABLE = ("active", "paused")


async def create(
    session: AsyncSession,
    listing_id: int,
    reason: str,
    note: str | None,
    user: User | None,
    ip: str | None,
) -> ListingReport:
    listing = await session.get(Listing, listing_id)
    if listing is None or listing.status not in REPORTABLE:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found")

    since = datetime.now(UTC) - SAME_WINDOW
    conds = [ListingReport.listing_id == listing_id, ListingReport.created_at > since]
    conds.append(ListingReport.reporter_id == user.id if user else ListingReport.ip == ip)
    existing = await session.scalar(select(ListingReport).where(*conds).limit(1))
    if existing is not None:
        return existing

    report = ListingReport(
        listing_id=listing_id,
        reporter_id=user.id if user else None,
        reason=reason,
        note=note,
        ip=ip,
    )
    session.add(report)
    await session.commit()
    await session.refresh(report)
    return report


async def waiting(session: AsyncSession) -> int:
    return (
        await session.scalar(
            select(func.count()).select_from(ListingReport).where(ListingReport.status == "new")
        )
        or 0
    )


async def queue(session: AsyncSession, lang: str, limit: int = 50) -> list[dict]:
    """Oldest first, with everything needed to judge without opening another page."""
    rows = (
        await session.scalars(
            select(ListingReport)
            .where(ListingReport.status == "new")
            .order_by(ListingReport.created_at)
            .limit(limit)
        )
    ).all()

    out = []
    for report in rows:
        listing = await session.scalar(
            select(Listing)
            .where(Listing.id == report.listing_id)
            .options(selectinload(Listing.translations), selectinload(Listing.photos))
        )
        text = None
        if listing and listing.translations:
            by_lang = {t.lang: t for t in listing.translations}
            text = by_lang.get(lang) or by_lang.get(listing.original_lang) or listing.translations[0]
        section = await session.get(Section, listing.section_id) if listing else None
        owner = await session.get(User, listing.owner_id) if listing and listing.owner_id else None
        others = (
            await session.scalar(
                select(func.count())
                .select_from(ListingReport)
                .where(
                    ListingReport.listing_id == report.listing_id,
                    ListingReport.id != report.id,
                )
            )
            or 0
        )
        out.append(
            {
                "id": report.id,
                "reason": report.reason,
                "note": report.note,
                "created_at": report.created_at,
                "also_reported": others,
                "listing_id": report.listing_id,
                "listing_title": text.title if text else "—",
                "listing_text": text.description if text else "",
                "listing_status": listing.status if listing else "—",
                "section_name": tr(section.name, lang) if section else "—",
                "owner_id": owner.id if owner else None,
                "owner_name": (owner.name or owner.email) if owner else None,
                "owner_active": owner.is_active if owner else None,
            }
        )
    return out


async def resolve(
    session: AsyncSession,
    report_id: int,
    action: str,
    staff: User,
    block_reason: str | None = None,
) -> None:
    """accept: take the ad down (and optionally block the person); reject: the ad is fine."""
    report = await session.get(ListingReport, report_id)
    if report is None or report.status != "new":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found")

    now = datetime.now(UTC)
    report.status = "accepted" if action == "accept" else "rejected"
    report.reviewed_by, report.reviewed_at = staff.id, now

    if action == "accept":
        listing = await session.get(Listing, report.listing_id)
        if listing is not None:
            listing.status = "rejected"
            listing.reject_reason = report.reason
            listing.moderated_by, listing.moderated_at = staff.id, now
            # every other complaint about this ad is answered by the same decision
            await session.execute(
                update(ListingReport)
                .where(
                    ListingReport.listing_id == report.listing_id,
                    ListingReport.status == "new",
                    ListingReport.id != report.id,
                )
                .values(status="accepted", reviewed_by=staff.id, reviewed_at=now)
            )
            if block_reason and listing.owner_id:
                await block_user(session, listing.owner_id, block_reason)
    await session.commit()


async def block_user(session: AsyncSession, user_id: int, reason: str) -> None:
    """The account stops working and everything it has on the site goes down with it."""
    person = await session.get(User, user_id)
    if person is None or person.is_staff:
        raise HTTPException(status.HTTP_409_CONFLICT, "cannot_block")
    person.is_active = False
    person.blocked_reason = reason[:200]
    await session.execute(
        update(Listing)
        .where(Listing.owner_id == user_id, Listing.status.in_(("active", "pending", "paused")))
        .values(status="paused")
    )


async def unblock_user(session: AsyncSession, user_id: int) -> None:
    person = await session.get(User, user_id)
    if person is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "not_found")
    person.is_active = True
    person.blocked_reason = None
    await session.commit()
